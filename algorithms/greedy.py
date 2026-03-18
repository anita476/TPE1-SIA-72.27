import time
import tracemalloc
import heapq
from utils.state import SokobanState, get_successors, Position
from algorithms.utils import SearchNode, SearchResult, get_peak_memory_kb
from algorithms.heuristics.heuristics import emm_heuristic, manhattan_heuristic, combination_heuristic


# todo is greedy optimal?
def greedy(initial_state: SokobanState, heuristic=emm_heuristic) -> SearchResult:
    start_time = time.time()
    tracemalloc.start()


    root = SearchNode(initial_state)
    frontier = [] # using a priority queue to select the less costly option
    counter = 0  # tie breaker # todo is this the FO in the paper ?
    heapq.heappush(frontier, (heuristic(initial_state), counter, root))
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
            )

        for direction, new_state in get_successors(node.state):
            if new_state not in explored:
                # checkeo estados repetidos
                child = SearchNode(new_state, parent=node, action=direction, cost=node.cost + 1)
                counter += 1
                heapq.heappush(frontier, (heuristic(new_state), counter, child))

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

