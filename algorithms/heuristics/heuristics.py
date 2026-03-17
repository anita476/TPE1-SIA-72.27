from utils.state import Position, SokobanState


def manhattan_distance(pos1: Position, pos2: Position) -> int:
    return abs(pos1.row - pos2.row) + abs(pos1.col - pos2.col)


def manhattan_heuristic(state: SokobanState) -> int:
    """Calculate heuristic: sum of minimum Manhattan distances from each box to any goal."""
    total_distance = 0
    for box in state.boxes:
        min_distance = min(manhattan_distance(box, goal) for goal in state.goals)
        total_distance += min_distance
    return total_distance
