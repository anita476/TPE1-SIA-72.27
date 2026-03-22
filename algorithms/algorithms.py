from algorithms.dfs import dfs
from algorithms.bfs import bfs
from algorithms.heuristics.basic_hungarian_plus_player_distance import basic_hungarian_plus_player_distance
from algorithms.iddfs import iddfs
from algorithms.greedy import greedy
from algorithms.astar import astar
from algorithms.heuristics.manhattan import manhattan_heuristic 
from algorithms.heuristics.mm import mm_heuristic
from algorithms.heuristics.emm import emm_heuristic
from algorithms.heuristics.deadlock import deadlock_heuristic
from algorithms.heuristics.combination import combination_heuristic
from algorithms.heuristics.improved_basic_hungarian_plus_player_distance import improved_hungarian_plus_player_distance_with_complex_count_linear_conflict
from algorithms.heuristics.push_distance import push_distance_heuristic
from algorithms.heuristics.simple_emm import emm_heuristic as simple_emm_heuristic


ALGORITHMS = {
    "dfs": dfs,
    "bfs": bfs,
    "iddfs": iddfs,
    "greedy": greedy,
    "astar": astar,
}

# Algorithms that accept a `heuristic` keyword argument
HEURISTIC_ALGORITHMS = {"greedy", "astar"}

HEURISTICS = {
    "manhattan": manhattan_heuristic,
    "basic_hungarian_plus_player_distance": basic_hungarian_plus_player_distance,
    "improved_hungarian_plus_player_distance": improved_hungarian_plus_player_distance_with_complex_count_linear_conflict,
    "mm": mm_heuristic,
    "emm": emm_heuristic,
    "deadlock": deadlock_heuristic,
    "combination": combination_heuristic,
    "push_distance": push_distance_heuristic,
    "simple_emm": simple_emm_heuristic,
}
