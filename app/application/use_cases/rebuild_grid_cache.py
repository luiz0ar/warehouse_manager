from app.application.ports.grid_cache_port import GridCachePort
from app.application.ports.warehouse_repository_port import WarehouseRepositoryPort
from app.domain.models.warehouse import Warehouse


class RebuildGridCacheUseCase:
    """Cold Start Use Case: Reconstructs the in-memory Redis 3D grid from PostgreSQL."""

    def __init__(
        self,
        repository: WarehouseRepositoryPort,
        grid_cache: GridCachePort,
    ) -> None:
        self.repository = repository
        self.grid_cache = grid_cache

    async def execute(self, warehouse_id: str) -> Warehouse | None:
        """Fetch warehouse ground truth from PostgreSQL and repopulate Redis cache."""
        warehouse = await self.repository.get_warehouse(warehouse_id)
        if warehouse is None:
            return None

        # Repopulate Redis cache atomically
        await self.grid_cache.set_warehouse_grid(warehouse)
        return warehouse
