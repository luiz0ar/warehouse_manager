from app.application.ports.grid_cache_port import GridCachePort
from app.application.ports.warehouse_repository_port import WarehouseRepositoryPort
from app.core.exceptions import WarehouseNotFoundError
from app.domain.models.picking_candidate import PickingCandidate
from app.domain.models.warehouse import Warehouse
from app.domain.optimization.picking_engine import PickingEngine


class RecommendPickingUseCase:
    """Application Use Case for generating optimal coffee picking recommendations."""

    def __init__(
        self,
        repository: WarehouseRepositoryPort,
        grid_cache: GridCachePort,
        picking_engine: PickingEngine | None = None,
    ) -> None:
        self.repository = repository
        self.grid_cache = grid_cache
        self.picking_engine = picking_engine or PickingEngine()

    async def execute(
        self,
        warehouse_id: str,
        coffee_type: str,
        cooperative_id: str | None = None,
        max_recommendations: int = 5,
    ) -> tuple[Warehouse, list[PickingCandidate]]:
        """Retrieve warehouse (via cache or database cold-start) and execute picking optimization."""
        warehouse = await self.grid_cache.get_warehouse_grid(warehouse_id)

        if warehouse is None:
            warehouse = await self.repository.get_warehouse(warehouse_id)
            if warehouse is None:
                raise WarehouseNotFoundError(warehouse_id)
            await self.grid_cache.set_warehouse_grid(warehouse)

        recommendations = self.picking_engine.recommend(
            warehouse=warehouse,
            coffee_type=coffee_type,
            cooperative_id=cooperative_id,
            max_recommendations=max_recommendations,
        )

        return warehouse, recommendations
