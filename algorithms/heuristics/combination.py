from utils.state import SokobanState
from algorithms.heuristics.deadlock import deadlock_heuristic
from algorithms.heuristics.improved_basic_hungarian_plus_player_distance import improved_hungarian_plus_player_distance_with_complex_count_linear_conflict


def combination_heuristic(state: SokobanState) -> float:
    result = deadlock_heuristic(state)
    if(result == 0):
        return improved_hungarian_plus_player_distance_with_complex_count_linear_conflict(state)
    return result
