from utils.state import AsciiSokoban, Position, SokobanState, ALL_DIRECTIONS, Direction
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


def _is_wall_or_out_of_bounds(pos: Position, state: SokobanState) -> bool:
    """Return True if the position is outside the board or is a wall"""
    if pos.row < 0 or pos.row >= state.rows or pos.col < 0 or pos.col >= state.cols:
        return True
    return state.matrix[pos.row][pos.col] == AsciiSokoban.WALL


def _is_goal_cell(pos: Position, state: SokobanState) -> bool:
    if pos.row < 0 or pos.row >= state.rows or pos.col < 0 or pos.col >= state.cols:
        return False
    cell = state.matrix[pos.row][pos.col]
    return cell in (AsciiSokoban.GOAL, AsciiSokoban.BOX_ON_GOAL, AsciiSokoban.PLAYER_ON_GOAL)


def _compute_all_deadlock_positions(state: SokobanState) -> frozenset:
    """Pre-compute all positions that would cause a deadlock in the current level.
    
    This includes:
    1. Corner deadlocks: positions in corners (blocked by 2 perpendicular walls)
    2. Edge deadlocks: positions along walls extending from corners, but ONLY if
       no goals are reachable within that edge corridor
    """
    deadlock_set = set()

    # first: find all corner deadlocks
    corner_deadlocks = set()
    for row in range(state.rows):
        for col in range(state.cols):
            pos = Position(row, col)

            # Skip walls and goals
            if _is_wall_or_out_of_bounds(pos, state) or _is_goal_cell(pos, state):
                continue

            if _is_corner_deadlock(pos, state):
                corner_deadlocks.add(pos)
                deadlock_set.add(pos)

    # second : use these corners to "travel" through indirect deadlock edges
    for corner in corner_deadlocks:
        deadlock_set.update(_find_edge_deadlocks_from_corner(corner, state))

    return frozenset(deadlock_set)


def _find_edge_deadlocks_from_corner(corner: Position, state: SokobanState) -> set:
    """
    From a corner, we travel along edges in the two directions that lead AWAY
    from the corner
    """
    edge_deadlocks = set()

    # Determine which corner type this is and the directions to explore
    up = corner + Direction.UP
    down = corner + Direction.DOWN
    left = corner + Direction.LEFT
    right = corner + Direction.RIGHT

    up_wall = _is_wall_or_out_of_bounds(up, state)
    down_wall = _is_wall_or_out_of_bounds(down, state)
    left_wall = _is_wall_or_out_of_bounds(left, state)
    right_wall = _is_wall_or_out_of_bounds(right, state)

    if up_wall and left_wall:
        # TOPLEFT: travel DOWN and RIGHT
        edge_deadlocks.update(_travel_edge(corner, Direction.DOWN, state))
        edge_deadlocks.update(_travel_edge(corner, Direction.RIGHT, state))
    elif up_wall and right_wall:
        # TOPRIGHT : travel DOWN and LEFT
        edge_deadlocks.update(_travel_edge(corner, Direction.DOWN, state))
        edge_deadlocks.update(_travel_edge(corner, Direction.LEFT, state))
    elif down_wall and left_wall:
        # BOTTOMLEFT : travel UP and RIGHT
        edge_deadlocks.update(_travel_edge(corner, Direction.UP, state))
        edge_deadlocks.update(_travel_edge(corner, Direction.RIGHT, state))
    elif down_wall and right_wall:
        # BOTTOM RIGHT: travel UP and LEFT
        edge_deadlocks.update(_travel_edge(corner, Direction.UP, state))
        edge_deadlocks.update(_travel_edge(corner, Direction.LEFT, state))

    return edge_deadlocks


def _travel_edge(start: Position, primary_direction: tuple, state: SokobanState) -> set:
    """
    Travel in primary_direction as long as:
    * The position is not a wall -> WE HAVE REACHED THE OTHER CORNER
    * The position is not a goal
    * The position has AT LEAST ONE wall perpendicular to travel direction (that would trap a box)
    
    If any position lacks a perpendicular wall, clear the collected positions
    (the edge is broken and remaining positions are not deadlocked).
    """
    edge_deadlocks = set()
    current = start + primary_direction

    # Determine perpendicular directions based on travel direction
    if primary_direction == Direction.DOWN or primary_direction == Direction.UP:
        # Traveling vertically: perpendicular directions are LEFT/RIGHT
        perpendicular_directions = [Direction.LEFT, Direction.RIGHT]
    else:
        # Traveling horizontally: perpendicular directions are UP/DOWN
        perpendicular_directions = [Direction.UP, Direction.DOWN]

    while not _is_wall_or_out_of_bounds(current, state):
        # If we hit a goal on this edge, the entire edge is NOT deadlocked
        if _is_goal_cell(current, state):
            return set()  # Empty set means edge is not deadlock

        # Check if this position is "trapped" on both perpendicular sides
        perp_walls = [_is_wall_or_out_of_bounds(current + perp_dir, state) 
                      for perp_dir in perpendicular_directions]

        # For an edge deadlock, BOTH perpendicular sides must have walls
        if not all(perp_walls):
            # Missing wall on at least one perpendicular side -> edge breaks here
            edge_deadlocks.clear()
            break

        # This position is deadlocked (walls on both perpendicular sides)
        edge_deadlocks.add(current)

        # Move to next position
        current = current + primary_direction

    return edge_deadlocks


def _is_corner_deadlock(box_pos: Position, state: SokobanState) -> bool:
    """Detect corner deadlock: box is in a corner and NOT on a goal."""
    if _is_goal_cell(box_pos, state):
        return False  # box on a goal is safe

    up = box_pos + Direction.UP
    down = box_pos + Direction.DOWN
    left = box_pos + Direction.LEFT
    right = box_pos + Direction.RIGHT

    up_wall = _is_wall_or_out_of_bounds(up, state)
    down_wall = _is_wall_or_out_of_bounds(down, state)
    left_wall = _is_wall_or_out_of_bounds(left, state)
    right_wall = _is_wall_or_out_of_bounds(right, state)

    if up_wall and left_wall:
        return True
    if up_wall and right_wall:
        return True
    if down_wall and left_wall:
        return True
    if down_wall and right_wall:
        return True

    return False


def _box_in_deadlock(box_pos: Position, state: SokobanState, deadlock_positions: frozenset) -> bool:
    """
    Check if a box is in a deadlock position.
    Uses pre-computed frozenset for O(1) lookup time.
    """
    # Direct O(1) frozenset lookup (hashed)
    return box_pos in deadlock_positions


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


def print_deadlock_map(state: SokobanState, deadlock_positions: frozenset) -> None:
    result = []
    for row in range(state.rows):
        line = []
        for col in range(state.cols):
            pos = Position(row, col)
            if pos in deadlock_positions:
                line.append('X')
            else:
                line.append(state.matrix[row][col])
        result.append("".join(line))
    print("\nDeadlock Map:")
    print("\n".join(result))
    print(f"\nTotal deadlock positions: {len(deadlock_positions)}")
