from algorithms.heuristics.heuristic_commons import manhattan_distance
from utils.state import SokobanState


def manhattan_heuristic(state: SokobanState) -> int:
    """Sum of minimum Manhattan distances from each box to any goal."""
    total = 0
    for box in state.boxes:
        total += min(manhattan_distance(box, goal) for goal in state.goals)
    return total