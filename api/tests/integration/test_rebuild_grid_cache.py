from datetime import UTC, datetime

import pytest
import redis.asyncio as aioredis

from app.application.use_cases.rebuild_grid_cache import RebuildGridCacheUseCase
from app.core.config import settings
from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse
from app.infrastructure.cache.redis_grid_adapter import RedisGridAdapter
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import async_session_factory


@pytest.mark.asyncio
async def test_cold_start_rebuild_grid_cache() -> None:
    warehouse_id = f"WH-COLD-{int(datetime.now(UTC).timestamp())}"

    # 1. Setup in PostgreSQL
    warehouse = Warehouse(
        warehouse_id=warehouse_id,
        name="Cold Start Warehouse",
        total_streets=4,
        total_columns=4,
        total_levels=3,
        dock_coordinates=Coordinates(0, 0, 0),
    )
    bag = CoffeeBag(
        batch_id="BATCH-COLD-1",
        cooperative_id="COOP-ALTA-MOGIANA",
        coffee_type="MUNDO_NOVO",
        harvest_year=2026,
        entry_date=datetime.now(UTC),
    )
    warehouse.set_slot(Slot(Coordinates(2, 2, 1), SlotStatus.OCCUPIED, bag=bag))

    async with async_session_factory() as session:
        repo = SqlAlchemyWarehouseRepository(session)
        await repo.save_warehouse(warehouse)

    # 2. Ensure Redis has no cache for this warehouse (simulating cold start / Redis wipe)
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    grid_cache = RedisGridAdapter(redis_client)
    await grid_cache.invalidate_warehouse_grid(warehouse_id)
    assert await grid_cache.get_warehouse_grid(warehouse_id) is None

    try:
        # 3. Execute Cold Start Use Case
        async with async_session_factory() as session:
            repo = SqlAlchemyWarehouseRepository(session)
            use_case = RebuildGridCacheUseCase(repository=repo, grid_cache=grid_cache)
            rebuilt = await use_case.execute(warehouse_id)

            assert rebuilt is not None
            assert rebuilt.warehouse_id == warehouse_id

        # 4. Verify Redis now holds the full 3D grid state
        cached_warehouse = await grid_cache.get_warehouse_grid(warehouse_id)
        assert cached_warehouse is not None
        assert cached_warehouse.warehouse_id == warehouse_id

        cached_slot = cached_warehouse.get_slot(Coordinates(2, 2, 1))
        assert cached_slot is not None
        assert cached_slot.status == SlotStatus.OCCUPIED
        assert cached_slot.bag is not None
        assert cached_slot.bag.batch_id == "BATCH-COLD-1"
        assert cached_slot.bag.coffee_type == "MUNDO_NOVO"

    finally:
        await redis_client.aclose()
