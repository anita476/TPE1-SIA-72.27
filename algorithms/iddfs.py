import time
import tracemalloc
from utils.state import SokobanState, get_successors
from algorithms.utils import SearchNode, SearchResult, get_peak_memory_kb


DEFAULT_MAX_IDDFS_ITERATIONS = 100_000


def depth_limited_search(
    node: SearchNode,
    depth_limit: int,
    path_states: set[SokobanState],
) -> tuple[SearchNode | None, int]:
    if node.state.is_solved():
        return node, 1

    if depth_limit <= 0:
        return None, 0

    if node.state in path_states:
        return None, 0

    path_states.add(node.state)
    expanded = 1

    for direction, new_state in get_successors(node.state):
        if new_state not in path_states:
            child = SearchNode(new_state, parent=node, action=direction, cost=node.cost + 1)
            result, child_expanded = depth_limited_search(child, depth_limit - 1, path_states)
            expanded += child_expanded
            if result is not None:
                path_states.remove(node.state)
                return result, expanded

    path_states.remove(node.state)
    return None, expanded


def iddfs(
    initial_state: SokobanState,
    *,
    max_iterations: int = DEFAULT_MAX_IDDFS_ITERATIONS,
) -> SearchResult:
    start_time = time.time()
    tracemalloc.start()
    total_expanded = 0
    depth = 0

    while depth < max_iterations:
        result, expanded = depth_limited_search(
            SearchNode(initial_state),
            depth_limit=depth,
            path_states=set(),
        )
        total_expanded += expanded

        if result is not None:
            elapsed = time.time() - start_time
            memory_kb = get_peak_memory_kb()
            tracemalloc.stop()
            return SearchResult(
                success=True,
                path=result.get_path(),
                cost=result.cost,
                expanded_nodes=total_expanded,
                frontier_nodes=0,
                processing_time=elapsed,
                memory_kb=memory_kb,
                boxes_displaced=result.box_pushes,
            )

        depth += 1

    elapsed = time.time() - start_time
    memory_kb = get_peak_memory_kb()
    tracemalloc.stop()
    return SearchResult(
        success=False,
        path=[],
        cost=0,
        expanded_nodes=total_expanded,
        frontier_nodes=0,
        processing_time=elapsed,
        memory_kb=memory_kb,
    )
