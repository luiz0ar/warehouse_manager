from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.presentation.api.v1.schemas.picking_dto import CoordinatesDTO


class BatchSnapshotDTO(BaseModel):
    """Snapshot of a coffee batch within a slot."""

    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    cooperative_id: str
    coffee_type: str
    harvest_year: int
    entry_date: datetime
    weight_kg: float


class SlotSnapshotDTO(BaseModel):
    """Snapshot representation of an individual warehouse slot."""

    model_config = ConfigDict(from_attributes=True)

    coordinates: CoordinatesDTO
    status: str
    batch: BatchSnapshotDTO | None = None


class WarehouseGridSnapshotDTO(BaseModel):
    """Complete 3D warehouse layout snapshot for dashboard rendering."""

    model_config = ConfigDict(from_attributes=True)

    warehouse_id: str
    name: str
    total_streets: int
    total_columns: int
    total_levels: int
    dock_coordinates: CoordinatesDTO
    total_slots: int = Field(..., description="Total geometric capacity (X * Y * Z)")
    occupied_slots_count: int
    free_slots_count: int
    slots: list[SlotSnapshotDTO]
