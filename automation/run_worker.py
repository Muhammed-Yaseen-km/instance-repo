#!/usr/bin/env python3
"""Start Celery worker with optional model warmup.

Usage: python run_worker.py [queue] [--no-warmup]
  queue: general|json|vision|all (default: all)
  --no-warmup: Skip model warmup

Examples:
  python run_worker.py general
  python run_worker.py vision --no-warmup
"""
import sys
import os
import subprocess

# Change to inference_engine directory (parent of automation/)
os.chdir(os.path.expanduser("~/inference_engine"))
sys.path.insert(0, os.getcwd())

# Parse args
args = sys.argv[1:]
queue = args[0] if args and args[0] in ("general", "json", "vision", "all") else "all"
extra_args = args[1:] if args and args[0] in ("general", "json", "vision", "all") else args

skip_warmup = "--no-warmup" in extra_args
extra_args = [a for a in extra_args if a != "--no-warmup"]

queues = "general,json,vision" if queue == "all" else queue

# Warmup models
if not skip_warmup:
    print(f"Warming up models for queue: {queue}")
    try:
        from client import warmup
        from config import settings
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
        print(f"Warmup failed (continuing): {e}")

# Start worker
cmd = [
    sys.executable, "-m", "celery",
    "-A", "celery_app",
    "worker",
    "-Q", queues,
    "-c", "1",
    "--loglevel", "info",
] + extra_args

print(f"Starting worker for: {queues}")
subprocess.run(cmd)
