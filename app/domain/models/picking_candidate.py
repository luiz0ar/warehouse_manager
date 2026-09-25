from dataclasses import dataclass

from app.domain.models.coordinates import Coordinates


@dataclass(frozen=True, slots=True)
class PickingCandidate:
    """Picking recommendation candidate with evaluated costs and metadata."""

    batch_id: str
    coordinates: Coordinates
    distance: float
    blocking_bags: int
    total_cost: float
    coffee_type: str
    cooperative_id: str
