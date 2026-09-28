from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse
from app.infrastructure.database.models import (
    CoffeeBatchModel,
    IdempotencyKeyModel,
    InventoryMovementModel,
    SlotModel,
    WarehouseModel,
)


class SqlAlchemyWarehouseRepository:
    """SQLAlchemy 2.0 asynchronous implementation of WarehouseRepositoryPort."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_warehouse(self, warehouse_id: str) -> Warehouse | None:
        """Fetch warehouse entity with all its slots and coffee bags populated."""
        query = (
            select(WarehouseModel)
            .where(WarehouseModel.id == warehouse_id)
            .options(selectinload(WarehouseModel.slots).selectinload(SlotModel.coffee_batch))
        )
        result = await self.session.execute(query)
        wh_model = result.scalar_one_or_none()

        if wh_model is None:
            return None

        warehouse = Warehouse(
            warehouse_id=wh_model.id,
            name=wh_model.name,
            total_streets=wh_model.total_streets,
            total_columns=wh_model.total_columns,
            total_levels=wh_model.total_levels,
            dock_coordinates=Coordinates(x=wh_model.dock_x, y=wh_model.dock_y, z=wh_model.dock_z),
        )

        for s_model in wh_model.slots:
            bag = None
            if s_model.coffee_batch is not None:
                bag = CoffeeBag(
                    batch_id=s_model.coffee_batch.batch_id,
                    cooperative_id=s_model.coffee_batch.cooperative_id,
                    coffee_type=s_model.coffee_batch.coffee_type,
                    harvest_year=s_model.coffee_batch.harvest_year,
                    entry_date=s_model.coffee_batch.entry_date,
                    weight_kg=s_model.coffee_batch.weight_kg,
                )

            slot = Slot(
                coordinates=Coordinates(x=s_model.x, y=s_model.y, z=s_model.z),
                status=SlotStatus(s_model.status),
                bag=bag,
            )
            warehouse.set_slot(slot)

        return warehouse

    async def save_warehouse(self, warehouse: Warehouse) -> None:
        """Create or update warehouse record and its slots."""
        query = select(WarehouseModel).where(WarehouseModel.id == warehouse.warehouse_id)
        result = await self.session.execute(query)
        wh_model = result.scalar_one_or_none()

        if wh_model is None:
            wh_model = WarehouseModel(
                id=warehouse.warehouse_id,
                name=warehouse.name,
                total_streets=warehouse.total_streets,
                total_columns=warehouse.total_columns,
                total_levels=warehouse.total_levels,
                dock_x=warehouse.dock_coordinates.x,
                dock_y=warehouse.dock_coordinates.y,
                dock_z=warehouse.dock_coordinates.z,
            )
            self.session.add(wh_model)
            await self.session.flush()

        for slot in warehouse.slots.values():
            await self.update_slot(warehouse.warehouse_id, slot)

        await self.session.commit()

    async def update_slot(self, warehouse_id: str, slot: Slot) -> None:
        """Update or insert an individual slot and its coffee bag."""
        query = select(SlotModel).where(
            SlotModel.warehouse_id == warehouse_id,
            SlotModel.x == slot.coordinates.x,
            SlotModel.y == slot.coordinates.y,
            SlotModel.z == slot.coordinates.z,
        )
        result = await self.session.execute(query)
        s_model = result.scalar_one_or_none()

        batch_model: CoffeeBatchModel | None = None
        if s_model is None:
            s_model = SlotModel(
                warehouse_id=warehouse_id,
                x=slot.coordinates.x,
                y=slot.coordinates.y,
                z=slot.coordinates.z,
                status=slot.status.value,
            )
            self.session.add(s_model)
            await self.session.flush()
        else:
            s_model.status = slot.status.value
            batch_query = select(CoffeeBatchModel).where(CoffeeBatchModel.slot_id == s_model.id)
            batch_res = await self.session.execute(batch_query)
            batch_model = batch_res.scalar_one_or_none()

        if slot.bag is not None:
            if batch_model is None:
                existing_batch_query = select(CoffeeBatchModel).where(
                    CoffeeBatchModel.batch_id == slot.bag.batch_id
                )
                existing_batch_res = await self.session.execute(existing_batch_query)
                existing_batch = existing_batch_res.scalar_one_or_none()

                if existing_batch is not None:
                    existing_batch.slot_id = s_model.id
                    existing_batch.cooperative_id = slot.bag.cooperative_id
                    existing_batch.coffee_type = slot.bag.coffee_type
                    existing_batch.harvest_year = slot.bag.harvest_year
                    existing_batch.entry_date = slot.bag.entry_date
                    existing_batch.weight_kg = slot.bag.weight_kg
                else:
                    new_batch = CoffeeBatchModel(
                        batch_id=slot.bag.batch_id,
                        slot_id=s_model.id,
                        cooperative_id=slot.bag.cooperative_id,
                        coffee_type=slot.bag.coffee_type,
                        harvest_year=slot.bag.harvest_year,
                        entry_date=slot.bag.entry_date,
                        weight_kg=slot.bag.weight_kg,
                    )
                    self.session.add(new_batch)
            else:
                batch_model.cooperative_id = slot.bag.cooperative_id
                batch_model.coffee_type = slot.bag.coffee_type
                batch_model.harvest_year = slot.bag.harvest_year
                batch_model.entry_date = slot.bag.entry_date
                batch_model.weight_kg = slot.bag.weight_kg
        elif batch_model is not None:
            await self.session.delete(batch_model)

    async def record_movement(
        self,
        warehouse_id: str,
        batch_id: str,
        movement_type: str,
        from_coords: Coordinates | None = None,
        to_coords: Coordinates | None = None,
    ) -> None:
        """Record an inventory movement."""
        movement = InventoryMovementModel(
            warehouse_id=warehouse_id,
            batch_id=batch_id,
            movement_type=movement_type,
            from_x=from_coords.x if from_coords else None,
            from_y=from_coords.y if from_coords else None,
            from_z=from_coords.z if from_coords else None,
            to_x=to_coords.x if to_coords else None,
            to_y=to_coords.y if to_coords else None,
            to_z=to_coords.z if to_coords else None,
            timestamp=datetime.now(UTC),
        )
        self.session.add(movement)
        await self.session.commit()

    async def is_idempotency_key_registered(self, key: str) -> bool:
        """Check whether an idempotency key already exists."""
        query = select(IdempotencyKeyModel.key).where(IdempotencyKeyModel.key == key)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def register_idempotency_key(self, key: str, source: str = "LEGACY_ERP") -> None:
        """Register a new idempotency key."""
        entry = IdempotencyKeyModel(key=key, source=source, created_at=datetime.now(UTC))
        self.session.add(entry)
        await self.session.commit()
