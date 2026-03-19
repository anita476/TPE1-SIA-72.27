from utils.state import SokobanState
from algorithms.heuristics.deadlock import deadlock_heuristic 
from algorithms.heuristics.emm import emm_heuristic

def combination_heuristic(state: SokobanState) -> int:
    return max(deadlock_heuristic(state), emm_heuristic(state))
