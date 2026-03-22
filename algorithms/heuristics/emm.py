from algorithms.heuristics.heuristic_commons import (
    exact_minimum_matching_cost,
    count_linear_conflicts,
    walk_before_first_push_lb
)
from utils.state import SokobanState


def emm_heuristic(state: SokobanState) -> float:
    """Enhanced Minimum Matching (Pereira et al.).

    EMM(state) = hMM(state) + 2 * L(state) + D(state)
      - hMM(state): Minimum Matching heuristic (exact push distances)
      - L(state): Number of linear conflicts in the current assignment
      - D(state): Player-to-nearest-box distance (lower bound on first move)
    """
    matching_cost = exact_minimum_matching_cost(state)
    if matching_cost == float("inf"):
        return matching_cost

    return matching_cost + 2 * count_linear_conflicts(state) + walk_before_first_push_lb(state)
