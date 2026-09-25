from datetime import UTC, datetime

import structlog

from app.application.ports.grid_cache_port import GridCachePort
from app.application.ports.warehouse_repository_port import WarehouseRepositoryPort
from app.core.exceptions import WarehouseNotFoundError
from app.core.metrics import WAREHOUSE_SYNC_LAG_SECONDS, WAREHOUSE_SYNC_MOVEMENTS_TOTAL
from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.infrastructure.erp.models import ERPMovementRecord, ERPMovementType

logger = structlog.get_logger()


class SyncERPMovementUseCase:
    """Use case to process inventory movements from the legacy ERP with idempotency guarantees,

    updating both PostgreSQL ground truth and the in-memory Redis grid cache atomically,
    and notifying subscribers via Redis Pub/Sub.
    """

    def __init__(
        self,
        repository: WarehouseRepositoryPort,
        grid_cache: GridCachePort,
    ) -> None:
        self.repository = repository
        self.grid_cache = grid_cache

    async def execute(self, movement: ERPMovementRecord) -> bool:
        """Process an ERP movement record.

        Returns True if newly processed, False if skipped due to idempotency.
        """
        if await self.repository.is_idempotency_key_registered(movement.event_id):
            WAREHOUSE_SYNC_MOVEMENTS_TOTAL.labels(
                warehouse_id=movement.warehouse_id,
                movement_type=movement.movement_type.value,
                status="duplicate",
            ).inc()
            logger.info(
                "erp_movement_skipped_duplicate",
                event_id=movement.event_id,
                batch_id=movement.batch_id,
                warehouse_id=movement.warehouse_id,
            )
            return False

        warehouse = await self.repository.get_warehouse(movement.warehouse_id)
        if warehouse is None:
            logger.error("warehouse_not_found_for_sync", warehouse_id=movement.warehouse_id)
            raise WarehouseNotFoundError(movement.warehouse_id)

        if movement.movement_type == ERPMovementType.INBOUND:
            if movement.to_x is None or movement.to_y is None or movement.to_z is None:
                raise ValueError("Destination coordinates (to_x, to_y, to_z) required for INBOUND")

            to_coords = Coordinates(movement.to_x, movement.to_y, movement.to_z)
            bag = CoffeeBag(
                batch_id=movement.batch_id,
                cooperative_id=movement.cooperative_id,
                coffee_type=movement.coffee_type,
                harvest_year=movement.harvest_year,
                entry_date=movement.entry_date,
                weight_kg=movement.weight_kg,
            )
            slot = Slot(coordinates=to_coords, status=SlotStatus.OCCUPIED, bag=bag)
            warehouse.set_slot(slot)

            await self.repository.update_slot(warehouse.warehouse_id, slot)
            await self.repository.record_movement(
                warehouse_id=warehouse.warehouse_id,
                batch_id=movement.batch_id,
                movement_type="INBOUND",
                from_coords=None,
                to_coords=to_coords,
            )

        elif movement.movement_type == ERPMovementType.OUTBOUND:
            if movement.from_x is None or movement.from_y is None or movement.from_z is None:
                raise ValueError(
                    "Source coordinates (from_x, from_y, from_z) required for OUTBOUND"
                )

            from_coords = Coordinates(movement.from_x, movement.from_y, movement.from_z)
            slot = Slot(coordinates=from_coords, status=SlotStatus.FREE, bag=None)
            warehouse.set_slot(slot)

            await self.repository.update_slot(warehouse.warehouse_id, slot)
            await self.repository.record_movement(
                warehouse_id=warehouse.warehouse_id,
                batch_id=movement.batch_id,
                movement_type="OUTBOUND",
                from_coords=from_coords,
                to_coords=None,
            )

        elif movement.movement_type == ERPMovementType.INTERNAL_TRANSFER:
            if (
                movement.from_x is None
                or movement.from_y is None
                or movement.from_z is None
                or movement.to_x is None
                or movement.to_y is None
                or movement.to_z is None
            ):
                raise ValueError(
                    "Both source and destination coordinates required for INTERNAL_TRANSFER"
                )

            from_coords = Coordinates(movement.from_x, movement.from_y, movement.from_z)
            to_coords = Coordinates(movement.to_x, movement.to_y, movement.to_z)

            vacated_slot = Slot(coordinates=from_coords, status=SlotStatus.FREE, bag=None)
            bag = CoffeeBag(
                batch_id=movement.batch_id,
                cooperative_id=movement.cooperative_id,
                coffee_type=movement.coffee_type,
                harvest_year=movement.harvest_year,
                entry_date=movement.entry_date,
                weight_kg=movement.weight_kg,
            )
            occupied_slot = Slot(coordinates=to_coords, status=SlotStatus.OCCUPIED, bag=bag)

            warehouse.set_slot(vacated_slot)
            warehouse.set_slot(occupied_slot)

            await self.repository.update_slot(warehouse.warehouse_id, vacated_slot)
            await self.repository.update_slot(warehouse.warehouse_id, occupied_slot)
            await self.repository.record_movement(
                warehouse_id=warehouse.warehouse_id,
                batch_id=movement.batch_id,
                movement_type="INTERNAL_TRANSFER",
                from_coords=from_coords,
                to_coords=to_coords,
            )

        await self.repository.register_idempotency_key(movement.event_id, source="LEGACY_ERP")

        await self.grid_cache.set_warehouse_grid(warehouse)

        event_payload = {
            "event": "INVENTORY_SYNC",
            "event_id": movement.event_id,
            "warehouse_id": warehouse.warehouse_id,
            "batch_id": movement.batch_id,
            "movement_type": movement.movement_type.value,
            "from_coords": (
                [movement.from_x, movement.from_y, movement.from_z]
                if movement.from_x is not None
                else None
            ),
            "to_coords": (
                [movement.to_x, movement.to_y, movement.to_z] if movement.to_x is not None else None
            ),
            "timestamp": movement.timestamp.isoformat(),
        }

        channel = f"warehouse:{warehouse.warehouse_id}:events"
        await self.grid_cache.publish_event(channel, event_payload)
        await self.grid_cache.publish_event("inventory_events", event_payload)

        lag_seconds = max(0.0, (datetime.now(UTC) - movement.timestamp).total_seconds())
        WAREHOUSE_SYNC_LAG_SECONDS.labels(warehouse_id=warehouse.warehouse_id).set(lag_seconds)
        WAREHOUSE_SYNC_MOVEMENTS_TOTAL.labels(
            warehouse_id=warehouse.warehouse_id,
            movement_type=movement.movement_type.value,
            status="processed",
        ).inc()

        logger.info(
            "erp_movement_processed_successfully",
            event_id=movement.event_id,
            batch_id=movement.batch_id,
            warehouse_id=warehouse.warehouse_id,
            movement_type=movement.movement_type.value,
            lag_seconds=round(lag_seconds, 3),
        )

        return True
