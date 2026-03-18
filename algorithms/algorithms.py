from algorithms.dfs import dfs
from algorithms.bfs import bfs
from algorithms.iddfs import iddfs
from algorithms.greedy import greedy
from algorithms.astar import astar
from algorithms.heuristics.heuristics import manhattan_heuristic, emm_heuristic

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
}
