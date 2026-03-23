from algorithms.heuristics.basic_hungarian_plus_player_distance import basic_hungarian_plus_player_distance
from utils.state import SokobanState
from algorithms.heuristics.deadlock import deadlock_heuristic 
from algorithms.heuristics.emm import emm_heuristic

def combination_heuristic(state: SokobanState) -> float:
    return max(deadlock_heuristic(state), basic_hungarian_plus_player_distance(state))
