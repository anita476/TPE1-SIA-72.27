from algorithms.heuristics.heuristic_commons import (
    count_linear_conflicts,
    hungarian_min_cost_assignment,
    manhattan_distance,
)
from utils.state import SokobanState


def improved_hungarian_plus_player_distance_with_complex_count_linear_conflict(state: SokobanState) -> float:
    """Simple Hungarian-plus-player-distance variant with linear conflicts.
    Uses Manhattan assignment + exact linear-conflict count + walk lower bound.
    """
    boxes = list(state.boxes)
    goals = list(state.goals)

    if not boxes or state.is_solved():
        return 0

    cost_matrix = [[manhattan_distance(box, goal) for goal in goals] for box in boxes]
    matching_cost, _assignment = hungarian_min_cost_assignment(cost_matrix)
    conflicts = count_linear_conflicts(state)
    player_to_nearest = max(min(manhattan_distance(state.player, box) for box in boxes) - 1, 0)

    return matching_cost + 2 * conflicts + player_to_nearest
