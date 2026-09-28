import time
from datetime import UTC, datetime
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.recommend_picking import RecommendPickingUseCase
from app.core.metrics import WAREHOUSE_PICKING_DURATION_SECONDS
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.cache.redis_grid_adapter import RedisGridAdapter
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import get_async_session
from app.presentation.api.v1.schemas.picking_dto import (
    CoordinatesDTO,
    PickingRecommendationItemDTO,
    PickingRequestDTO,
    PickingResponseDTO,
)

router = APIRouter(prefix="/picking", tags=["Picking"])


@router.post(
    "/recommend",
    response_model=PickingResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="Recommend optimal picking route",
    description="Calculates lowest cost route evaluating 3D distance and rehandling penalties.",
)
async def recommend_picking(
    payload: PickingRequestDTO,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    redis_client: Annotated[aioredis.Redis[bytes], Depends(get_redis_client)],
) -> PickingResponseDTO:
    repository = SqlAlchemyWarehouseRepository(session)
    grid_cache = RedisGridAdapter(redis_client)
    use_case = RecommendPickingUseCase(repository=repository, grid_cache=grid_cache)

    start_time = time.perf_counter()
    try:
        warehouse, recommendations = await use_case.execute(
            warehouse_id=payload.warehouse_id,
            coffee_type=payload.coffee_type,
            cooperative_id=payload.cooperative_id,
            max_recommendations=payload.max_recommendations,
        )
        duration = time.perf_counter() - start_time
        WAREHOUSE_PICKING_DURATION_SECONDS.labels(
            warehouse_id=payload.warehouse_id, status="success"
        ).observe(duration)
    except Exception:
        duration = time.perf_counter() - start_time
        WAREHOUSE_PICKING_DURATION_SECONDS.labels(
            warehouse_id=payload.warehouse_id, status="error"
        ).observe(duration)
        raise

    items = [
        PickingRecommendationItemDTO(
            rank=i + 1,
            batch_id=cand.batch_id,
            coordinates=CoordinatesDTO(
                street_x=cand.coordinates.x,
                column_y=cand.coordinates.y,
                level_z=cand.coordinates.z,
            ),
            distance_to_dock=cand.distance,
            blocking_bags_count=cand.blocking_bags,
            estimated_cost=cand.total_cost,
            coffee_type=cand.coffee_type,
            cooperative_id=cand.cooperative_id,
        )
        for i, cand in enumerate(recommendations)
    ]

    return PickingResponseDTO(
        warehouse_id=warehouse.warehouse_id,
        generated_at=datetime.now(UTC),
        total_candidates_evaluated=len(recommendations),
        recommendations=items,
    )
