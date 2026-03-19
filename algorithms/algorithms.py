from algorithms.dfs import dfs
from algorithms.bfs import bfs
from algorithms.iddfs import iddfs
from algorithms.greedy import greedy
from algorithms.astar import astar
from algorithms.heuristics.manhattan import manhattan_heuristic 
from algorithms.heuristics.emm import emm_heuristic
from algorithms.heuristics.deadlock import deadlock_heuristic
from algorithms.heuristics.combination import combination_heuristic


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
    "emm": emm_heuristic,
    "deadlock": deadlock_heuristic,
    "combination": combination_heuristic,
}
