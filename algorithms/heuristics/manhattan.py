from algorithms.heuristics.heuristic_commons import manhattan_distance
from utils.state import SokobanState


def manhattan_heuristic(state: SokobanState) -> int:
    """Sum of minimum Manhattan distances from each box to any goal."""
    total = 0
    for box in state.boxes:
        total += min(manhattan_distance(box, goal) for goal in state.goals)
    return total

def manhattan_heuristics_with_greedy_asignment(state: SokobanState) -> int:
    """Sum of minimum Manhattan distances from each box to any goal, using a greedy assignment."""
    total = 0
    remaining_goals = set(state.goals)
    for box in state.boxes:
        if not remaining_goals:
            break
        closest_goal = min(remaining_goals, key=lambda g: manhattan_distance(box, g))
        total += manhattan_distance(box, closest_goal)
        remaining_goals.remove(closest_goal)
    return total