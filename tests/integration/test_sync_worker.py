from datetime import UTC, datetime
from unittest.mock import patch

import pytest
import redis.asyncio as aioredis

from app.application.use_cases.sync_erp_movement import SyncERPMovementUseCase
from app.core.config import settings
from app.core.exceptions import WarehouseNotFoundError
from app.domain.models.coordinates import Coordinates
from app.domain.models.warehouse import Warehouse
from app.infrastructure.cache.redis_grid_adapter import RedisGridAdapter
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import async_session_factory
from app.infrastructure.erp.client import simulated_erp_client
from app.infrastructure.erp.models import ERPMovementRecord, ERPMovementType
from app.infrastructure.workers.tasks import (
    handle_dead_letter,
    poll_erp_movements_task,
    process_erp_movement_task,
)


@pytest.fixture
def unique_warehouse_id() -> str:
    return f"WH-SYNC-{datetime.now(UTC).timestamp()}"


@pytest.fixture
async def seeded_warehouse(unique_warehouse_id: str) -> Warehouse:
    wh = Warehouse(
        warehouse_id=unique_warehouse_id,
        name="Sync Worker Test Warehouse",
        total_streets=2,
        total_columns=2,
        total_levels=2,
        dock_coordinates=Coordinates(0, 0, 0),
    )
    async with async_session_factory() as session:
        repo = SqlAlchemyWarehouseRepository(session)
        await repo.save_warehouse(wh)
    return wh


@pytest.mark.asyncio
async def test_sync_inbound_movement_with_idempotency_and_pubsub(
    seeded_warehouse: Warehouse,
) -> None:
    warehouse_id = seeded_warehouse.warehouse_id
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    pubsub = client.pubsub()
    channel = f"warehouse:{warehouse_id}:events"
    await pubsub.subscribe(channel)

    try:
        # Initial subscription message
        await pubsub.get_message(ignore_subscribe_messages=False, timeout=2.0)

        async with async_session_factory() as session:
            repository = SqlAlchemyWarehouseRepository(session)
            grid_cache = RedisGridAdapter(client)
            use_case = SyncERPMovementUseCase(repository=repository, grid_cache=grid_cache)

            event = ERPMovementRecord(
                event_id=f"ERP-IN-{datetime.now(UTC).timestamp()}",
                warehouse_id=warehouse_id,
                batch_id="BATCH-SYNC-01",
                cooperative_id="COOP-A",
                coffee_type="BOURBON",
                harvest_year=2026,
                weight_kg=60.0,
                movement_type=ERPMovementType.INBOUND,
                to_x=0,
                to_y=1,
                to_z=0,
            )

            # 1. Process movement
            result = await use_case.execute(event)
            assert result is True

            # 2. Verify ground truth in PostgreSQL
            wh_db = await repository.get_warehouse(warehouse_id)
            assert wh_db is not None
            slot_db = wh_db.get_slot(Coordinates(0, 1, 0))
            assert slot_db is not None
            assert slot_db.is_occupied
            assert slot_db.bag is not None
            assert slot_db.bag.batch_id == "BATCH-SYNC-01"

            # 3. Verify Redis grid cache updated
            wh_redis = await grid_cache.get_warehouse_grid(warehouse_id)
            assert wh_redis is not None
            slot_redis = wh_redis.get_slot(Coordinates(0, 1, 0))
            assert slot_redis is not None
            assert slot_redis.is_occupied

            # 4. Verify Pub/Sub notification received
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=2.0)
            assert msg is not None
            assert b"INVENTORY_SYNC" in msg["data"]
            assert b"BATCH-SYNC-01" in msg["data"]

            # 5. Verify Idempotency: duplicate submission must return False
            duplicate_result = await use_case.execute(event)
            assert duplicate_result is False

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()  # type: ignore[no-untyped-call]
        await client.aclose()


@pytest.mark.asyncio
async def test_sync_outbound_and_internal_transfer(seeded_warehouse: Warehouse) -> None:
    warehouse_id = seeded_warehouse.warehouse_id
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)

    try:
        async with async_session_factory() as session:
            repository = SqlAlchemyWarehouseRepository(session)
            grid_cache = RedisGridAdapter(client)
            use_case = SyncERPMovementUseCase(repository=repository, grid_cache=grid_cache)

            # Step 1: Inbound
            inbound_evt = ERPMovementRecord(
                event_id=f"ERP-IN-TRANS-{datetime.now(UTC).timestamp()}",
                warehouse_id=warehouse_id,
                batch_id="BATCH-TRANS-01",
                cooperative_id="COOP-B",
                coffee_type="CATUAI",
                harvest_year=2026,
                movement_type=ERPMovementType.INBOUND,
                to_x=0,
                to_y=0,
                to_z=0,
            )
            await use_case.execute(inbound_evt)

            # Step 2: Internal Transfer from (0,0,0) to (0,0,1)
            transfer_evt = ERPMovementRecord(
                event_id=f"ERP-TRANSFER-{datetime.now(UTC).timestamp()}",
                warehouse_id=warehouse_id,
                batch_id="BATCH-TRANS-01",
                cooperative_id="COOP-B",
                coffee_type="CATUAI",
                harvest_year=2026,
                movement_type=ERPMovementType.INTERNAL_TRANSFER,
                from_x=0,
                from_y=0,
                from_z=0,
                to_x=0,
                to_y=0,
                to_z=1,
            )
            res_transfer = await use_case.execute(transfer_evt)
            assert res_transfer is True

            wh_db = await repository.get_warehouse(warehouse_id)
            assert wh_db is not None
            s00 = wh_db.get_slot(Coordinates(0, 0, 0))
            s01 = wh_db.get_slot(Coordinates(0, 0, 1))
            assert s00 is not None
            assert s00.is_available
            assert s01 is not None
            assert s01.is_occupied

            # Step 3: Outbound from (0,0,1)
            outbound_evt = ERPMovementRecord(
                event_id=f"ERP-OUT-{datetime.now(UTC).timestamp()}",
                warehouse_id=warehouse_id,
                batch_id="BATCH-TRANS-01",
                cooperative_id="COOP-B",
                coffee_type="CATUAI",
                harvest_year=2026,
                movement_type=ERPMovementType.OUTBOUND,
                from_x=0,
                from_y=0,
                from_z=1,
            )
            res_outbound = await use_case.execute(outbound_evt)
            assert res_outbound is True

            wh_db_after = await repository.get_warehouse(warehouse_id)
            assert wh_db_after is not None
            s01_after = wh_db_after.get_slot(Coordinates(0, 0, 1))
            assert s01_after is not None
            assert s01_after.is_available

    finally:
        await client.aclose()


def test_celery_task_and_polling(seeded_warehouse: Warehouse) -> None:
    warehouse_id = seeded_warehouse.warehouse_id
    simulated_erp_client.clear()

    event = ERPMovementRecord(
        event_id=f"ERP-CELERY-{datetime.now(UTC).timestamp()}",
        warehouse_id=warehouse_id,
        batch_id="BATCH-CELERY-01",
        cooperative_id="COOP-C",
        coffee_type="ARABICA",
        harvest_year=2026,
        movement_type=ERPMovementType.INBOUND,
        to_x=1,
        to_y=1,
        to_z=0,
    )

    # 1. Test direct task execution
    success = process_erp_movement_task(event.model_dump(mode="json"))
    assert success is True

    # 2. Test Polling task with client
    simulated_erp_client.feed_movement(event)
    polled = poll_erp_movements_task()
    assert polled >= 1

    # 3. Test DLQ handler
    handle_dead_letter({"test": "payload"}, "Simulated Error")


def test_celery_task_retries_and_dlq_on_failure() -> None:
    invalid_payload = {
        "event_id": "ERP-INVALID",
        "warehouse_id": "NON-EXISTENT-WH",
        "batch_id": "B1",
        "cooperative_id": "C1",
        "coffee_type": "ARABICA",
        "harvest_year": 2026,
        "movement_type": "INBOUND",
        "to_x": 0,
        "to_y": 0,
        "to_z": 0,
    }

    # Test DLQ routing when retries exhausted
    process_erp_movement_task.push_request(retries=3)
    try:
        with patch("app.infrastructure.workers.tasks.handle_dead_letter.delay") as mock_dlq:
            with pytest.raises(WarehouseNotFoundError):
                process_erp_movement_task(invalid_payload)
            mock_dlq.assert_called_once()
    finally:
        process_erp_movement_task.pop_request()

    # Test retry invocation when retries < max_retries
    process_erp_movement_task.push_request(retries=0)
    try:
        with patch.object(
            process_erp_movement_task, "retry", side_effect=RuntimeError("Retried")
        ) as mock_retry:
            with pytest.raises(RuntimeError, match="Retried"):
                process_erp_movement_task(invalid_payload)
            mock_retry.assert_called_once()
    finally:
        process_erp_movement_task.pop_request()
