from utils.state import Position, SokobanState
from enum import StrEnum

class Heuristic(StrEnum):
    MANHATTAN = "MANHATTAN"
    EMM = "EMM"

def manhattan_distance(pos1: Position, pos2: Position) -> int:
    return abs(pos1.row - pos2.row) + abs(pos1.col - pos2.col)


# too simple of an heuristic 
# todo: what happens with obstacles or many boxes
def manhattan_heuristic(state: SokobanState) -> int:
    """Calculate heuristic: sum of minimum Manhattan distances from each box to any goal."""
    total_distance = 0
    for box in state.boxes:
        min_distance = min(manhattan_distance(box, goal) for goal in state.goals)
        total_distance += min_distance
    return total_distance

# "standard" heuristic for sokoban
def emm_heuristic(state: SokobanState) -> int:
    """Enhanced Minimum Matching heuristic but accounting for player movement costs
    
    For each box, calculates the minimum cost over all goals of:
    distance(player, box) + distance(box, goal)
    
    """
    total_distance = 0
    for box in state.boxes:
        # For each box, find the goal that minimizes the combined cost
        min_cost = float('inf')
        for goal in state.goals:
            # Cost = distance from player to box + distance from box to goal
            player_to_box = manhattan_distance(state.player, box)
            box_to_goal = manhattan_distance(box, goal)
            cost = player_to_box + box_to_goal
            min_cost = min(min_cost, cost)
        total_distance += min_cost
    return total_distance
