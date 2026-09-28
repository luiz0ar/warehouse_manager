from datetime import UTC, datetime

import pytest
import redis.asyncio as aioredis

from app.core.config import settings
from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse
from app.infrastructure.cache.redis_grid_adapter import RedisGridAdapter


@pytest.mark.asyncio
async def test_redis_grid_adapter_lifecycle() -> None:
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=False)
    adapter = RedisGridAdapter(redis_client)

    warehouse_id = f"WH-REDIS-{int(datetime.now(UTC).timestamp())}"
    warehouse = Warehouse(
        warehouse_id=warehouse_id,
        name="Redis Test Warehouse",
        total_streets=2,
        total_columns=3,
        total_levels=2,
        dock_coordinates=Coordinates(0, 0, 0),
    )

    bag = CoffeeBag(
        batch_id="BATCH-REDIS-1",
        cooperative_id="COOP-SUL",
        coffee_type="CATUAI",
        harvest_year=2026,
        entry_date=datetime.now(UTC),
        weight_kg=60.0,
    )

    slot = Slot(
        coordinates=Coordinates(0, 1, 0),
        status=SlotStatus.OCCUPIED,
        bag=bag,
    )
    warehouse.set_slot(slot)

    try:
        await adapter.set_warehouse_grid(warehouse)

        loaded = await adapter.get_warehouse_grid(warehouse_id)
        assert loaded is not None
        assert loaded.warehouse_id == warehouse_id
        assert loaded.total_streets == 2
        assert loaded.dock_coordinates == Coordinates(0, 0, 0)

        loaded_slot = loaded.get_slot(Coordinates(0, 1, 0))
        assert loaded_slot is not None
        assert loaded_slot.status == SlotStatus.OCCUPIED
        assert loaded_slot.bag is not None
        assert loaded_slot.bag.batch_id == "BATCH-REDIS-1"
        assert loaded_slot.bag.coffee_type == "CATUAI"

        tensor = await adapter.get_occupied_tensor(warehouse_id)
        assert tensor is not None
        assert tensor.shape == (2, 3, 2)
        assert tensor[0, 1, 0]
        assert not tensor[0, 0, 0]

        await adapter.invalidate_warehouse_grid(warehouse_id)
        assert await adapter.get_warehouse_grid(warehouse_id) is None
        assert await adapter.get_occupied_tensor(warehouse_id) is None

    finally:
        await redis_client.close()


@pytest.mark.asyncio
async def test_redis_pub_sub_event() -> None:
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    adapter = RedisGridAdapter(redis_client)

    channel = "warehouse:events:test"
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        await adapter.publish_event(channel, {"event": "INVENTORY_SYNC", "batch_id": "BATCH-99"})
        sub_msg = await pubsub.get_message(ignore_subscribe_messages=False, timeout=2.0)
        assert sub_msg is not None
        assert sub_msg["type"] == "subscribe"

        event_msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=2.0)
        assert event_msg is not None
        assert "INVENTORY_SYNC" in event_msg["data"]

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis_client.close()
