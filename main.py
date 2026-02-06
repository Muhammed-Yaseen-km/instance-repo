import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from api import router
from config import settings, get_logger

log = get_logger("api")

app = FastAPI(title="Inference Engine", version="1.0.0")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing and request ID."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:8])
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    log.info(f"{request_id} | {request.method} {request.url.path} | {response.status_code} | {duration:.0f}ms")
    response.headers["X-Request-ID"] = request_id
    return response


# CORS: credentials only allowed with explicit origins (not wildcard)
allow_credentials = "*" not in settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
log.info("Inference Engine started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
