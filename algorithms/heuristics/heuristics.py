from utils.state import Position, SokobanState, ALL_DIRECTIONS, Direction
from enum import StrEnum
from collections import deque

# CACHE OF DEADLOCK POS
_deadlock_positions_cache = None  


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






# DEADLOCK RELATED FUNCTIONS


def _compute_all_deadlock_positions(state: SokobanState) -> frozenset:
    """
    pre-compute all positions that would cause a deadlock in the current level
    """
    deadlock_set = set()
    
    for row in range(state.rows):
        for col in range(state.cols):
            pos = Position(row, col)
            
            # Skip walls and goals
            if pos in state.walls or pos in state.goals:
                continue
            
            if _is_corner_deadlock(pos, state.walls, state.goals, state.rows, state.cols):
                deadlock_set.add(pos)
                continue

    
    return frozenset(deadlock_set)


def _is_position_wall_or_out_of_bounds(pos: Position, walls: frozenset, rows: int, cols: int) -> bool:
    return pos in walls or pos.row < 0 or pos.row >= rows or pos.col < 0 or pos.col >= cols

def _is_corner_deadlock(box_pos: Position, walls: frozenset, goals: frozenset, rows: int, cols: int) -> bool:
    """
    Detect corner deadlock: box is in a corner and NOT on a goal.
    
    Examples of corners:
    Combinations:
    * top -left
    * top - right
    * bottom -left 
    * bottom right
    """
    if box_pos in goals:
        return False  # box on a goal is safe
    
    up = box_pos + Direction.UP
    down = box_pos + Direction.DOWN
    left = box_pos + Direction.LEFT
    right = box_pos + Direction.RIGHT
    
    up_wall = _is_position_wall_or_out_of_bounds(up, walls, rows, cols)
    down_wall = _is_position_wall_or_out_of_bounds(down, walls, rows, cols)
    left_wall = _is_position_wall_or_out_of_bounds(left, walls, rows, cols)
    right_wall = _is_position_wall_or_out_of_bounds(right, walls, rows, cols)
    
    if up_wall and left_wall:
        return True  
    if up_wall and right_wall:
        return True 
    if down_wall and left_wall:
        return True 
    if down_wall and right_wall:
        return True  
    
    return False


def _is_edge_deadlock(box_pos: Position, deadlock_positions: frozenset) -> bool:
    return box_pos in deadlock_positions


def _is_unreachable_deadlock(box_pos: Position, walls: frozenset, goals: frozenset, 
                           other_boxes: frozenset, rows: int, cols: int) -> bool:
    """
    Detect unreachable deadlock: box is between walls with no accessible goal.
    
    USE BFS to check if the box can reach any goal given wall constraints
    If all neighbors are walls or another box, and no goal is reachable, it's a deadlock
    """
    if box_pos in goals:
        return False
    
    # if all 4 directions have walls or boxes, it's definitely unreachable
    all_neighbors_blocked = True
    for direction in ALL_DIRECTIONS:
        neighbor = box_pos + direction
        is_blocked = (_is_position_wall_or_out_of_bounds(neighbor, walls, rows, cols) or
                     neighbor in other_boxes)
        if not is_blocked:
            all_neighbors_blocked = False
            break
    
    if all_neighbors_blocked:
        return True
    
    # BFS to check if any goal is reachable from the box position
    # (ignoring other boxes, considering only walls as obstacles)
    visited = set()
    queue = deque([box_pos])
    visited.add(box_pos)
    
    while queue:
        current = queue.popleft()
        
        if current in goals:
            return False  # Goal is reachable!
        
        # Explore neighbors (walls are obstacles)
        for direction in ALL_DIRECTIONS:
            neighbor = current + direction
            
            if neighbor in visited:
                continue
            if _is_position_wall_or_out_of_bounds(neighbor, walls, rows, cols):
                continue
            
            visited.add(neighbor)
            queue.append(neighbor)
    
    # if i can reach no goal -> unreachable
    return True


def _box_in_deadlock(box_pos: Position, state: SokobanState, deadlock_positions: frozenset) -> bool:
    """
    Check cases of deadlock for this box.
    Uses pre-computed deadlock positions for efficiency (includes corners and edge deadlocks).
    """
    other_boxes = frozenset(b for b in state.boxes if b != box_pos)
    
    # edge deadlock check with cache
    if _is_edge_deadlock(box_pos, deadlock_positions):
        return True
    
    # if im not in a dead spot, can i reach at least one goal?
    if _is_unreachable_deadlock(box_pos, state.walls, state.goals, other_boxes, state.rows, state.cols):
        return True
    
    return False


def deadlock_heuristic(state: SokobanState) -> int:
    """
    Deadlock Detection Heuristic with caching.
    Pre-computes edge deadlock positions once per level, then reuses them.
    Includes corner and edge deadlocks in cached positions
    """
    global _deadlock_positions_cache
        
    # Initialize or update cache if needed (new level detected)
    if _deadlock_positions_cache is None:
        _deadlock_positions_cache = _compute_all_deadlock_positions(state)
    
    for box in state.boxes:
        if _box_in_deadlock(box, state, _deadlock_positions_cache):
            return float('inf')  # unsolvable
    
    return 0  # state is potentially solvable 


def combination_heuristic(state: SokobanState) -> int:
    return max(deadlock_heuristic(state), emm_heuristic(state))