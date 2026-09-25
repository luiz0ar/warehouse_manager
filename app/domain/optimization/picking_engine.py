import numpy as np

from app.domain.models.picking_candidate import PickingCandidate
from app.domain.models.slot import SlotStatus
from app.domain.models.warehouse import Warehouse
from app.domain.optimization.cost_function import CostFunction, CostParameters


class PickingEngine:
    """Operations Research Heuristic Engine for Coffee Picking Optimization.

    Executes vectorized computations using NumPy to:
    1. Locate candidate nodes matching retrieval filters.
    2. Compute the 3D rehandling matrix (vertical obstructing bags).
    3. Evaluate three-dimensional distances to the dispatch dock.
    4. Apply the linear cost function Z = (alpha * D) + (beta * R).
    5. Execute Greedy Sort to return the Top-K lowest operational cost nodes.
    """

    def __init__(
        self,
        cost_parameters: CostParameters | None = None,
        use_euclidean_distance: bool = False,
    ) -> None:
        self.cost_function = CostFunction(cost_parameters)
        self.use_euclidean_distance = use_euclidean_distance

    @staticmethod
    def compute_rehandling_tensor(occupied_tensor: np.ndarray) -> np.ndarray:
        """Compute the 3D vertical obstructing bags tensor (Rehandling).

        For each node (x, y, z), rehandling is the count of bags present at
        (x, y, k) where k > z.

        Args:
            occupied_tensor: Boolean array with shape (X, Y, Z).

        Returns:
            Integer array with identical shape (X, Y, Z) containing blocking counts.
        """
        rehandling = np.zeros_like(occupied_tensor, dtype=np.int32)
        total_levels = occupied_tensor.shape[2]

        # Descending accumulation along the Z axis (height)
        # rehandling[..., z] = sum of occupied[..., z+1:]
        running_sum = np.zeros(occupied_tensor.shape[:2], dtype=np.int32)
        for z in range(total_levels - 1, -1, -1):
            rehandling[:, :, z] = running_sum
            running_sum += occupied_tensor[:, :, z].astype(np.int32)

        return rehandling

    def recommend(
        self,
        warehouse: Warehouse,
        coffee_type: str,
        cooperative_id: str | None = None,
        max_recommendations: int = 5,
    ) -> list[PickingCandidate]:
        """Generate an ordered list with the best picking recommendations.

        Args:
            warehouse: Warehouse with populated slots.
            coffee_type: Coffee type requested by the operator.
            cooperative_id: Optional filter for a specific cooperative.
            max_recommendations: Maximum number of recommendations (e.g. 3 to 5).

        Returns:
            List of PickingCandidate sorted by lowest cost Z (Greedy Sort).
        """
        shape = (warehouse.total_streets, warehouse.total_columns, warehouse.total_levels)

        # 1. Build in-memory occupation tensor
        occupied_tensor = np.zeros(shape, dtype=bool)
        candidates_raw = []

        for coords, slot in warehouse.slots.items():
            if slot.status == SlotStatus.OCCUPIED and slot.bag is not None:
                occupied_tensor[coords.x, coords.y, coords.z] = True

                # Check if slot matches picking criteria
                match_type = slot.bag.coffee_type == coffee_type
                match_coop = cooperative_id is None or slot.bag.cooperative_id == cooperative_id

                if match_type and match_coop:
                    candidates_raw.append((coords, slot.bag))

        if not candidates_raw:
            return []

        # 2. Compute warehouse rehandling tensor in a vectorized manner
        rehandling_tensor = self.compute_rehandling_tensor(occupied_tensor)

        # 3. Evaluate metrics for all matching candidates
        dock = warehouse.dock_coordinates
        evaluated: list[PickingCandidate] = []

        for coords, bag in candidates_raw:
            if self.use_euclidean_distance:
                distance = coords.euclidean_distance_to(dock)
            else:
                distance = coords.manhattan_distance_to(dock)

            blocking = int(rehandling_tensor[coords.x, coords.y, coords.z])
            cost = self.cost_function.calculate(distance=distance, blocking_bags=blocking)

            evaluated.append(
                PickingCandidate(
                    batch_id=bag.batch_id,
                    coordinates=coords,
                    distance=round(distance, 2),
                    blocking_bags=blocking,
                    total_cost=round(cost, 2),
                    coffee_type=bag.coffee_type,
                    cooperative_id=bag.cooperative_id,
                )
            )

        # 4. Greedy Sort: Lowest Cost Z, Lowest Rehandling, Lowest Distance
        evaluated.sort(
            key=lambda c: (
                c.total_cost,
                c.blocking_bags,
                c.distance,
                c.coordinates.x,
                c.coordinates.y,
                c.coordinates.z,
            )
        )

        return evaluated[:max_recommendations]
