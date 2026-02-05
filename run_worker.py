#!/usr/bin/env python
"""Start Celery worker with optional model warmup.

Usage: python run_worker.py [queue] [--no-warmup] [celery options]
  queue: general|json|vision|all (default: all)
  --no-warmup: Skip model warmup

Examples:
  python run_worker.py general              # Warmup + start worker
  python run_worker.py general --no-warmup  # Skip warmup
  python run_worker.py vision --loglevel debug
"""
import sys
import subprocess

# Parse args
args = sys.argv[1:]
queue = args[0] if args and args[0] in ("general", "json", "vision", "all") else "all"
extra_args = args[1:] if args and args[0] in ("general", "json", "vision", "all") else args

# Check for --no-warmup flag
skip_warmup = "--no-warmup" in extra_args
extra_args = [a for a in extra_args if a != "--no-warmup"]

queues = "general,json,vision" if queue == "all" else queue

# Warmup models for this queue
if not skip_warmup:
    print(f"Warming up models for queue: {queue}")
    try:
        from client import warmup
        from config import settings

        # Map queue to model
        queue_models = {
            "general": [settings.MODELS["general"]],
            "json": [settings.MODELS["json"]],
            "vision": [settings.MODELS["vision"]],
            "all": list(settings.MODELS.values()),
        }
        models = queue_models.get(queue, [])
        result = warmup(models)
        for model, status in result.get("models", {}).items():
            print(f"  {model}: {status}")
    except Exception as e:
        print(f"Warmup failed (continuing anyway): {e}")

# Build celery command
cmd = [
    sys.executable, "-m", "celery",
    "-A", "celery_app",
    "worker",
    "-Q", queues,
]

# Add defaults only if not overridden
if not any("-c" in arg or "--concurrency" in arg for arg in extra_args):
    cmd.extend(["-c", "1"])  # Default: 1 worker (1 GPU)
if not any("--loglevel" in arg for arg in extra_args):
    cmd.extend(["--loglevel", "info"])

cmd.extend(extra_args)

print(f"Starting worker for queue(s): {queues}")
print(f"Command: {' '.join(cmd)}")
subprocess.run(cmd)
