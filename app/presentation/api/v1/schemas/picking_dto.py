from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CoordinatesDTO(BaseModel):
    """3D coordinates schema [street_x, column_y, level_z]."""

    model_config = ConfigDict(from_attributes=True)

    street_x: int = Field(..., ge=0, description="Operational street / aisle index")
    column_y: int = Field(..., ge=0, description="Column / depth index")
    level_z: int = Field(..., ge=0, description="Vertical stacking level index")


class PickingRequestDTO(BaseModel):
    """Input payload for picking route recommendation."""

    model_config = ConfigDict(extra="forbid")

    warehouse_id: str = Field(..., min_length=1, description="Unique warehouse identifier")
    coffee_type: str = Field(..., min_length=1, description="Coffee variety/type requested")
    cooperative_id: str | None = Field(
        default=None, description="Optional cooperative member filter"
    )
    max_recommendations: int = Field(
        default=5, ge=1, le=20, description="Maximum number of candidates to recommend"
    )


class PickingRecommendationItemDTO(BaseModel):
    """Ranked picking recommendation candidate."""

    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., ge=1, description="Greedy priority rank (1 = lowest cost)")
    batch_id: str = Field(..., description="Unique coffee lot / bag identifier")
    coordinates: CoordinatesDTO = Field(..., description="Physical coordinates in warehouse")
    distance_to_dock: float = Field(..., description="3D distance from dispatch dock")
    blocking_bags_count: int = Field(
        ..., ge=0, description="Number of obstructing bags directly above this slot"
    )
    estimated_cost: float = Field(
        ..., description="Evaluated cost function score Z = (alpha * D) + (beta * R)"
    )
    coffee_type: str = Field(..., description="Coffee type")
    cooperative_id: str = Field(..., description="Originating cooperative")


class PickingResponseDTO(BaseModel):
    """Output payload containing ranked picking recommendations."""

    model_config = ConfigDict(from_attributes=True)

    warehouse_id: str = Field(..., description="Warehouse identifier")
    generated_at: datetime = Field(..., description="Timestamp when route was calculated")
    total_candidates_evaluated: int = Field(
        ..., ge=0, description="Total matching batches evaluated"
    )
    recommendations: list[PickingRecommendationItemDTO] = Field(
        default_factory=list, description="Top ranked recommendations"
    )
