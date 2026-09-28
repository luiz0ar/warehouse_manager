from fastapi import APIRouter

from app.presentation.api.v1.endpoints.picking import router as picking_router
from app.presentation.api.v1.endpoints.warehouse import router as warehouse_router

api_v1_router = APIRouter()
api_v1_router.include_router(picking_router)
api_v1_router.include_router(warehouse_router)
