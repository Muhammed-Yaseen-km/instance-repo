"""Celery application with queue management for LLM inference.

3 queues (general, json, vision) with dedicated workers.
Each queue processes tasks independently - slow tasks don't block fast ones.
"""
import time
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from kombu import Queue
from config import settings, get_logger
import client

log = get_logger("worker")

# === Celery App ===

app = Celery(
    "inference_engine",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

app.conf.update(
    # Queue config
    task_queues=[
        Queue(settings.QUEUE_GENERAL),
        Queue(settings.QUEUE_JSON),
        Queue(settings.QUEUE_VISION),
    ],
    task_routes={
        "task.generate": {"queue": settings.QUEUE_GENERAL},
        "task.chat": {"queue": settings.QUEUE_GENERAL},
        "task.structured": {"queue": settings.QUEUE_JSON},
        "task.extract": {"queue": settings.QUEUE_JSON},
        "task.vision": {"queue": settings.QUEUE_VISION},
    },
    # Worker config
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_max_tasks_per_child=100,  # Restart after 100 tasks (prevent memory leak)
    # Task reliability
    task_acks_late=settings.CELERY_TASK_ACKS_LATE,
    task_reject_on_worker_lost=True,  # Requeue if worker crashes
    task_time_limit=600,              # Hard kill after 10 min
    task_soft_time_limit=540,         # Warn at 9 min
    # Result config
    result_expires=settings.CELERY_RESULT_EXPIRES,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Broker reliability
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},  # 1 hour before requeue
)


# === Task Logging ===

_task_start = {}

@task_prerun.connect
def on_task_start(task_id, task, *args, **kwargs):
    _task_start[task_id] = time.time()
    log.info(f"{task_id[:8]} | START | {task.name}")

@task_postrun.connect
def on_task_end(task_id, task, retval, state, *args, **kwargs):
    duration = (time.time() - _task_start.pop(task_id, time.time())) * 1000
    log.info(f"{task_id[:8]} | {state} | {task.name} | {duration:.0f}ms")

@task_failure.connect
def on_task_fail(task_id, exception, *args, **kwargs):
    log.error(f"{task_id[:8]} | FAILED | {type(exception).__name__}: {exception}")


# === Tasks ===

# Retry settings: exponential backoff, max 2 retries
TASK_OPTS = dict(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=2)


# General queue tasks
@app.task(name="task.generate", **TASK_OPTS)
def generate(self, prompt: str, model: str = None, task: str = "synthesize",
             temperature: float = 0.7, system: str = None, num_predict: int = None, **kwargs):
    """Text generation task."""
    return {"success": True, "response": client.infer(
        prompt=prompt, task=task, model=model, temperature=temperature, system=system,
        num_predict=num_predict, **kwargs)}


@app.task(name="task.chat", **TASK_OPTS)
def chat(self, messages: list, model: str = None, system: str = None, **kwargs):
    """Chat completion task."""
    return {"success": True, "response": client.chat(
        messages=messages, model=model, system=system, **kwargs)}


# JSON queue tasks
@app.task(name="task.structured", **TASK_OPTS)
def structured(self, prompt: str, schema: dict, model: str = None, retries: int = 2, **kwargs):
    """Structured JSON extraction task."""
    return client.structured(prompt=prompt, schema=schema, model=model, retries=retries, **kwargs)


@app.task(name="task.extract", **TASK_OPTS)
def extract(self, prompt: str, model: str = None, temperature: float = 0.1, num_predict: int = 2048, **kwargs):
    """Data extraction task - limited output for speed."""
    return {"success": True, "response": client.infer(
        prompt=prompt, task="extract", model=model, temperature=temperature,
        num_predict=num_predict, **kwargs)}


# Vision queue tasks (longer timeout for slow inference)
@app.task(name="task.vision", **TASK_OPTS, time_limit=900, soft_time_limit=840)
def vision(self, prompt: str, images: list, model: str = None, temperature: float = 0.7, **kwargs):
    """Vision analysis task."""
    return {"success": True, "response": client.infer(
        prompt=prompt, task="vision", images=images, model=model, temperature=temperature, **kwargs)}
