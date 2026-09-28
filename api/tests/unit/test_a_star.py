import pytest

from app.domain.models.coordinates import Coordinates
from app.domain.optimization.pathfinding.a_star import (
    AStarPathfinder,
    PathfindingParameters,
    PathNotFoundError,
)
from app.domain.optimization.pathfinding.heuristics import (
    corridor_aware_heuristic,
    manhattan_distance_heuristic,
)
from app.domain.optimization.pathfinding.warehouse_graph import WarehouseGraph


@pytest.fixture
def graph() -> WarehouseGraph:
    return WarehouseGraph(
        total_streets=4,
        total_columns=10,
        total_levels=4,
        dock=Coordinates(0, 0, 0),
    )


def test_a_star_same_start_and_goal(graph: WarehouseGraph) -> None:
    finder = AStarPathfinder(graph)
    target = Coordinates(0, 0, 0)
    result = finder.find_path(target, target)

    assert result.path == [target]
    assert result.total_cost == 0.0
    assert result.ground_distance == 0.0
    assert result.vertical_distance == 0.0
    assert result.turn_count == 0


def test_a_star_straight_line_path(graph: WarehouseGraph) -> None:
    finder = AStarPathfinder(graph)
    start = Coordinates(0, 0, 0)
    goal = Coordinates(0, 5, 0)

    result = finder.find_path(start, goal)

    assert result.path[0] == start
    assert result.path[-1] == goal
    assert len(result.path) == 6
    assert result.ground_distance == 5.0
    assert result.vertical_distance == 0.0
    assert result.turn_count == 0
    assert result.total_cost == 5.0


def test_a_star_cross_aisle_routing_and_rack_avoidance(graph: WarehouseGraph) -> None:
    # Starting at Street 0, Column 5, attempting to reach Street 2, Column 5.
    # Solid racks block lateral movement at Column 5.
    # Nearest cross-aisle is Column 9 (distance 4), whereas Column 0 is distance 5.
    # Optimal route detours through rear cross-aisle (Y=9):
    # (0,5) -> (0,6) -> (0,7) -> (0,8) -> (0,9) -> (1,9) -> (2,9) -> (2,8) -> (2,7) -> (2,6) -> (2,5)
    finder = AStarPathfinder(graph, parameters=PathfindingParameters(step_cost=1.0, turn_penalty=0.5))
    start = Coordinates(0, 5, 0)
    goal = Coordinates(2, 5, 0)

    result = finder.find_path(start, goal)

    assert result.path[0] == start
    assert result.path[-1] == goal
    assert result.ground_distance == 10.0  # 4 down + 2 across + 4 back
    assert result.turn_count == 2  # Turn into cross-aisle + turn into target street
    # Total cost = 10.0 (ground) + 2 * 0.5 (turns) = 11.0
    assert result.total_cost == 11.0

    # Ensure it detoured via Column 9
    assert Coordinates(0, 9, 0) in result.path
    assert Coordinates(1, 9, 0) in result.path
    assert Coordinates(2, 9, 0) in result.path


def test_a_star_with_vertical_elevation(graph: WarehouseGraph) -> None:
    finder = AStarPathfinder(graph, parameters=PathfindingParameters(step_cost=1.0, turn_penalty=0.5, vertical_cost_per_level=1.5))
    start = Coordinates(0, 0, 0)
    goal = Coordinates(1, 0, 3)

    result = finder.find_path(start, goal)

    # Waypoints: (0,0,0) -> (1,0,0) -> (1,0,3)
    assert result.path[0] == start
    assert result.path[-1] == goal
    assert result.ground_distance == 1.0
    assert result.vertical_distance == 3.0
    # Cost = 1.0 (step) + 3 * 1.5 (vertical) = 5.5
    assert result.total_cost == 5.5


def test_a_star_with_blocked_node_forces_detour(graph: WarehouseGraph) -> None:
    # Route from (0,0,0) to (0,2,0)
    # Normally direct: (0,0,0) -> (0,1,0) -> (0,2,0)
    # Block (0,1,0)
    graph.block_node(Coordinates(0, 1, 0))

    finder = AStarPathfinder(graph)
    start = Coordinates(0, 0, 0)
    goal = Coordinates(0, 2, 0)

    # Forklift must detour through cross-aisle: (0,0) -> (1,0) -> (1,1) -> (1,2) -> wait, (1,2) cannot cross to (0,2)!
    # Must go all the way to rear cross-aisle (Y=9) or through valid connections!
    result = finder.find_path(start, goal)

    assert result.path[0] == start
    assert result.path[-1] == goal
    assert Coordinates(0, 1, 0) not in result.path


def test_a_star_unreachable_raises_path_not_found(graph: WarehouseGraph) -> None:
    # Completely block access to (3, 5, 0): block (3, 4, 0) and (3, 6, 0)
    graph.block_node(Coordinates(3, 4, 0))
    graph.block_node(Coordinates(3, 6, 0))

    finder = AStarPathfinder(graph)
    with pytest.raises(PathNotFoundError, match="No navigable path found"):
        finder.find_path(Coordinates(0, 0, 0), Coordinates(3, 5, 2))


def test_a_star_out_of_bounds_raises_error(graph: WarehouseGraph) -> None:
    finder = AStarPathfinder(graph)
    with pytest.raises(PathNotFoundError, match="out of warehouse bounds"):
        finder.find_path(Coordinates(0, 0, 0), Coordinates(10, 10, 10))


def test_corridor_aware_heuristic_consistency(graph: WarehouseGraph) -> None:
    c1 = Coordinates(0, 5, 0)
    c2 = Coordinates(2, 5, 0)

    manhattan_h = manhattan_distance_heuristic(c1, c2)
    assert manhattan_h == 2.0  # |0-2| + |5-5|

    corridor_h = corridor_aware_heuristic(c1, c2, graph.cross_aisles)
    # Minimum detour through Y=9 is 4 + 2 + 4 = 10
    assert corridor_h == 10.0
    # Must be less than or equal to true cost (10.0)
    finder = AStarPathfinder(graph, heuristic=lambda a, b: corridor_aware_heuristic(a, b, graph.cross_aisles))
    result = finder.find_path(c1, c2)
    assert corridor_h <= result.ground_distance


def test_a_star_start_with_z_greater_than_zero(graph: WarehouseGraph) -> None:
    finder = AStarPathfinder(graph)
    start = Coordinates(0, 0, 2)
    goal = Coordinates(0, 3, 1)

    result = finder.find_path(start, goal)

    assert result.path[0] == start
    assert result.path[1] == Coordinates(0, 0, 0)
    assert result.path[-1] == goal
    assert result.vertical_distance == 3.0  # 2 down + 1 up


def test_a_star_blocked_start(graph: WarehouseGraph) -> None:
    graph.block_node(Coordinates(0, 0, 0))
    finder = AStarPathfinder(graph)

    with pytest.raises(PathNotFoundError, match="Start transit node"):
        finder.find_path(Coordinates(0, 0, 0), Coordinates(0, 2, 0))

