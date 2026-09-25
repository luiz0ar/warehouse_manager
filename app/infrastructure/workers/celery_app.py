from celery import Celery
from kombu import Queue

from app.core.config import settings

celery_app = Celery(
    "warehouse_manager",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.infrastructure.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("dead_letter", routing_key="dlq"),
    ),
    task_routes={
        "app.infrastructure.workers.tasks.handle_dead_letter": {"queue": "dead_letter"},
    },
    beat_schedule={
        "poll-legacy-erp-movements": {
            "task": "app.infrastructure.workers.tasks.poll_erp_movements_task",
            "schedule": float(settings.CELERY_POLL_INTERVAL_SECONDS),
        },
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)