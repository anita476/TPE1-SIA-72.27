from algorithms.heuristics.heuristic_commons import (
    hungarian_min_cost_assignment,
    manhattan_distance,
)
from utils.state import SokobanState


def basic_hungarian_plus_player_distance(state: SokobanState) -> float:
    """Simple Hungarian-plus-player-distance heuristic.
    This is a simpler variant based on Manhattan assignment plus a lower bound on the walk before the first push.
    """
    boxes = list(state.boxes)
    goals = list(state.goals)

    if not boxes or state.is_solved():
        return 0

    cost_matrix = [[manhattan_distance(box, goal) for goal in goals] for box in boxes]
    matching_cost, _assignment = hungarian_min_cost_assignment(cost_matrix)
    player_to_nearest = max(min(manhattan_distance(state.player, box) for box in boxes) - 1, 0)

    return matching_cost + player_to_nearest
