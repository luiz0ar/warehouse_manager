import heapq
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.models.coordinates import Coordinates
from app.domain.optimization.pathfinding.heuristics import (
    HeuristicFunction,
    manhattan_distance_heuristic,
)

if TYPE_CHECKING:
    from app.domain.optimization.pathfinding.warehouse_graph import WarehouseGraph


class PathNotFoundError(Exception):
    """Raised when no valid obstacle-free path exists between start and goal."""


@dataclass(frozen=True, slots=True)
class PathfindingParameters:
    """Configurable weights for A* routing."""

    step_cost: float = 1.0
    turn_penalty: float = 0.5
    vertical_cost_per_level: float = 1.0


@dataclass(frozen=True, slots=True)
class PathResult:
    """Complete routing result produced by the A* algorithm."""

    path: list[Coordinates]
    total_cost: float
    ground_distance: float
    vertical_distance: float
    turn_count: int


class AStarPathfinder:
    """A* (A-Star) Pathfinding Engine for Industrial Coffee Warehouse Logistics.

    Guarantees mathematically optimal, obstacle-free paths across warehouse corridors,
    incorporating floor transit, turn deceleration penalties, and vertical mast lifting.
    """

    def __init__(
        self,
        graph: "WarehouseGraph",
        parameters: PathfindingParameters | None = None,
        heuristic: HeuristicFunction | None = None,
    ) -> None:
        self.graph = graph
        self.params = parameters or PathfindingParameters()
        self.heuristic = heuristic or manhattan_distance_heuristic

    def find_path(self, start: Coordinates, goal: Coordinates) -> PathResult:
        """Find the optimal obstacle-free path from start to goal.

        Args:
            start: Origin coordinates (typically loading dock at Z=0).
            goal: Destination rack coordinates [X, Y, Z].

        Returns:
            PathResult with ordered waypoints, total cost, distances, and turn count.

        Raises:
            PathNotFoundError: If start or goal is unwalkable/out-of-bounds or no path exists.
        """
        if not self.graph.is_within_bounds(start):
            raise PathNotFoundError(f"Start coordinates {start} are out of warehouse bounds.")
        if not self.graph.is_within_bounds(goal):
            raise PathNotFoundError(f"Goal coordinates {goal} are out of warehouse bounds.")

        # Ground access points at Z=0
        start_ground = Coordinates(start.x, start.y, 0)
        goal_ground = self.graph.get_access_point(goal)

        if not self.graph.is_walkable(start_ground):
            raise PathNotFoundError(f"Start transit node {start_ground} is blocked.")
        if not self.graph.is_walkable(goal_ground):
            raise PathNotFoundError(f"Goal transit access node {goal_ground} is blocked.")

        # Trivial case: start and goal are identical
        if start == goal:
            return PathResult(
                path=[start],
                total_cost=0.0,
                ground_distance=0.0,
                vertical_distance=0.0,
                turn_count=0,
            )

        # State representation: (Coordinates, direction)
        # direction is a tuple (dx, dy) representing orientation from the last move
        initial_direction = None
        start_state = (start_ground, initial_direction)

        # Priority queue storing tuples: (f_score, tie_breaker_counter, state)
        counter = 0
        open_set: list[tuple[float, int, tuple[Coordinates, tuple[int, int] | None]]] = []

        initial_h = self.heuristic(start_ground, goal_ground)
        heapq.heappush(open_set, (initial_h, counter, start_state))

        g_score: dict[tuple[Coordinates, tuple[int, int] | None], float] = {start_state: 0.0}
        came_from: dict[
            tuple[Coordinates, tuple[int, int] | None],
            tuple[Coordinates, tuple[int, int] | None],
        ] = {}

        best_goal_state: tuple[Coordinates, tuple[int, int] | None] | None = None

        while open_set:
            _current_f, _, current_state = heapq.heappop(open_set)
            current_node, current_dir = current_state
            current_g = g_score[current_state]

            # Reached ground access point for the destination slot
            if current_node == goal_ground:
                best_goal_state = current_state
                break

            for neighbor in self.graph.get_floor_neighbors(current_node):
                move_dir = (neighbor.x - current_node.x, neighbor.y - current_node.y)

                # Transition cost: step cost + turn penalty if changing direction
                cost = self.params.step_cost
                is_turn = current_dir is not None and current_dir != move_dir
                if is_turn:
                    cost += self.params.turn_penalty

                tentative_g = current_g + cost
                neighbor_state = (neighbor, move_dir)

                if tentative_g < g_score.get(neighbor_state, float("inf")):
                    g_score[neighbor_state] = tentative_g
                    came_from[neighbor_state] = current_state

                    h_score = self.heuristic(neighbor, goal_ground)
                    counter += 1
                    heapq.heappush(open_set, (tentative_g + h_score, counter, neighbor_state))

        if best_goal_state is None:
            raise PathNotFoundError(f"No navigable path found from {start} to {goal}.")

        # Reconstruct path at floor level Z=0
        reconstructed_ground: list[Coordinates] = []
        curr: tuple[Coordinates, tuple[int, int] | None] | None = best_goal_state
        turns = 0

        while curr is not None:
            reconstructed_ground.append(curr[0])
            prev = came_from.get(curr)
            if (
                prev is not None
                and prev[1] is not None
                and curr[1] is not None
                and prev[1] != curr[1]
            ):
                turns += 1
            curr = prev

        reconstructed_ground.reverse()

        # Handle vertical lift from ground access point to rack slot
        ground_distance = float(len(reconstructed_ground) - 1) if reconstructed_ground else 0.0
        vertical_levels = float(goal.z)
        vertical_cost = vertical_levels * self.params.vertical_cost_per_level

        final_path: list[Coordinates] = []

        # If start had Z > 0, prepend mast descent
        if start.z > 0:
            final_path.append(start)
            vertical_levels += float(start.z)
            vertical_cost += float(start.z) * self.params.vertical_cost_per_level

        final_path.extend(reconstructed_ground)

        # If goal has Z > 0, append mast elevation waypoint
        if goal.z > 0:
            final_path.append(goal)

        total_cost = g_score[best_goal_state] + vertical_cost

        return PathResult(
            path=final_path,
            total_cost=round(total_cost, 2),
            ground_distance=round(ground_distance, 2),
            vertical_distance=round(vertical_levels, 2),
            turn_count=turns,
        )
