import time
import tracemalloc
from utils.state import SokobanState, get_successors
from algorithms.utils import SearchNode, SearchResult, get_peak_memory_kb


def dfs(initial_state: SokobanState) -> SearchResult:
    start_time = time.time()
    tracemalloc.start()

    root = SearchNode(initial_state)
    frontier = [root]
    explored = set()
    expanded_count = 0

    while frontier:
        node = frontier.pop()

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
                frontier.append(child)

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
