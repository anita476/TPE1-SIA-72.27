import tracemalloc
from utils.state import SokobanState, DIRECTION_NAMES


def get_peak_memory_kb() -> float:
    """Retorna el pico de memoria usado (KB) desde tracemalloc.start()."""
    current, peak = tracemalloc.get_traced_memory()
    return peak / 1024


class SearchNode:
    def __init__(self, state: SokobanState, parent=None, action=None, cost: int = 0):
        self.state = state
        self.parent = parent
        self.action = action
        self.cost = cost
        if parent is not None and state.boxes != parent.state.boxes:
            self.box_pushes = parent.box_pushes + 1
        else:
            self.box_pushes = 0 if parent is None else parent.box_pushes

    def get_path(self) -> list[tuple]:
        path = []
        node = self
        while node.parent is not None:
            path.append(node.action)
            node = node.parent
        path.reverse()
        return path


class SearchResult:
    def __init__(
        self,
        success: bool,
        path: list,
        cost: int,
        expanded_nodes: int,
        frontier_nodes: int,
        processing_time: float,
        memory_kb: float = 0,
        boxes_displaced: int = 0,
        heuristic_time: float = 0.0,  # total time spent evaluating the heuristic (seconds)
    ):
        self.success = success
        self.path = path
        self.cost = cost
        self.expanded_nodes = expanded_nodes
        self.frontier_nodes = frontier_nodes
        self.processing_time = processing_time
        self.memory_kb = memory_kb
        self.boxes_displaced = boxes_displaced
        self.heuristic_time = heuristic_time

    def __str__(self):
        lines = []
        lines.append(f"Result: {'Success' if self.success else 'Failure'}")
        if self.success:
            lines.append(f"Solution cost: {self.cost}")
            lines.append(f"Boxes displaced: {self.boxes_displaced}")
            path_str = " -> ".join(DIRECTION_NAMES[d] for d in self.path)
            lines.append(f"Solution: {path_str}")
        lines.append(f"Expanded nodes: {self.expanded_nodes}")
        lines.append(f"Frontier nodes: {self.frontier_nodes}")
        lines.append(f"Processing time: {self.processing_time:.4f}s")
        lines.append(f"Heuristic time: {self.heuristic_time:.4f}s")
        lines.append(f"Memory: {self.memory_kb:.1f} KB")
        return "\n".join(lines)
