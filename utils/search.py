import time
from utils.state import SokobanState, DIRECTION_NAMES, get_successors


class SearchNode:
    def __init__(self, state: SokobanState, parent=None, action=None, cost: int = 0):
        self.state = state
        self.parent = parent
        self.action = action
        self.cost = cost

    def get_path(self) -> list[tuple]:
        path = []
        node = self
        while node.parent is not None:
            path.append(node.action)
            node = node.parent
        path.reverse()
        return path


class SearchResult:
    def __init__(self, success: bool, path: list, cost: int, expanded_nodes: int, frontier_nodes: int, processing_time: float):
        self.success = success
        self.path = path
        self.cost = cost
        self.expanded_nodes = expanded_nodes
        self.frontier_nodes = frontier_nodes
        self.processing_time = processing_time

    def __str__(self):
        lines = []
        lines.append(f"Result: {'Success' if self.success else 'Failure'}")
        if self.success:
            lines.append(f"Solution cost: {self.cost}")
            path_str = " -> ".join(DIRECTION_NAMES[d] for d in self.path)
            lines.append(f"Solution: {path_str}")
        lines.append(f"Expanded nodes: {self.expanded_nodes}")
        lines.append(f"Frontier nodes: {self.frontier_nodes}")
        lines.append(f"Processing time: {self.processing_time:.4f}s")
        return "\n".join(lines)


def dfs(initial_state: SokobanState) -> SearchResult:
    start_time = time.time()

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
            return SearchResult(
                success=True,
                path=node.get_path(),
                cost=node.cost,
                expanded_nodes=expanded_count,
                frontier_nodes=len(frontier),
                processing_time=elapsed,
            )

        for direction, new_state in get_successors(node.state):
            if new_state not in explored:
                child = SearchNode(new_state, parent=node, action=direction, cost=node.cost + 1)
                frontier.append(child)

    elapsed = time.time() - start_time
    return SearchResult(
        success=False,
        path=[],
        cost=0,
        expanded_nodes=expanded_count,
        frontier_nodes=0,
        processing_time=elapsed,
    )
