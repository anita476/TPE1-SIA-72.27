from algorithms.heuristics.heuristic_commons import (
    relaxed_push_hungarian_cost,
    player_to_nearest_box_lb,
)
from utils.state import SokobanState


def push_distance_heuristic(state: SokobanState) -> float:
    """Move-optimal lower bound based on relaxed push distances."""
    matching_cost = relaxed_push_hungarian_cost(state)
    if matching_cost == float("inf"):
        return matching_cost

    return matching_cost + player_to_nearest_box_lb(state)
