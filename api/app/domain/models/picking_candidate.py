from dataclasses import dataclass, field

from app.domain.models.coordinates import Coordinates


@dataclass(frozen=True, slots=True)
class PickingCandidate:
    """Picking recommendation candidate with evaluated costs, routing, and metadata."""

    batch_id: str
    coordinates: Coordinates
    distance: float
    blocking_bags: int
    total_cost: float
    coffee_type: str
    cooperative_id: str
    path: list[Coordinates] = field(default_factory=list)
    turn_count: int = 0
    travel_distance: float = 0.0
    vertical_distance: float = 0.0
