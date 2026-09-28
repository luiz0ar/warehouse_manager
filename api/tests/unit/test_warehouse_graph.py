import pytest

from app.domain.models.coordinates import Coordinates
from app.domain.models.warehouse import Warehouse
from app.domain.optimization.pathfinding.warehouse_graph import WarehouseGraph


@pytest.fixture
def standard_graph() -> WarehouseGraph:
    return WarehouseGraph(
        total_streets=4,
        total_columns=10,
        total_levels=4,
        dock=Coordinates(0, 0, 0),
    )


def test_warehouse_graph_default_initialization(standard_graph: WarehouseGraph) -> None:
    assert standard_graph.total_streets == 4
    assert standard_graph.total_columns == 10
    assert standard_graph.total_levels == 4
    assert standard_graph.dock == Coordinates(0, 0, 0)
    # Default cross-aisles: 0 (front) and 9 (rear)
    assert standard_graph.cross_aisles == {0, 9}
    assert standard_graph.blocked_nodes == set()


def test_warehouse_graph_invalid_dimensions() -> None:
    with pytest.raises(ValueError, match="must be greater than zero"):
        WarehouseGraph(total_streets=0, total_columns=10, total_levels=4)

    with pytest.raises(ValueError, match="must be greater than zero"):
        WarehouseGraph(total_streets=4, total_columns=-1, total_levels=4)


def test_warehouse_graph_invalid_dock() -> None:
    with pytest.raises(ValueError, match="outside warehouse bounds"):
        WarehouseGraph(
            total_streets=4,
            total_columns=10,
            total_levels=4,
            dock=Coordinates(5, 0, 0),
        )


def test_warehouse_graph_invalid_cross_aisles() -> None:
    with pytest.raises(ValueError, match="outside bounds"):
        WarehouseGraph(
            total_streets=4,
            total_columns=10,
            total_levels=4,
            cross_aisles={0, 15},
        )


def test_is_cross_aisle(standard_graph: WarehouseGraph) -> None:
    assert standard_graph.is_cross_aisle(0) is True
    assert standard_graph.is_cross_aisle(9) is True
    assert standard_graph.is_cross_aisle(1) is False
    assert standard_graph.is_cross_aisle(5) is False


def test_floor_neighbors_in_cross_aisle(standard_graph: WarehouseGraph) -> None:
    # At (0, 0, 0): Corner dock position
    # Can move North along aisle to (0, 1, 0) AND East across cross-aisle to (1, 0, 0)
    neighbors = standard_graph.get_floor_neighbors(Coordinates(0, 0, 0))
    expected = {Coordinates(0, 1, 0), Coordinates(1, 0, 0)}
    assert set(neighbors) == expected

    # In intermediate street at front cross-aisle (1, 0, 0)
    # Can move to (0, 0, 0), (2, 0, 0), and (1, 1, 0)
    neighbors_mid = standard_graph.get_floor_neighbors(Coordinates(1, 0, 0))
    expected_mid = {Coordinates(0, 0, 0), Coordinates(2, 0, 0), Coordinates(1, 1, 0)}
    assert set(neighbors_mid) == expected_mid


def test_floor_neighbors_inside_aisle_prevents_rack_collision(
    standard_graph: WarehouseGraph,
) -> None:
    # At (1, 5, 0): Deep inside aisle between racks
    # Racks are solid on both sides (X=0 and X=2), so lateral moves are prohibited!
    # Only longitudinal moves (along aisle) are valid: (1, 4, 0) and (1, 6, 0)
    neighbors = standard_graph.get_floor_neighbors(Coordinates(1, 5, 0))
    expected = {Coordinates(1, 4, 0), Coordinates(1, 6, 0)}
    assert set(neighbors) == expected
    assert Coordinates(0, 5, 0) not in neighbors
    assert Coordinates(2, 5, 0) not in neighbors


def test_intermediate_cross_aisle() -> None:
    # Warehouse with an extra cross-aisle in the middle (Column 5)
    graph = WarehouseGraph(
        total_streets=4,
        total_columns=10,
        total_levels=4,
        cross_aisles={0, 5, 9},
    )
    # Now at (1, 5, 0), lateral moves are enabled!
    neighbors = graph.get_floor_neighbors(Coordinates(1, 5, 0))
    expected = {
        Coordinates(1, 4, 0),
        Coordinates(1, 6, 0),
        Coordinates(0, 5, 0),
        Coordinates(2, 5, 0),
    }
    assert set(neighbors) == expected


def test_blocked_node_handling(standard_graph: WarehouseGraph) -> None:
    blocked = Coordinates(1, 1, 0)
    standard_graph.block_node(blocked)

    assert standard_graph.is_walkable(blocked) is False
    assert blocked in standard_graph.blocked_nodes

    # (1, 0, 0) should no longer have (1, 1, 0) as a neighbor
    neighbors = standard_graph.get_floor_neighbors(Coordinates(1, 0, 0))
    assert blocked not in neighbors

    # Unblock
    standard_graph.unblock_node(blocked)
    assert standard_graph.is_walkable(blocked) is True
    assert blocked in standard_graph.get_floor_neighbors(Coordinates(1, 0, 0))


def test_block_invalid_node(standard_graph: WarehouseGraph) -> None:
    with pytest.raises(ValueError, match="Cannot block out-of-bounds"):
        standard_graph.block_node(Coordinates(10, 10, 0))


def test_get_access_point(standard_graph: WarehouseGraph) -> None:
    slot = Coordinates(2, 7, 3)
    access = standard_graph.get_access_point(slot)
    assert access == Coordinates(2, 7, 0)

    with pytest.raises(ValueError, match="outside warehouse bounds"):
        standard_graph.get_access_point(Coordinates(10, 10, 10))


def test_floor_neighbors_requires_z_zero(standard_graph: WarehouseGraph) -> None:
    with pytest.raises(ValueError, match="Floor transit queries require Z=0"):
        standard_graph.get_floor_neighbors(Coordinates(1, 1, 2))


def test_from_warehouse_factory() -> None:
    warehouse = Warehouse(
        warehouse_id="WH-MOCK-01",
        name="Mock Warehouse",
        total_streets=6,
        total_columns=12,
        total_levels=5,
        dock_coordinates=Coordinates(0, 0, 0),
    )
    graph = WarehouseGraph.from_warehouse(warehouse, cross_aisles=[0, 6, 11])

    assert graph.total_streets == 6
    assert graph.total_columns == 12
    assert graph.total_levels == 5
    assert graph.cross_aisles == {0, 6, 11}
