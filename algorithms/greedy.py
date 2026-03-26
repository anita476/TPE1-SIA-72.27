import time
import tracemalloc
import heapq
from utils.state import SokobanState, get_successors
from algorithms.utils import SearchNode, SearchResult, get_peak_memory_kb
from algorithms.heuristics.manhattan import manhattan_heuristic
from algorithms.heuristics.deadlock import deadlock_heuristic
from algorithms.heuristics.combination import combination_heuristic
from algorithms.heuristics.emm import emm_heuristic


def greedy(initial_state: SokobanState, heuristic=emm_heuristic) -> SearchResult:
    start_time = time.time()
    tracemalloc.start()
    heuristic_time_total = 0.0

    root = SearchNode(initial_state)
    frontier = [] # using a priority queue to select the less costly option
    counter = 0
    h_start = time.perf_counter()
    root_h = heuristic(initial_state)
    heuristic_time_total += time.perf_counter() - h_start
    heapq.heappush(frontier, (root_h, counter, root))
    explored = set()
    expanded_count = 0

    while frontier:
        _, _, node = heapq.heappop(frontier)

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
                heuristic_time=heuristic_time_total,
            )

        for direction, new_state in get_successors(node.state):
            if new_state not in explored:
                # checkeo estados repetidos
                child = SearchNode(new_state, parent=node, action=direction, cost=node.cost + 1)
                counter += 1
                h_start = time.perf_counter()
                h_value = heuristic(new_state)
                heuristic_time_total += time.perf_counter() - h_start
                heapq.heappush(frontier, (h_value, counter, child))

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
        heuristic_time=heuristic_time_total,
    )

