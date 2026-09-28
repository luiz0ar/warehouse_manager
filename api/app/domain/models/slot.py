from dataclasses import dataclass
from enum import StrEnum

from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates


class SlotStatus(StrEnum):
    """Operational status of a three-dimensional slot in the warehouse."""

    FREE = "FREE"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"


@dataclass(slots=True)
class Slot:
    """Individual physical slot in the 3D warehouse space."""

    coordinates: Coordinates
    status: SlotStatus = SlotStatus.FREE
    bag: CoffeeBag | None = None

    def __post_init__(self) -> None:
        if self.status == SlotStatus.OCCUPIED and self.bag is None:
            raise ValueError("A slot with OCCUPIED status must contain a CoffeeBag.")
        if self.status == SlotStatus.FREE and self.bag is not None:
            raise ValueError("A slot with FREE status cannot have an associated CoffeeBag.")

    @property
    def is_available(self) -> bool:
        """Indicate whether the slot is free to be used or reserved."""
        return self.status == SlotStatus.FREE

    @property
    def is_occupied(self) -> bool:
        """Indicate whether the slot is currently occupied by a coffee bag."""
        return self.status == SlotStatus.OCCUPIED
