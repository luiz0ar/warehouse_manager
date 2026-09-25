from typing import Protocol

from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot
from app.domain.models.warehouse import Warehouse


class WarehouseRepositoryPort(Protocol):
    """Port interface defining persistence operations for warehouses and inventory."""

    async def get_warehouse(self, warehouse_id: str) -> Warehouse | None:
        """Fetch warehouse entity with its slots and coffee bags populated."""
        ...

    async def save_warehouse(self, warehouse: Warehouse) -> None:
        """Save a new warehouse or update metadata."""
        ...

    async def update_slot(self, warehouse_id: str, slot: Slot) -> None:
        """Update or insert a slot and its associated coffee bag."""
        ...

    async def record_movement(
        self,
        warehouse_id: str,
        batch_id: str,
        movement_type: str,
        from_coords: Coordinates | None = None,
        to_coords: Coordinates | None = None,
    ) -> None:
        """Record an inventory movement event."""
        ...

    async def is_idempotency_key_registered(self, key: str) -> bool:
        """Check whether an idempotency key has already been processed."""
        ...

    async def register_idempotency_key(self, key: str, source: str = "LEGACY_ERP") -> None:
        """Register a processed idempotency key."""
        ...
