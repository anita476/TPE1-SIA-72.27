from utils.state import Position, SokobanState, ALL_DIRECTIONS
from enum import StrEnum
from collections import deque

class Heuristic(StrEnum):
    MANHATTAN = "MANHATTAN"
    EMM = "EMM"

# ---------------------------------------------------------------------------
# SHARED UTILITIES
# ---------------------------------------------------------------------------

def manhattan_distance(pos1: Position, pos2: Position) -> int:
    return abs(pos1.row - pos2.row) + abs(pos1.col - pos2.col)


def _hungarian_min_cost_assignment(cost_matrix: list[list[int]]) -> tuple[int, list[int]]:
    """Compute minimum-cost perfect matching for a square cost matrix.

    Returns (min_cost, match) where match[i] is the column assigned to row i.
    O(n^3) Hungarian algorithm — correct and admissible base for all heuristics.
    """
    n = len(cost_matrix)
    if n == 0:
        return 0, []

    cost = [row[:] for row in cost_matrix]
    u    = [0] * (n + 1)
    v    = [0] * (n + 1)
    p    = [0] * (n + 1)
    way  = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0   = 0
        minv = [float('inf')] * (n + 1)
        used = [False]        * (n + 1)
        while True:
            used[j0] = True
            i0    = p[j0]
            delta = float('inf')
            j1    = 0
            for j in range(1, n + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j]  = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1    = j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j]    -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1    = way[j0]
            p[j0] = p[j1]
            j0    = j1
            if j0 == 0:
                break

    match = [-1] * n
    for j in range(1, n + 1):
        if p[j] != 0:
            match[p[j] - 1] = j - 1

    return -v[0], match


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


def manhattan_heuristic(state: SokobanState) -> int:
    """Sum of minimum Manhattan distances from each box to any goal."""
    total = 0
    for box in state.boxes:
        total += min(manhattan_distance(box, goal) for goal in state.goals)
    return total

def emm_heuristic(state: SokobanState) -> int:
    """Enhanced Minimum Matching with linear conflicts.

    Admissible and consistent:
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

    matching_cost, assignment = _hungarian_min_cost_assignment(cost_matrix)
    conflicts               = _linear_conflicts(boxes, goals, assignment)
    ## min to the nearest box would tend to underestimate but its for it to keep being admissible
    player_to_nearest       = min(manhattan_distance(state.player, box) for box in boxes)

    return matching_cost + 2 * conflicts + player_to_nearest

