from algorithms.heuristics.heuristic_commons import hungarian_min_cost_assignment, manhattan_distance
from utils.state import Position, SokobanState


def _linear_conflicts(boxes: list[Position], goals: list[Position], assignment: list[int]) -> int:
    """Count linear conflicts between boxes whose assigned goals are in the same
    row/column but in reversed order

    removed the adjacency restriction: any two boxes in the
    same row/col whose goals are reversed constitute a conflict, not just
    neighbouring ones.  
    its admissible because resolving each such conflict requires at least 2 extra pushes
    -> todo prove this
    """
    conflicts = 0
    n = len(boxes)


    for i in range(n): # O(n^2)
        for j in range(i + 1, n):
            b1, b2 = boxes[i], boxes[j] # box row b1 and box column b2
            g1 = goals[assignment[i]]
            g2 = goals[assignment[j]] # goal for that box row g1, goal for that box g2

            if b1.row == b2.row == g1.row == g2.row:
                if (b1.col < b2.col) != (g1.col < g2.col):
                    conflicts += 1

            elif b1.col == b2.col == g1.col == g2.col:
                if (b1.row < b2.row) != (g1.row < g2.row):
                    conflicts += 1

    return conflicts


def emm_heuristic(state: SokobanState) -> int:
    """Enhanced Minimum Matching with linear conflicts.

    Non-Admissible:
      - Hungarian matching gives a lower bound on push cost
      - Each linear conflict adds at least 2 extra pushes 
      - Player-to-nearest-box distance is a lower bound on the first move cost

    Reference: Pereira et al., IJCAI 2016.
    """
    boxes = list(state.boxes)
    goals = list(state.goals)

    if not boxes:
        return 0

    cost_matrix = [
        [manhattan_distance(box, goal) for goal in goals]
        for box in boxes
    ]

    matching_cost, assignment = hungarian_min_cost_assignment(cost_matrix)
    conflicts = _linear_conflicts(boxes, goals, assignment)
    ## min to the nearest box would tend to underestimate but its for it to keep being admissible
    player_to_nearest = min(manhattan_distance(state.player, box) for box in boxes)

    return matching_cost + 2 * conflicts + player_to_nearest