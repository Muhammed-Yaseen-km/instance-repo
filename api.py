import os
import time
import shutil
from collections import defaultdict
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import client
from config import settings
from celery.result import AsyncResult
from celery_app import app as celery_app
import redis
import uuid

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# === Redis Connection Pool ===
_redis_pool = None

def get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(settings.CELERY_BROKER_URL)
    return redis.Redis(connection_pool=_redis_pool)

# === Middleware ===

_requests = defaultdict(list)

async def auth(request: Request):
    if settings.API_KEY:
        if request.headers.get("Authorization", "").replace("Bearer ", "") != settings.API_KEY:
            raise HTTPException(401, "Invalid API key")

async def rate_limit(request: Request):
    if settings.RATE_LIMIT:
        now, ip = time.time(), request.client.host
        _requests[ip] = [t for t in _requests[ip] if now - t < 60]
        if len(_requests[ip]) >= settings.RATE_LIMIT:
            raise HTTPException(429, "Rate limit exceeded")
        _requests[ip].append(now)

# === Models ===

class InferRequest(BaseModel):
    prompt: str = None
    messages: List[Dict] = None
    images: List[str] = None
    task: str = "chat"
    model: str = None
    stream: bool = False
    temperature: float = 0.7
    system: str = None

class StructuredRequest(BaseModel):
    prompt: str
    schema_: Dict
    model: str = None
    class Config:
        fields = {"schema_": "schema"}

class AsyncTaskRequest(BaseModel):
    task_type: str  # generate, chat, vision, structured, extract
    payload: Dict[str, Any]

# === Router ===

router = APIRouter(prefix="/api/v1", dependencies=[Depends(auth), Depends(rate_limit)])

# Task routing: task_type -> (celery_task_name, queue)
TASKS = {
    "generate": ("task.generate", settings.QUEUE_GENERAL),
    "chat": ("task.chat", settings.QUEUE_GENERAL),
    "structured": ("task.structured", settings.QUEUE_JSON),
    "extract": ("task.extract", settings.QUEUE_JSON),
    "vision": ("task.vision", settings.QUEUE_VISION),
}

# === Sync Endpoints ===

@router.get("/health")
def health():
    return client.health()

@router.post("/generate")
def generate(req: InferRequest):
    r = client.infer(prompt=req.prompt, task=req.task, model=req.model, images=req.images,
                     stream=req.stream, temperature=req.temperature, system=req.system)
    return StreamingResponse(r, media_type="text/event-stream") if req.stream else {"response": r}

@router.post("/chat")
def chat(req: InferRequest):
    r = client.chat(messages=req.messages, model=req.model, stream=req.stream, system=req.system)
    return StreamingResponse(r, media_type="text/event-stream") if req.stream else {"response": r}

@router.post("/vision")
def vision(req: InferRequest):
    return {"response": client.infer(prompt=req.prompt, task="vision", images=req.images, temperature=req.temperature)}

@router.post("/structured")
def structured(req: StructuredRequest):
    return client.structured(prompt=req.prompt, schema=req.schema_, model=req.model)

@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    if file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(413, "File too large")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"]:
        raise HTTPException(400, "Unsupported file type")
    path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"path": path}

# === Async Queue Endpoints ===

@router.post("/async/submit")
def submit_async(req: AsyncTaskRequest):
    """Submit task to queue. Tasks run independently per queue."""
    if req.task_type not in TASKS:
        raise HTTPException(400, f"Unknown task: {req.task_type}. Available: {list(TASKS.keys())}")
    task_name, queue = TASKS[req.task_type]
    task = celery_app.send_task(task_name, kwargs=req.payload, queue=queue)
    return {"task_id": task.id, "queue": queue, "status": "PENDING"}

@router.get("/async/status/{task_id}")
def get_status(task_id: str):
    """Get task status and result."""
    r = AsyncResult(task_id, app=celery_app)
    resp = {"task_id": task_id, "status": r.state}
    if r.successful():
        resp["result"] = r.result
    elif r.failed():
        resp["error"] = str(r.result)
    return resp

@router.get("/async/stats")
def get_stats():
    """Queue statistics."""
    r = get_redis()
    return {q: {"pending": r.llen(q)} for q in [settings.QUEUE_GENERAL, settings.QUEUE_JSON, settings.QUEUE_VISION]}

@router.delete("/async/{task_id}")
def cancel_task(task_id: str):
    """Cancel a pending or running task."""
    celery_app.control.revoke(task_id, terminate=True)
    return {"task_id": task_id, "status": "cancelled"}

@router.get("/async/position/{task_id}")
def get_position(task_id: str):
    """Get task position in queue."""
    r = get_redis()
    for queue in [settings.QUEUE_GENERAL, settings.QUEUE_JSON, settings.QUEUE_VISION]:
        tasks = r.lrange(queue, 0, -1)
        for i, task_data in enumerate(tasks):
            if task_id.encode() in task_data:
                return {"task_id": task_id, "queue": queue, "position": i + 1, "total": len(tasks)}
    return {"task_id": task_id, "position": None, "status": "not_in_queue"}

@router.get("/health/async")
def health_async():
    """Async system health."""
    try:
        get_redis().ping()
        broker_ok = True
    except redis.RedisError:
        broker_ok = False
    workers = celery_app.control.inspect().ping() or {}
    return {"broker": "ok" if broker_ok else "down", "workers": len(workers)}
