from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CoffeeBag:
    """Representation of a coffee bag/batch stored in the system."""

    batch_id: str
    cooperative_id: str
    coffee_type: str
    harvest_year: int
    entry_date: datetime
    weight_kg: float = 60.0

    def __post_init__(self) -> None:
        if not self.batch_id.strip():
            raise ValueError("batch_id cannot be empty.")
        if not self.cooperative_id.strip():
            raise ValueError("cooperative_id cannot be empty.")
        if not self.coffee_type.strip():
            raise ValueError("coffee_type cannot be empty.")
        if self.weight_kg <= 0:
            raise ValueError("weight_kg must be strictly positive.")
