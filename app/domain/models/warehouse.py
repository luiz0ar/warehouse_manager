from dataclasses import dataclass, field

from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot


@dataclass(slots=True)
class Warehouse:
    """Domain entity representing a coffee warehouse and its geometric bounds."""

    warehouse_id: str
    name: str
    total_streets: int  # N_STREETS (X axis)
    total_columns: int  # N_COLUMNS (Y axis)
    total_levels: int   # N_LEVELS (Z axis)
    dock_coordinates: Coordinates = field(default_factory=lambda: Coordinates(0, 0, 0))
    slots: dict[Coordinates, Slot] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.total_streets <= 0:
            raise ValueError("total_streets must be greater than zero.")
        if self.total_columns <= 0:
            raise ValueError("total_columns must be greater than zero.")
        if self.total_levels <= 0:
            raise ValueError("total_levels must be greater than zero.")
        if not self.is_within_bounds(self.dock_coordinates):
            raise ValueError(
                f"Dock coordinates {self.dock_coordinates} are outside warehouse bounds."
            )

    def is_within_bounds(self, coordinates: Coordinates) -> bool:
        """Check whether coordinates lie within operational geometric bounds."""
        return (
            0 <= coordinates.x < self.total_streets
            and 0 <= coordinates.y < self.total_columns
            and 0 <= coordinates.z < self.total_levels
        )

    def get_slot(self, coordinates: Coordinates) -> Slot | None:
        """Retrieve the slot for given coordinates if it exists."""
        return self.slots.get(coordinates)

    def set_slot(self, slot: Slot) -> None:
        """Store or update a slot in the warehouse after bounds verification."""
        if not self.is_within_bounds(slot.coordinates):
            raise ValueError(
                f"Coordinates {slot.coordinates} exceed the configured bounds for this warehouse."
            )
        self.slots[slot.coordinates] = slot
