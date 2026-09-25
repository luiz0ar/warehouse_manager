from datetime import UTC, datetime

import numpy as np
import pytest

from app.domain.models.coffee_bag import CoffeeBag
from app.domain.models.coordinates import Coordinates
from app.domain.models.slot import Slot, SlotStatus
from app.domain.models.warehouse import Warehouse
from app.domain.optimization.cost_function import CostParameters
from app.domain.optimization.picking_engine import PickingEngine


@pytest.fixture
def empty_warehouse() -> Warehouse:
    return Warehouse(
        warehouse_id="WH-TEST",
        name="Test Warehouse",
        total_streets=5,
        total_columns=5,
        total_levels=4,
        dock_coordinates=Coordinates(0, 0, 0),
    )


def create_slot(
    x: int,
    y: int,
    z: int,
    batch_id: str,
    coffee_type: str = "ARABICA_SPECIAL",
    cooperative_id: str = "COOP-MINAS",
) -> Slot:
    bag = CoffeeBag(
        batch_id=batch_id,
        cooperative_id=cooperative_id,
        coffee_type=coffee_type,
        harvest_year=2026,
        entry_date=datetime.now(UTC),
    )
    return Slot(coordinates=Coordinates(x, y, z), status=SlotStatus.OCCUPIED, bag=bag)


def test_picking_empty_warehouse(empty_warehouse: Warehouse) -> None:
    engine = PickingEngine()
    recommendations = engine.recommend(
        warehouse=empty_warehouse, coffee_type="ARABICA_SPECIAL"
    )
    assert recommendations == []


def test_picking_no_matching_coffee_type(empty_warehouse: Warehouse) -> None:
    empty_warehouse.set_slot(create_slot(1, 1, 0, "B-1", coffee_type="ROBUSTA"))
    engine = PickingEngine()
    recommendations = engine.recommend(
        warehouse=empty_warehouse, coffee_type="ARABICA_SPECIAL"
    )
    assert recommendations == []


def test_rehandling_tensor_calculation() -> None:
    # 2 Streets, 2 Columns, 4 Levels
    occupied = np.zeros((2, 2, 4), dtype=bool)

    # Stack at position (0, 0) with 3 bags stacked (levels 0, 1, 2)
    occupied[0, 0, 0] = True
    occupied[0, 0, 1] = True
    occupied[0, 0, 2] = True
    # level 3 is empty

    rehandling = PickingEngine.compute_rehandling_tensor(occupied)

    # Level 0 has 2 bags above (levels 1 and 2)
    assert rehandling[0, 0, 0] == 2
    # Level 1 has 1 bag above (level 2)
    assert rehandling[0, 0, 1] == 1
    # Level 2 has 0 bags above
    assert rehandling[0, 0, 2] == 0
    # Level 3 has 0 bags above
    assert rehandling[0, 0, 3] == 0

    # Position (1, 1) completely empty should have 0 blockages
    assert np.all(rehandling[1, 1, :] == 0)


def test_picking_rehandling_priority_over_distance(empty_warehouse: Warehouse) -> None:
    """Validate that with beta >> alpha, retrieving from the top (no rehandling)

    is prioritized even if slightly further away than a batch buried on the
    ground with bags on top.
    """
    # Batch A: Close to dock (1, 1, 0), but with 2 bags blocking above
    empty_warehouse.set_slot(create_slot(1, 1, 0, "BATCH-FLOOR", coffee_type="ARABICA"))
    empty_warehouse.set_slot(create_slot(1, 1, 1, "OBSTACLE-1", coffee_type="OTHER"))
    empty_warehouse.set_slot(create_slot(1, 1, 2, "OBSTACLE-2", coffee_type="OTHER"))

    # Batch B: Slightly further away (2, 2, 1), but with no bags above
    empty_warehouse.set_slot(create_slot(2, 2, 1, "BATCH-TOP", coffee_type="ARABICA"))

    # alpha=1.0, beta=10.0
    # Batch A: Dock (0,0,0) -> Manhattan dist: 1+1+0 = 2. Rehandling: 2. Cost Z = (1*2) + (10*2) = 22.0
    # Batch B: Dock (0,0,0) -> Manhattan dist: 2+2+1 = 5. Rehandling: 0. Cost Z = (1*5) + (10*0) = 5.0
    engine = PickingEngine(CostParameters(alpha=1.0, beta=10.0))
    recs = engine.recommend(warehouse=empty_warehouse, coffee_type="ARABICA")

    assert len(recs) == 2
    assert recs[0].batch_id == "BATCH-TOP"
    assert recs[0].total_cost == 5.0
    assert recs[0].blocking_bags == 0

    assert recs[1].batch_id == "BATCH-FLOOR"
    assert recs[1].total_cost == 22.0
    assert recs[1].blocking_bags == 2


def test_picking_cooperative_filter(empty_warehouse: Warehouse) -> None:
    empty_warehouse.set_slot(
        create_slot(1, 0, 0, "BATCH-COOP-A", coffee_type="ARABICA", cooperative_id="COOP-A")
    )
    empty_warehouse.set_slot(
        create_slot(2, 0, 0, "BATCH-COOP-B", coffee_type="ARABICA", cooperative_id="COOP-B")
    )

    engine = PickingEngine()
    recs = engine.recommend(
        warehouse=empty_warehouse,
        coffee_type="ARABICA",
        cooperative_id="COOP-A",
    )

    assert len(recs) == 1
    assert recs[0].batch_id == "BATCH-COOP-A"
    assert recs[0].cooperative_id == "COOP-A"


def test_picking_max_recommendations_limit(empty_warehouse: Warehouse) -> None:
    for i in range(10):
        empty_warehouse.set_slot(
            create_slot(0, i % 5, i % 4, f"BATCH-{i}", coffee_type="ARABICA")
        )

    engine = PickingEngine()
    recs = engine.recommend(
        warehouse=empty_warehouse,
        coffee_type="ARABICA",
        max_recommendations=3,
    )

    assert len(recs) == 3


def test_picking_deterministic_tie_breaker(empty_warehouse: Warehouse) -> None:
    # Two symmetric batches with the exact same cost Z
    empty_warehouse.set_slot(create_slot(1, 2, 0, "BATCH-X", coffee_type="ARABICA"))
    empty_warehouse.set_slot(create_slot(2, 1, 0, "BATCH-Y", coffee_type="ARABICA"))

    engine = PickingEngine()
    recs = engine.recommend(warehouse=empty_warehouse, coffee_type="ARABICA")

    assert len(recs) == 2
    assert recs[0].total_cost == recs[1].total_cost
    # Deterministic tie-breaking by coordinate x
    assert recs[0].coordinates.x == 1
    assert recs[1].coordinates.x == 2


def test_picking_with_euclidean_distance(empty_warehouse: Warehouse) -> None:
    empty_warehouse.set_slot(create_slot(3, 4, 0, "BATCH-EUCLID", coffee_type="ARABICA"))
    # (3, 4, 0) to dock (0, 0, 0) -> sqrt(3^2 + 4^2) = 5.0
    engine = PickingEngine(use_euclidean_distance=True)
    recs = engine.recommend(warehouse=empty_warehouse, coffee_type="ARABICA")

    assert len(recs) == 1
    assert recs[0].distance == 5.0
