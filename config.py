import os
import logging
import sys

# === Logging Setup ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)],
)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class Settings:
    # Celery Configuration (same Redis DB for simplicity)
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Queue names
    QUEUE_GENERAL = "general"
    QUEUE_JSON = "json"
    QUEUE_VISION = "vision"

    # Task-to-queue mapping
    TASK_QUEUE_MAP = {
        "generate": "general",
        "chat": "general",
        "synthesize": "general",
        "extract": "json",
        "structured": "json",
        "vision": "vision",
    }

    # Worker settings
    CELERY_TASK_ACKS_LATE = True
    CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # One task at a time
    CELERY_RESULT_EXPIRES = 60 * 60 * 48   # 48 hours

    # Ollama
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))

    # OpenRouter fallback
    OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3-5-sonnet")

    # Auth & Rate limiting
    API_KEY = os.getenv("API_KEY", "")
    RATE_LIMIT = int(os.getenv("RATE_LIMIT", "300"))  # 300 requests per minute

    # Models - defaults, but client can override via request
    MODELS = {
        "general": os.getenv("GENERAL_MODEL", "qwen2.5:32b"),
        "json": os.getenv("JSON_MODEL", "deepseek-coder-v2:16b"),
        "vision": os.getenv("VISION_MODEL", "qwen2.5vl:7b"),
    }
    TASK_MODEL = {"synthesize": "general", "extract": "json", "vision": "vision"}

    # Prompts
    SYSTEM = {
        "chat": "You are a helpful assistant.",
        "extract": "Extract structured data. Return valid JSON only.",
        "synthesize": "Synthesize information. Return valid JSON only.",
        "vision": "Analyze the image precisely.",
    }

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    # File uploads
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./data/uploads")
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024)))  # 10MB

settings = Settings()

def get_model(task: str) -> str:
    return settings.MODELS.get(settings.TASK_MODEL.get(task))

def get_system(task: str) -> str:
    return settings.SYSTEM.get(task, settings.SYSTEM["chat"])
