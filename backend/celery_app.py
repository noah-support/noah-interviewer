import os

from celery import Celery
from dotenv import load_dotenv


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")

load_dotenv(".env.local", override=True)


celery_app = Celery(
    "noah_interviewer",
    broker=_redis_url(),
    backend=_redis_url(),
    include=["tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue=os.getenv("CELERY_QUEUE", "default"),
    timezone="UTC",
)

# Ensure task decorators in `tasks.py` are registered when workers boot.
# (Celery only registers tasks from imported modules.)
import tasks  # noqa: E402,F401

