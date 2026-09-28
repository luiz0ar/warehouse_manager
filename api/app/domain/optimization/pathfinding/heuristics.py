from typing import Protocol

from app.domain.models.coordinates import Coordinates


class HeuristicFunction(Protocol):
    """Protocol defining the interface for an admissible A* heuristic function."""

    def __call__(self, current: Coordinates, goal: Coordinates) -> float: ...


def manhattan_distance_heuristic(current: Coordinates, goal: Coordinates) -> float:
    """Standard 3D Manhattan distance heuristic (|dx| + |dy| + |dz|).

    Admissibility:
    Guaranteed admissible (h(n) <= h*(n)) because any physical movement on a grid
    requires at least |dx| + |dy| steps on the floor and |dz| vertical steps.
    Because physical racks impose obstacle detours, the true cost h*(n) is always
    greater than or equal to pure Manhattan distance.
    """
    return float(abs(current.x - goal.x) + abs(current.y - goal.y) + abs(current.z - goal.z))


def corridor_aware_heuristic(
    current: Coordinates,
    goal: Coordinates,
    cross_aisles: set[int] | None = None,
) -> float:
    """Corridor-aware admissible heuristic.

    If current and goal are in different streets (current.x != goal.x), the forklift
    MUST detour through the nearest reachable cross-aisle.
    If no cross-aisles are specified or both are in the same street, falls back to Manhattan.
    """
    base_vertical = float(abs(current.z - goal.z))
    if current.x == goal.x or not cross_aisles:
        return float(abs(current.x - goal.x) + abs(current.y - goal.y)) + base_vertical

    # Minimum detour to any cross-aisle Y:
    # Cost = min_{ca in cross_aisles} (|current.y - ca| + |current.x - goal.x| + |goal.y - ca|)
    min_detour = min(
        abs(current.y - ca) + abs(current.x - goal.x) + abs(goal.y - ca) for ca in cross_aisles
    )
    return float(min_detour) + base_vertical
