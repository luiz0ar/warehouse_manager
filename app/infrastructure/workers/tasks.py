import asyncio
from typing import Any

import redis.asyncio as aioredis
import structlog
from celery import Task

from app.application.use_cases.sync_erp_movement import SyncERPMovementUseCase
from app.core.config import settings
from app.infrastructure.cache.redis_grid_adapter import RedisGridAdapter
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import async_session_factory
from app.infrastructure.erp.client import simulated_erp_client
from app.infrastructure.erp.models import ERPMovementRecord
from app.infrastructure.workers.celery_app import celery_app

logger = structlog.get_logger()


async def _execute_sync(record: ERPMovementRecord) -> bool:
    """Execute domain state synchronization in an isolated asynchronous session."""
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    try:
        async with async_session_factory() as session:
            repository = SqlAlchemyWarehouseRepository(session)
            grid_cache = RedisGridAdapter(client)
            use_case = SyncERPMovementUseCase(repository=repository, grid_cache=grid_cache)
            return await use_case.execute(record)
    finally:
        await client.aclose()


async def _execute_poll() -> int:
    """Query legacy ERP and enqueue new movements for worker processing."""
    records = await simulated_erp_client.fetch_pending_movements()
    for record in records:
        process_erp_movement_task.delay(record.model_dump(mode="json"))
    return len(records)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=2)
def process_erp_movement_task(self: Task, movement_dict: dict[str, Any]) -> bool:
    """Celery task processing an individual ERP movement record with exponential backoff and DLQ routing."""
    try:
        record = ERPMovementRecord.model_validate(movement_dict)
        return asyncio.run(_execute_sync(record))
    except Exception as exc:
        logger.warning(
            "erp_movement_processing_failed",
            error=str(exc),
            retry_count=self.request.retries,
            max_retries=self.max_retries,
        )
        if self.request.retries >= self.max_retries:
            logger.error(
                "erp_movement_retries_exhausted_forwarding_to_dlq",
                payload=movement_dict,
                error=str(exc),
            )
            handle_dead_letter.delay(movement_dict, str(exc))
            raise exc

        countdown = 2**self.request.retries
        raise self.retry(exc=exc, countdown=countdown) from exc


@celery_app.task
def poll_erp_movements_task() -> int:
    """Scheduled task to poll the legacy ERP and dispatch worker jobs."""
    polled_count = asyncio.run(_execute_poll())
    logger.info("erp_movements_polled", count=polled_count)
    return polled_count


@celery_app.task(queue="dead_letter")
def handle_dead_letter(payload: dict[str, Any], error: str) -> None:
    """Dead letter queue handler logging and archiving failed sync tasks."""
    logger.error("dead_letter_queue_event_received", payload=payload, error=error)