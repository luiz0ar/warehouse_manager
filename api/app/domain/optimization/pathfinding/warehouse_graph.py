from collections.abc import Sequence
from dataclasses import dataclass, field

from app.domain.models.coordinates import Coordinates
from app.domain.models.warehouse import Warehouse


@dataclass(slots=True)
class WarehouseGraph:
    """Operations Research navigation graph modeling the physical layout of a coffee warehouse.

    Topology Rules:
    1. Floor Transit (Z = 0): Forklifts and automated guided vehicles (AGVs) navigate
       through a network of street aisles and cross-aisles at ground level.
    2. Racks as Obstacles: Transit across streets (changing X) is strictly constrained
       to designated cross-aisles (e.g. front at Y=0, rear at Y=max). At intermediate
       columns, rack structures prevent lateral movement.
    3. Target Access Point: Every rack slot (x, y, z) is serviced from its ground
       access point (x, y, 0).
    4. Vertical Movement (Z > 0): Forklift mast elevation is executed after reaching
       the ground access point facing the target slot.
    """

    total_streets: int
    total_columns: int
    total_levels: int
    dock: Coordinates = field(default_factory=lambda: Coordinates(0, 0, 0))
    cross_aisles: set[int] = field(default_factory=set)
    blocked_nodes: set[Coordinates] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.total_streets <= 0 or self.total_columns <= 0 or self.total_levels <= 0:
            raise ValueError("All dimensions (streets, columns, levels) must be greater than zero.")

        # Default cross-aisles: Front cross-aisle (Y=0) and Rear cross-aisle (Y=total_columns - 1)
        if not self.cross_aisles:
            self.cross_aisles = {0, self.total_columns - 1}
        else:
            # Validate cross-aisles within column bounds
            for ca in self.cross_aisles:
                if not (0 <= ca < self.total_columns):
                    raise ValueError(
                        f"Cross-aisle column Y={ca} is outside bounds [0, {self.total_columns - 1}]."
                    )

        if not self.is_within_bounds(self.dock):
            raise ValueError(f"Dock {self.dock} is outside warehouse bounds.")

    def is_within_bounds(self, coords: Coordinates) -> bool:
        """Check whether the given coordinates lie within warehouse operational limits."""
        return (
            0 <= coords.x < self.total_streets
            and 0 <= coords.y < self.total_columns
            and 0 <= coords.z < self.total_levels
        )

    def is_cross_aisle(self, y: int) -> bool:
        """Return True if the column Y is designated as a traversable cross-aisle."""
        return y in self.cross_aisles

    def is_walkable(self, coords: Coordinates) -> bool:
        """Verify whether a cell is transit-accessible and not blocked."""
        return self.is_within_bounds(coords) and coords not in self.blocked_nodes

    def get_access_point(self, slot_coords: Coordinates) -> Coordinates:
        """Get the floor transit access point (Z=0) servicing the specified rack slot."""
        if not self.is_within_bounds(slot_coords):
            raise ValueError(f"Slot {slot_coords} is outside warehouse bounds.")
        return Coordinates(slot_coords.x, slot_coords.y, 0)

    def get_floor_neighbors(self, node: Coordinates) -> list[Coordinates]:
        """Return adjacent reachable transit nodes on the floor (Z = 0).

        Movement rules:
        - Longitudinal movement (along aisle in Y): Allowed for all Y if the target cell is walkable.
        - Lateral movement (across streets in X): ONLY permitted if the current node is in a
          designated cross-aisle, preventing illegal traversal through solid racks.
        """
        if node.z != 0:
            raise ValueError(f"Floor transit queries require Z=0, got {node}.")

        neighbors: list[Coordinates] = []

        # 1. Longitudinal movement (North / South along aisle)
        for dy in (-1, 1):
            next_y = node.y + dy
            if 0 <= next_y < self.total_columns:
                next_node = Coordinates(node.x, next_y, 0)
                if next_node not in self.blocked_nodes:
                    neighbors.append(next_node)

        # 2. Lateral movement (East / West across streets) - only in cross-aisles!
        if self.is_cross_aisle(node.y):
            for dx in (-1, 1):
                next_x = node.x + dx
                if 0 <= next_x < self.total_streets:
                    next_node = Coordinates(next_x, node.y, 0)
                    if next_node not in self.blocked_nodes:
                        neighbors.append(next_node)

        return neighbors

    def block_node(self, coords: Coordinates) -> None:
        """Add a transit node to the blocked list (e.g. temporary obstruction or spill)."""
        if not self.is_within_bounds(coords):
            raise ValueError(f"Cannot block out-of-bounds node {coords}.")
        self.blocked_nodes.add(coords)

    def unblock_node(self, coords: Coordinates) -> None:
        """Remove a transit node from the blocked list."""
        self.blocked_nodes.discard(coords)

    @classmethod
    def from_warehouse(
        cls,
        warehouse: Warehouse,
        cross_aisles: Sequence[int] | None = None,
        blocked_nodes: set[Coordinates] | None = None,
    ) -> "WarehouseGraph":
        """Factory constructor instantiating a WarehouseGraph from a domain Warehouse entity."""
        return cls(
            total_streets=warehouse.total_streets,
            total_columns=warehouse.total_columns,
            total_levels=warehouse.total_levels,
            dock=warehouse.dock_coordinates,
            cross_aisles=set(cross_aisles) if cross_aisles is not None else set(),
            blocked_nodes=blocked_nodes if blocked_nodes is not None else set(),
        )
