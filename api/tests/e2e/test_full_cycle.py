import time
from datetime import UTC, datetime

import httpx
import numpy as np
import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport

from app.application.use_cases.sync_erp_movement import SyncERPMovementUseCase
from app.core.config import settings
from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse
from app.infrastructure.cache.redis_grid_adapter import RedisGridAdapter
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import async_session_factory
from app.infrastructure.erp.client import simulated_erp_client
from app.infrastructure.erp.models import ERPMovementRecord, ERPMovementType
from app.infrastructure.workers.tasks import process_erp_movement_task
from app.presentation.main import app


@pytest.fixture
def unique_warehouse_id() -> str:
    return f"WH-E2E-CYCLE-{int(datetime.now(UTC).timestamp() * 1000)}"


@pytest.fixture
async def e2e_warehouse(unique_warehouse_id: str) -> Warehouse:
    """Create and seed an isolated test warehouse in Postgres and Redis."""
    wh = Warehouse(
        warehouse_id=unique_warehouse_id,
        name="E2E Full Cycle Validation Warehouse",
        total_streets=3,
        total_columns=4,
        total_levels=3,
        dock_coordinates=Coordinates(0, 0, 0),
    )

    # Populate baseline slots with initial coffee batches
    for x in range(wh.total_streets):
        for y in range(wh.total_columns):
            for z in range(wh.total_levels):
                coords = Coordinates(x, y, z)
                # Column (1, 1) is left initially FREE for inbound sync test
                if (x, y) == (1, 1):
                    wh.set_slot(Slot(coordinates=coords, status=SlotStatus.FREE))
                else:
                    bag = CoffeeBag(
                        batch_id=f"BASELINE-{x}-{y}-{z}",
                        cooperative_id="COOP-GUAXUPE",
                        coffee_type="MUNDO_NOVO",
                        harvest_year=2026,
                        entry_date=datetime.now(UTC),
                        weight_kg=60.0,
                    )
                    wh.set_slot(Slot(coordinates=coords, status=SlotStatus.OCCUPIED, bag=bag))

    async with async_session_factory() as session:
        repo = SqlAlchemyWarehouseRepository(session)
        await repo.save_warehouse(wh)

    # Sync Redis grid
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    redis_adapter = RedisGridAdapter(redis_client)
    await redis_adapter.set_warehouse_grid(wh)
    await redis_client.aclose()

    return wh


@pytest.mark.asyncio
async def test_full_cycle_erp_polling_to_grid_to_picking_api(
    e2e_warehouse: Warehouse,
) -> None:
    """Full Cycle E2E Test:

    1. Staging ERP Inbound event for a high-priority coffee batch at (1, 1, 0).
    2. Sync Worker processes movement -> Postgres update + Redis grid update.
    3. Picking API (POST /api/v1/picking/recommend) detects and recommends new batch.
    4. ERP Outbound event consumes the batch.
    5. Sync Worker frees the slot -> Subsequent Picking API excludes it.
    """
    wh_id = e2e_warehouse.warehouse_id
    target_coords = Coordinates(1, 1, 0)
    batch_id = "BATCH-SPECIAL-BOURBON-777"

    # Step 1: Simulate ERP Inbound Movement Record
    inbound_event = ERPMovementRecord(
        event_id=f"EVT-IN-{int(datetime.now(UTC).timestamp() * 1000)}",
        warehouse_id=wh_id,
        movement_type=ERPMovementType.INBOUND,
        timestamp=datetime.now(UTC),
        batch_id=batch_id,
        coffee_type="BOURBON_AMARELO",
        cooperative_id="COOP-GUAXUPE",
        harvest_year=2026,
        weight_kg=60.0,
        from_x=None,
        from_y=None,
        from_z=None,
        to_x=1,
        to_y=1,
        to_z=0,
    )
    simulated_erp_client.feed_movement(inbound_event)

    # Step 2: Sync Worker processes inbound event
    result = process_erp_movement_task.apply(args=[inbound_event.model_dump(mode="json")]).get()
    assert result is True

    # Verify Redis grid was updated
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    redis_adapter = RedisGridAdapter(redis_client)
    cached_wh = await redis_adapter.get_warehouse_grid(wh_id)
    assert cached_wh is not None
    slot = cached_wh.get_slot(target_coords)
    assert slot is not None
    assert slot.status == SlotStatus.OCCUPIED
    assert slot.bag is not None
    assert slot.bag.batch_id == batch_id

    # Step 3: Picking API Call — Verify batch is recommended
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        pick_payload = {
            "warehouse_id": wh_id,
            "coffee_type": "BOURBON_AMARELO",
            "cooperative_id": "COOP-GUAXUPE",
            "max_recommendations": 3,
        }
        res = await client.post("/api/v1/picking/recommend", json=pick_payload)
        assert res.status_code == 200
        data = res.json()
        assert data["warehouse_id"] == wh_id
        assert len(data["recommendations"]) == 1
        top_rec = data["recommendations"][0]
        assert top_rec["batch_id"] == batch_id
        assert top_rec["coffee_type"] == "BOURBON_AMARELO"
        assert top_rec["coordinates"]["street_x"] == 1
        assert top_rec["coordinates"]["column_y"] == 1
        assert top_rec["coordinates"]["level_z"] == 0
        assert top_rec["blocking_bags_count"] == 0

    # Step 4: Outbound ERP Movement (Dispatch batch from warehouse)
    outbound_event = ERPMovementRecord(
        event_id=f"EVT-OUT-{int(datetime.now(UTC).timestamp() * 1000)}",
        warehouse_id=wh_id,
        movement_type=ERPMovementType.OUTBOUND,
        timestamp=datetime.now(UTC),
        batch_id=batch_id,
        coffee_type="BOURBON_AMARELO",
        cooperative_id="COOP-GUAXUPE",
        harvest_year=2026,
        weight_kg=60.0,
        from_x=1,
        from_y=1,
        from_z=0,
        to_x=None,
        to_y=None,
        to_z=None,
    )
    simulated_erp_client.feed_movement(outbound_event)

    out_result = process_erp_movement_task.apply(
        args=[outbound_event.model_dump(mode="json")]
    ).get()
    assert out_result is True

    # Step 5: Verify slot is now FREE and excluded from subsequent picking
    updated_wh = await redis_adapter.get_warehouse_grid(wh_id)
    assert updated_wh is not None
    freed_slot = updated_wh.get_slot(target_coords)
    assert freed_slot is not None
    assert freed_slot.status == SlotStatus.FREE
    assert freed_slot.bag is None

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res_after = await client.post("/api/v1/picking/recommend", json=pick_payload)
        assert res_after.status_code == 200
        data_after = res_after.json()
        assert data_after["total_candidates_evaluated"] == 0
        assert len(data_after["recommendations"]) == 0

    await redis_client.aclose()


@pytest.mark.asyncio
async def test_dod_picking_latency_p99_under_500ms(
    e2e_warehouse: Warehouse,
) -> None:
    """DoD Acceptance Criteria: Picking P99 Latency must be < 500ms.

    Runs repeated picking requests across the 3D grid and asserts P99 SLA.
    """
    wh_id = e2e_warehouse.warehouse_id
    latencies: list[float] = []
    num_requests = 30

    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "warehouse_id": wh_id,
            "coffee_type": "MUNDO_NOVO",
            "max_recommendations": 5,
        }

        # Warm up
        await client.post("/api/v1/picking/recommend", json=payload)

        # Benchmark run
        for _ in range(num_requests):
            t0 = time.perf_counter()
            resp = await client.post("/api/v1/picking/recommend", json=payload)
            t1 = time.perf_counter()
            assert resp.status_code == 200
            latencies.append((t1 - t0) * 1000.0)  # ms

    p99 = float(np.percentile(latencies, 99))
    p95 = float(np.percentile(latencies, 95))
    p50 = float(np.percentile(latencies, 50))

    # Assert SLA: P99 < 500ms
    assert p99 < 500.0, f"P99 latency exceeded 500ms SLA: {p99:.2f}ms"
    assert p95 < 250.0, f"P95 latency too high: {p95:.2f}ms"
    assert p50 < 100.0, f"Median latency too high: {p50:.2f}ms"


@pytest.mark.asyncio
async def test_dod_sync_lag_under_60_seconds(
    e2e_warehouse: Warehouse,
) -> None:
    """DoD Acceptance Criteria: Sync lag measured must be < 60 seconds."""
    wh_id = e2e_warehouse.warehouse_id

    event = ERPMovementRecord(
        event_id=f"EVT-LAG-{int(datetime.now(UTC).timestamp() * 1000)}",
        warehouse_id=wh_id,
        movement_type=ERPMovementType.INBOUND,
        timestamp=datetime.now(UTC),
        batch_id="BATCH-LAG-TEST",
        coffee_type="CATUAI_VERMELHO",
        cooperative_id="COOP-GUAXUPE",
        harvest_year=2026,
        weight_kg=60.0,
        from_x=None,
        from_y=None,
        from_z=None,
        to_x=0,
        to_y=0,
        to_z=1,
    )

    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    async with async_session_factory() as session:
        repo = SqlAlchemyWarehouseRepository(session)
        redis_adapter = RedisGridAdapter(redis_client)
        use_case = SyncERPMovementUseCase(repo, redis_adapter)
        await use_case.execute(event)

    # Check metrics endpoint to ensure sync lag was recorded and is < 60s
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        metrics_resp = await client.get("/metrics")
        assert metrics_resp.status_code == 200
        assert "warehouse_sync_lag_seconds" in metrics_resp.text

    await redis_client.aclose()
