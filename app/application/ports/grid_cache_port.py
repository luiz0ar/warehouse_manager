from typing import Any, Protocol

from app.domain.models.warehouse import Warehouse


class GridCachePort(Protocol):
    """Port interface defining caching and serialization operations for the 3D grid in Redis."""

    async def set_warehouse_grid(self, warehouse: Warehouse) -> None:
        """Serialize and cache the 3D warehouse state in Redis."""
        ...

    async def get_warehouse_grid(self, warehouse_id: str) -> Warehouse | None:
        """Deserialize and retrieve the full 3D warehouse state from Redis."""
        ...

    async def publish_event(self, channel: str, message: dict[str, Any]) -> None:
        """Publish a real-time event via Redis Pub/Sub."""
        ...

    async def invalidate_warehouse_grid(self, warehouse_id: str) -> None:
        """Evict the cached grid for a warehouse."""
        ...
