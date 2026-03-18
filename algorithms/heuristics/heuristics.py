from utils.state import Position, SokobanState
from enum import StrEnum

class Heuristic(StrEnum):
    MANHATTAN = "MANHATTAN"
    EMM = "EMM"

"""
UTILS FOR HEURISTIC CALCS
"""
def manhattan_distance(pos1: Position, pos2: Position) -> int:
    return abs(pos1.row - pos2.row) + abs(pos1.col - pos2.col)


# matrix is always square -> remember its On3 -> ok for small number of boxes but not for bigger maps
# how it works: https://www.youtube.com/watch?v=cQ5MsiGaDY8
#               https://en.wikipedia.org/wiki/Hungarian_algorithm#Matrix_interpretation

def _hungarian_min_cost_assignment(cost_matrix: list[list[int]]) -> tuple[int, list[int]]:
    """Compute minimum-cost perfect matching for a square cost matrix

    Returns a tuple of (min_cost, match) where match[i] is the index of the column
    assigned to row i.

    based on the Hungarian algorithm (O(n^3))
    """

    n = len(cost_matrix)
    if n == 0:
        return 0, []

    # Create a copy so we don't mutate the input
    cost = [row[:] for row in cost_matrix]

    u = [0] * (n + 1)
    v = [0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [float('inf')] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float('inf')
            j1 = 0
            for j in range(1, n + 1):
                if used[j]:
                    continue
                cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]:
                    minv[j] = cur
                    way[j] = j0
                if minv[j] < delta:
                    delta = minv[j]
                    j1 = j
            for j in range(0, n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    match = [-1] * n
    for j in range(1, n + 1):
        if p[j] != 0:
            match[p[j] - 1] = j - 1

    min_cost = -v[0]
    return min_cost, match


# too simple of an heuristic 
# todo: what happens with obstacles or many boxes
def manhattan_heuristic(state: SokobanState) -> int:
    """Calculate heuristic: sum of minimum Manhattan distances from each box to any goal."""
    total_distance = 0
    for box in state.boxes:
        min_distance = min(manhattan_distance(box, goal) for goal in state.goals)
        total_distance += min_distance
    return total_distance




# contar LINEAR CONFLICTS 
def _linear_conflicts(boxes: list[Position], goals: list[Position], assignment: list[int]) -> int:
    """Count linear conflicts between adjacent boxes based on their assigned goals

        theres conflict if -> 2 adjacent boxes are in the same row/column + assigned goals are in the same row/column
        but in reverse order 

        ejemplo: 
        box A -> pos 0,0 -> goal 5,1
        box B -> pos 0,1 -> goal 5,0 
        the position columns are increasing, but the goal columns are decreasing -> conflict ! 
    """
    conflicts = 0
    n = len(boxes)

    def _is_adjacent(p1: Position, p2: Position) -> bool:
        return manhattan_distance(p1, p2) == 1

    for i in range(n):
        for j in range(i + 1, n):
            b1, b2 = boxes[i], boxes[j]
            if not _is_adjacent(b1, b2):
                continue
            g1 = goals[assignment[i]]
            g2 = goals[assignment[j]]

            # Row conflict
            if b1.row == b2.row == g1.row == g2.row:
                if (b1.col < b2.col and g1.col > g2.col) or (b1.col > b2.col and g1.col < g2.col):
                    conflicts += 1
                    continue

            # Column conflict
            if b1.col == b2.col == g1.col == g2.col:
                if (b1.row < b2.row and g1.row > g2.row) or (b1.row > b2.row and g1.row < g2.row):
                    conflicts += 1

    return conflicts


# "standard" heuristic for sokoban
# Reference: Pereira et al., "Improved Heuristic and Tie-Breaking for Optimally Solving Sokoban"
#            IJCAI 2016 — https://www.ijcai.org/Proceedings/16/Papers/100.pdf
def emm_heuristic(state: SokobanState) -> int:
    """Enhanced Minimum Matching heuristic with simple linear conflict cost.

    This implementation computes a minimum-cost perfect matching between boxes and goals
    where the edge cost is the Manhattan distance from the player to the box plus the
    Manhattan distance from the box to the goal.

    It then adds 2 for each linear conflict detected between adjacent boxes.

    Admissible ? Yes -> linear conflict adds "at least" 2 extra moves so it never overestimates
    fixing a "reversed order" pair ( two adjacent boxes needing to swap positions) requires at least 2 extra pushes 
    """
    boxes = list(state.boxes)
    goals = list(state.goals)

    if not boxes:
        return 0

    # Cost matrix: only box-to-goal distances
    cost_matrix = [
        [manhattan_distance(box, goal) for goal in goals]
        for box in boxes
    ]

    matching_cost, assignment = _hungarian_min_cost_assignment(cost_matrix)
    linear_conflicts = _linear_conflicts(boxes, goals, assignment)
    player_to_nearest_box = min(manhattan_distance(state.player, box) for box in boxes)

    return matching_cost + 2 * linear_conflicts + player_to_nearest_box

    