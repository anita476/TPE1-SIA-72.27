from algorithms.heuristics.heuristic_commons import exact_push_hungarian_cost, player_to_nearest_box_lb
from utils.state import SokobanState


def mm_heuristic(state: SokobanState) -> float:
    """Minimum Matching heuristic (hMM) using exact one-stone push distances + walk before first push."""
    return exact_push_hungarian_cost(state) + player_to_nearest_box_lb(state)
