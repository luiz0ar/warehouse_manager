from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import WarehouseNotFoundError
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.cache.redis_grid_adapter import RedisGridAdapter
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import get_async_session
from app.presentation.api.v1.schemas.picking_dto import CoordinatesDTO
from app.presentation.api.v1.schemas.warehouse_dto import (
    BatchSnapshotDTO,
    SlotSnapshotDTO,
    WarehouseGridSnapshotDTO,
)

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


@router.get(
    "/{warehouse_id}/grid",
    response_model=WarehouseGridSnapshotDTO,
    status_code=status.HTTP_200_OK,
    summary="Get 3D warehouse grid snapshot",
    description="Returns current 3D topology and occupied slots for static tablet dashboard rendering.",
)
async def get_warehouse_grid(
    warehouse_id: str,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    redis_client: Annotated[aioredis.Redis[bytes], Depends(get_redis_client)],
) -> WarehouseGridSnapshotDTO:
    grid_cache = RedisGridAdapter(redis_client)
    warehouse = await grid_cache.get_warehouse_grid(warehouse_id)

    if warehouse is None:
        repository = SqlAlchemyWarehouseRepository(session)
        warehouse = await repository.get_warehouse(warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(warehouse_id)
        await grid_cache.set_warehouse_grid(warehouse)

    total_capacity = warehouse.total_streets * warehouse.total_columns * warehouse.total_levels
    occupied_count = 0
    free_count = 0
    slots_dto: list[SlotSnapshotDTO] = []

    for coords, slot in warehouse.slots.items():
        if slot.is_occupied:
            occupied_count += 1
        elif slot.is_available:
            free_count += 1

        batch_dto = None
        if slot.bag is not None:
            batch_dto = BatchSnapshotDTO(
                batch_id=slot.bag.batch_id,
                cooperative_id=slot.bag.cooperative_id,
                coffee_type=slot.bag.coffee_type,
                harvest_year=slot.bag.harvest_year,
                entry_date=slot.bag.entry_date,
                weight_kg=slot.bag.weight_kg,
            )

        slots_dto.append(
            SlotSnapshotDTO(
                coordinates=CoordinatesDTO(street_x=coords.x, column_y=coords.y, level_z=coords.z),
                status=slot.status.value,
                batch=batch_dto,
            )
        )

    return WarehouseGridSnapshotDTO(
        warehouse_id=warehouse.warehouse_id,
        name=warehouse.name,
        total_streets=warehouse.total_streets,
        total_columns=warehouse.total_columns,
        total_levels=warehouse.total_levels,
        dock_coordinates=CoordinatesDTO(
            street_x=warehouse.dock_coordinates.x,
            column_y=warehouse.dock_coordinates.y,
            level_z=warehouse.dock_coordinates.z,
        ),
        total_slots=total_capacity,
        occupied_slots_count=occupied_count,
        free_slots_count=free_count,
        slots=slots_dto,
    )
