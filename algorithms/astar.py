import time
import tracemalloc
import heapq
from utils.state import SokobanState, get_successors
from algorithms.utils import SearchNode, SearchResult, get_peak_memory_kb
from algorithms.heuristics.manhattan import manhattan_heuristic
from algorithms.heuristics.deadlock import deadlock_heuristic
from algorithms.heuristics.combination import combination_heuristic
from algorithms.heuristics.emm import emm_heuristic


def astar(initial_state: SokobanState, heuristic=emm_heuristic) -> SearchResult:
    """A* search: expands nodes in order of f(n) = g(n) + h(n).

    Assumes the heuristic is consistent (monotone): h(n) <= cost(n->n') + h(n') hence will find an optimal solution.
    """
    start_time = time.time()
    tracemalloc.start()

    initial_h = heuristic(initial_state)
    if callable(initial_h):
        heuristic_fn = initial_h
        initial_h = heuristic_fn(initial_state)
    else:
        heuristic_fn = heuristic

    root = SearchNode(initial_state)
    explored = set()
    counter = 0
    frontier: list = []
    heapq.heappush(frontier, (initial_h, counter, root))

    expanded_count = 0

    while frontier:
        _f, _tie, node = heapq.heappop(frontier)

        if node.state in explored:
            continue
        explored.add(node.state)
        expanded_count += 1

        if node.state.is_solved():
            elapsed = time.time() - start_time
            memory_kb = get_peak_memory_kb()
            tracemalloc.stop()
            return SearchResult(
                success=True,
                path=node.get_path(),
                cost=node.cost,
                expanded_nodes=expanded_count,
                frontier_nodes=len(frontier),
                processing_time=elapsed,
                memory_kb=memory_kb,
                boxes_displaced=node.box_pushes,
            )

        for direction, new_state in get_successors(node.state):
            if new_state not in explored:
                child = SearchNode(new_state, parent=node, action=direction, cost=node.cost + 1)
                counter += 1
                heapq.heappush(frontier, (node.cost + 1 + heuristic_fn(new_state), counter, child))

    elapsed = time.time() - start_time
    memory_kb = get_peak_memory_kb()
    tracemalloc.stop()
    return SearchResult(
        success=False,
        path=[],
        cost=0,
        expanded_nodes=expanded_count,
        frontier_nodes=0,
        processing_time=elapsed,
        memory_kb=memory_kb,
    )
