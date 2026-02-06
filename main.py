import time
import uuid
import subprocess
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api import router
from config import settings, get_logger

log = get_logger("api")

# Deploy secret (set in .env or use default)
DEPLOY_SECRET = os.getenv("DEPLOY_SECRET", "inference-deploy-2024")

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

# Deploy webhook endpoint - triggered from your PC after git push
@app.post("/deploy")
async def deploy(request: Request):
    """Pull latest code and restart services. Requires X-Deploy-Secret header."""
    secret = request.headers.get("X-Deploy-Secret", "")
    if secret != DEPLOY_SECRET:
        raise HTTPException(401, "Invalid deploy secret")

    log.info("Deploy triggered - pulling code and restarting...")
    try:
        # Run deploy script
        result = subprocess.run(
            ["bash", "-c", "cd ~/inference_engine && git pull origin main"],
            capture_output=True, text=True, timeout=60
        )
        git_output = result.stdout + result.stderr

        # Restart services (runs in background, don't wait)
        subprocess.Popen(
            ["bash", "-c", "cd ~/inference_engine && docker compose down && docker compose up -d --build"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        log.info(f"Deploy started: {git_output.strip()}")
        return {"status": "deploying", "git": git_output.strip(), "message": "Services restarting..."}
    except Exception as e:
        log.error(f"Deploy failed: {e}")
        raise HTTPException(500, f"Deploy failed: {e}")

log.info("Inference Engine started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
