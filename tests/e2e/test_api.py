from datetime import UTC, datetime

import httpx
import pytest
from httpx import ASGITransport

from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse
from app.infrastructure.database.repositories import SqlAlchemyWarehouseRepository
from app.infrastructure.database.session import async_session_factory
from app.presentation.main import app


@pytest.mark.asyncio
async def test_health_check_endpoint() -> None:
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["database"] == "up"
        assert data["services"]["redis"] == "up"


@pytest.mark.asyncio
async def test_metrics_endpoint() -> None:
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert (
            "http_requests_total" in response.text or "python_gc_objects_collected" in response.text
        )


@pytest.mark.asyncio
async def test_correlation_id_header_propagation() -> None:
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Without incoming header -> auto-generated
        res1 = await client.get("/health")
        assert "X-Request-ID" in res1.headers
        assert len(res1.headers["X-Request-ID"]) > 10

        # With incoming custom header -> propagated
        custom_id = "custom-trace-id-12345"
        res2 = await client.get("/health", headers={"X-Request-ID": custom_id})
        assert res2.headers["X-Request-ID"] == custom_id


@pytest.mark.asyncio
async def test_warehouse_not_found_rfc7807() -> None:
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/warehouses/NON-EXISTENT-WH/grid")
        assert response.status_code == 404
        error = response.json()
        assert error["type"] == "https://errors.warehouse-manager.io/not-found"
        assert error["title"] == "Resource Not Found"
        assert error["status"] == 404
        assert "NON-EXISTENT-WH" in error["detail"]
        assert error["instance"] == "/api/v1/warehouses/NON-EXISTENT-WH/grid"


@pytest.mark.asyncio
async def test_picking_validation_error_rfc7807() -> None:
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Invalid payload: empty coffee_type and negative max_recommendations
        payload = {
            "warehouse_id": "WH-001",
            "coffee_type": "",
            "max_recommendations": -5,
        }
        response = await client.post("/api/v1/picking/recommend", json=payload)
        assert response.status_code == 422
        error = response.json()
        assert error["type"] == "https://errors.warehouse-manager.io/validation-error"
        assert error["title"] == "Validation Error"
        assert error["status"] == 422
        assert "invalid_params" in error


@pytest.mark.asyncio
async def test_picking_recommendation_and_grid_full_flow() -> None:
    warehouse_id = f"WH-API-FLOW-{int(datetime.now(UTC).timestamp())}"

    # 1. Seed database with warehouse and two coffee batches (top vs bottom of stack)
    warehouse = Warehouse(
        warehouse_id=warehouse_id,
        name="API Flow Warehouse",
        total_streets=4,
        total_columns=4,
        total_levels=3,
        dock_coordinates=Coordinates(0, 0, 0),
    )

    # Batch 1: Ground floor (1, 1, 0) with two bags on top (Rehandling = 2)
    bag_floor = CoffeeBag(
        batch_id=f"BATCH-FLOOR-{warehouse_id}",
        cooperative_id="COOP-API",
        coffee_type="CATUAI_AMARELO",
        harvest_year=2026,
        entry_date=datetime.now(UTC),
    )
    obstacle_1 = CoffeeBag(
        batch_id=f"OBS-1-{warehouse_id}",
        cooperative_id="COOP-API",
        coffee_type="OUTRO",
        harvest_year=2026,
        entry_date=datetime.now(UTC),
    )
    obstacle_2 = CoffeeBag(
        batch_id=f"OBS-2-{warehouse_id}",
        cooperative_id="COOP-API",
        coffee_type="OUTRO",
        harvest_year=2026,
        entry_date=datetime.now(UTC),
    )

    # Batch 2: Top floor (2, 2, 1) with NO bags on top (Rehandling = 0)
    bag_top = CoffeeBag(
        batch_id=f"BATCH-TOP-{warehouse_id}",
        cooperative_id="COOP-API",
        coffee_type="CATUAI_AMARELO",
        harvest_year=2026,
        entry_date=datetime.now(UTC),
    )

    warehouse.set_slot(Slot(Coordinates(1, 1, 0), SlotStatus.OCCUPIED, bag=bag_floor))
    warehouse.set_slot(Slot(Coordinates(1, 1, 1), SlotStatus.OCCUPIED, bag=obstacle_1))
    warehouse.set_slot(Slot(Coordinates(1, 1, 2), SlotStatus.OCCUPIED, bag=obstacle_2))
    warehouse.set_slot(Slot(Coordinates(2, 2, 1), SlotStatus.OCCUPIED, bag=bag_top))

    async with async_session_factory() as session:
        repo = SqlAlchemyWarehouseRepository(session)
        await repo.save_warehouse(warehouse)

    # 2. Call Picking Recommendation API
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "warehouse_id": warehouse_id,
            "coffee_type": "CATUAI_AMARELO",
            "cooperative_id": "COOP-API",
            "max_recommendations": 3,
        }
        res_picking = await client.post("/api/v1/picking/recommend", json=payload)
        assert res_picking.status_code == 200
        picking_data = res_picking.json()

        assert picking_data["warehouse_id"] == warehouse_id
        assert picking_data["total_candidates_evaluated"] == 2
        recommendations = picking_data["recommendations"]
        assert len(recommendations) == 2

        # Top ranked candidate MUST be the one with zero rehandling (BATCH-TOP)
        assert recommendations[0]["rank"] == 1
        assert recommendations[0]["batch_id"] == f"BATCH-TOP-{warehouse_id}"
        assert recommendations[0]["blocking_bags_count"] == 0
        assert recommendations[0]["estimated_cost"] < recommendations[1]["estimated_cost"]

        # Second ranked candidate is the one on the floor
        assert recommendations[1]["rank"] == 2
        assert recommendations[1]["batch_id"] == f"BATCH-FLOOR-{warehouse_id}"
        assert recommendations[1]["blocking_bags_count"] == 2

        # 3. Call Warehouse Grid Snapshot API
        res_grid = await client.get(f"/api/v1/warehouses/{warehouse_id}/grid")
        assert res_grid.status_code == 200
        grid_data = res_grid.json()

        assert grid_data["warehouse_id"] == warehouse_id
        assert grid_data["total_slots"] == 4 * 4 * 3  # 48
        assert grid_data["occupied_slots_count"] == 4
        assert len(grid_data["slots"]) == 4
