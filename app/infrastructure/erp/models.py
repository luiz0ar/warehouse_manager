from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ERPMovementType(StrEnum):
    """Types of inventory movements coming from the legacy ERP."""

    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    INTERNAL_TRANSFER = "INTERNAL_TRANSFER"


class ERPMovementRecord(BaseModel):
    """Schema representing an immutable inventory movement event emitted by the ERP."""

    model_config = ConfigDict(frozen=True, from_attributes=True)

    event_id: str = Field(description="Unique event/transaction ID from the legacy ERP")
    warehouse_id: str = Field(description="Target warehouse identifier")
    batch_id: str = Field(description="Coffee batch unique code")
    cooperative_id: str = Field(description="Origin cooperative member identifier")
    coffee_type: str = Field(description="Variety / classification of coffee")
    harvest_year: int = Field(description="Harvest crop year")
    entry_date: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Original batch entry timestamp",
    )
    weight_kg: float = Field(default=60.0, description="Gross batch weight in kg")
    movement_type: ERPMovementType = Field(description="Classification of the inventory movement")
    from_x: int | None = Field(default=None, description="Source street coordinate X")
    from_y: int | None = Field(default=None, description="Source column coordinate Y")
    from_z: int | None = Field(default=None, description="Source level coordinate Z")
    to_x: int | None = Field(default=None, description="Destination street coordinate X")
    to_y: int | None = Field(default=None, description="Destination column coordinate Y")
    to_z: int | None = Field(default=None, description="Destination level coordinate Z")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of movement completion in ERP",
    )
