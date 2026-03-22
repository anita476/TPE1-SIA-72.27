from algorithms.heuristics.heuristic_commons import exact_minimum_matching_cost, walk_before_first_push_lb
from utils.state import SokobanState


def mm_heuristic(state: SokobanState) -> float:
    """Minimum Matching heuristic (hMM) using exact one-stone push distances + walk before first push."""
    return exact_minimum_matching_cost(state) + walk_before_first_push_lb(state)
