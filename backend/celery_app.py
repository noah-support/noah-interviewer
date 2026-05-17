import os

from celery import Celery
from env_loader import load_app_env
from redis_config import normalize_redis_url_for_celery, redis_url

load_app_env()

_broker_url = normalize_redis_url_for_celery(redis_url())

celery_app = Celery(
    "noah_interviewer",
    broker=_broker_url,
    backend=_broker_url,
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
