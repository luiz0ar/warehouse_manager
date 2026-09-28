from datetime import UTC, datetime

import pytest

from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import async_session_factory


@pytest.mark.asyncio
async def test_warehouse_repository_lifecycle() -> None:
    warehouse_id = f"WH-TEST-{int(datetime.now(UTC).timestamp())}"

    # 1. Instantiate Warehouse Domain Entity
    warehouse = Warehouse(
        warehouse_id=warehouse_id,
        name="Test Integration Warehouse",
        total_streets=3,
        total_columns=4,
        total_levels=2,
        dock_coordinates=Coordinates(0, 0, 0),
    )

    bag = CoffeeBag(
        batch_id=f"BATCH-{warehouse_id}",
        cooperative_id="COOP-CERRADO",
        coffee_type="BOURBON_AMARELO",
        harvest_year=2026,
        entry_date=datetime.now(UTC),
        weight_kg=60.0,
    )

    slot_occupied = Slot(
        coordinates=Coordinates(1, 2, 0),
        status=SlotStatus.OCCUPIED,
        bag=bag,
    )
    slot_free = Slot(
        coordinates=Coordinates(0, 1, 0),
        status=SlotStatus.FREE,
    )

    warehouse.set_slot(slot_occupied)
    warehouse.set_slot(slot_free)

    # 2. Save via SqlAlchemyWarehouseRepository
    async with async_session_factory() as session:
        repo = SqlAlchemyWarehouseRepository(session)
        await repo.save_warehouse(warehouse)

    # 3. Retrieve and Verify
    async with async_session_factory() as session:
        repo = SqlAlchemyWarehouseRepository(session)
        loaded = await repo.get_warehouse(warehouse_id)

        assert loaded is not None
        assert loaded.warehouse_id == warehouse_id
        assert loaded.name == "Test Integration Warehouse"
        assert loaded.dock_coordinates == Coordinates(0, 0, 0)
        assert len(loaded.slots) == 2

        loaded_occupied = loaded.get_slot(Coordinates(1, 2, 0))
        assert loaded_occupied is not None
        assert loaded_occupied.status == SlotStatus.OCCUPIED
        assert loaded_occupied.bag is not None
        assert loaded_occupied.bag.batch_id == f"BATCH-{warehouse_id}"
        assert loaded_occupied.bag.coffee_type == "BOURBON_AMARELO"

        loaded_free = loaded.get_slot(Coordinates(0, 1, 0))
        assert loaded_free is not None
        assert loaded_free.status == SlotStatus.FREE
        assert loaded_free.bag is None


@pytest.mark.asyncio
async def test_warehouse_repository_idempotency_and_movements() -> None:
    key = f"IDEMPOTENCY-{int(datetime.now(UTC).timestamp())}"
    warehouse_id = f"WH-MOVEMENTS-{int(datetime.now(UTC).timestamp())}"

    wh = Warehouse(
        warehouse_id=warehouse_id,
        name="Movements Warehouse",
        total_streets=2,
        total_columns=2,
        total_levels=2,
        dock_coordinates=Coordinates(0, 0, 0),
    )

    async with async_session_factory() as session:
        repo = SqlAlchemyWarehouseRepository(session)
        await repo.save_warehouse(wh)

        # Idempotency key check before registration
        assert not await repo.is_idempotency_key_registered(key)

        # Register key
        await repo.register_idempotency_key(key, source="LEGACY_ERP")

        # Idempotency key check after registration
        assert await repo.is_idempotency_key_registered(key)

        # Record movement
        await repo.record_movement(
            warehouse_id=warehouse_id,
            batch_id="BATCH-001",
            movement_type="PICKING",
            from_coords=Coordinates(1, 1, 1),
            to_coords=Coordinates(0, 0, 0),
        )
