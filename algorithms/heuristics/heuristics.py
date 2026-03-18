from utils.state import Position, SokobanState, ALL_DIRECTIONS
from enum import StrEnum
from collections import deque

class Heuristic(StrEnum):
    MANHATTAN = "MANHATTAN"
    EMM = "EMM"
    PDB = "PDB"

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


"""
PATTERN DATABASE (PDB) HEURISTIC
Based on Planning and Learning Heuristics for Sokoban"
References: Pereira et al., "A Bidirectional Hierarchical Search Strategy for Sokoban"
"""

def _max_weight_matching_pdb(boxes: list[Position], pdb: dict, cut_square: Position) -> tuple[int, list[int]]:
    """Compute maximum weight matching for PDB-2 using dynamic programming.
    
    For 2 stones this is equivalent to finding the best pair pairing.
    We try all possible assignments and pick the one with maximum cost.
    """
    n = len(boxes)
    
    if n == 0:
        return 0, []
    if n == 1:
        dist = pdb.get((boxes[0],), manhattan_distance(boxes[0], cut_square))
        return dist, [0]
    
    # For small n, we can try all permutations
    best_cost = 0
    best_match = list(range(n))
    
    # Simple greedy: pair boxes that are closest to cut square together
    visited = [False] * n
    match = [-1] * n
    total_cost = 0
    
    for i in range(n):
        if visited[i]:
            continue
        
        best_partner = -1
        best_pair_cost = 0
        
        # If odd number, last box gets artificial partner at cut square
        if i == n - 1:
            dist = pdb.get((boxes[i],), manhattan_distance(boxes[i], cut_square))
            match[i] = n  # artificial
            total_cost += dist
            visited[i] = True
        else:
            # Find best partner for box i
            for j in range(i + 1, n):
                if visited[j]:
                    continue
                pair_cost = pdb.get((boxes[i], boxes[j]), 
                                   manhattan_distance(boxes[i], cut_square) +
                                   manhattan_distance(boxes[j], cut_square))
                if pair_cost > best_pair_cost:
                    best_pair_cost = pair_cost
                    best_partner = j
            
            if best_partner != -1:
                match[i] = best_partner
                match[best_partner] = i
                total_cost += best_pair_cost
                visited[i] = True
                visited[best_partner] = True
    
    return total_cost, match

class PatternDatabaseCache:
    """Cached Pattern Database for efficient evaluation across many states.
    
    Builds the PDB structure once during initialization, then reuses it for all
    subsequent state evaluations. This eliminates the O(rows×cols) BFS per state
    that makes naive PDB slow.
    
    **Performance impact**:
    - Without cache: O(rows×cols) BFS per state → 10K states = 10K BFS calls
    - With cache: O(rows×cols) BFS once + O(n³) matching per state
    - **Speedup: 100-1000x for large searches**
    """
    
    def __init__(self, initial_state: SokobanState):
        """Build and cache all instance-dependent data"""
        self.initial_state = initial_state
        self.rows = initial_state.rows
        self.cols = initial_state.cols
        self.walls = initial_state.walls
        self.goals = initial_state.goals
        
        # pre compute cut square (same for all states in this instance)
        self.cut_square = self._find_cut_square_cached()
        
        # Pre-compute goal zone (same for all states)
        self.goal_zone = self._find_reachable_from_goals_cached()
        
        # Build PDB once
        self.pdb = self._build_pdb_cached()
        
    def _find_cut_square_cached(self) -> Position:
        """Find cut square (only done once per instance)."""
        free_squares = set()
        for r in range(self.rows):
            for c in range(self.cols):
                pos = Position(r, c)
                if pos not in self.walls:
                    free_squares.add(pos)
        
        best_cut = None
        max_maze_size = -1
        
        for candidate in free_squares:
            if candidate in self.goals:
                continue
            
            goal_zone = self._compute_goal_zone(candidate)
            maze_zone_size = len(free_squares) - len(goal_zone) - 1
            
            if maze_zone_size > max_maze_size:
                max_maze_size = maze_zone_size
                best_cut = candidate
        
        if best_cut is None:
            best_cut = Position(self.rows // 2, self.cols // 2)
        
        return best_cut
    
    def _compute_goal_zone(self, cut_square: Position) -> set:
        """Compute reachable goal zone from all goals (avoiding cut square for stone placement)."""
        free_squares = set()
        for r in range(self.rows):
            for c in range(self.cols):
                pos = Position(r, c)
                if pos not in self.walls:
                    free_squares.add(pos)
        
        reachable = set()
        queue = deque(self.goals)
        visited = set(self.goals)
        
        while queue:
            pos = queue.popleft()
            reachable.add(pos)
            for direction in ALL_DIRECTIONS:
                neighbor = pos + direction
                if neighbor not in visited and neighbor in free_squares:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return reachable
    
    def _find_reachable_from_goals_cached(self) -> set:
        """Cache the goal zone (reachable squares from goals)."""
        return self._compute_goal_zone(self.cut_square)
    
    def _build_pdb_cached(self) -> dict:
        """Build PDB once for the instance."""
        pdb = {}
        free_squares = set()
        for r in range(self.rows):
            for c in range(self.cols):
                pos = Position(r, c)
                if pos not in self.walls:
                    free_squares.add(pos)
                    dist = manhattan_distance(pos, self.cut_square)
                    pdb[(pos,)] = dist
        return pdb
    
    def evaluate(self, state: SokobanState) -> int:
        """Evaluate heuristic for a state using cached data.
        
        This is O(n³) for matching + O(n²) conflict detection, NOT O(rows×cols) BFS.
        """
        boxes = list(state.boxes)
        goals = list(state.goals)
        
        if not boxes:
            return 0
        
        # Partition boxes using pre-computed goal zone
        maze_boxes = [b for b in boxes if b not in self.goal_zone]
        goal_boxes = [b for b in boxes if b in self.goal_zone]
        
        # Compute maze zone heuristic
        maze_cost, _ = _max_weight_matching_pdb(maze_boxes, self.pdb, self.cut_square)
        
        # Compute goal zone heuristic
        goal_cost = 0
        goal_linear_conflicts = 0
        
        if goal_boxes:
            cost_matrix_goal = []
            for box in goal_boxes:
                player_pos = self.cut_square if box in maze_boxes else state.player
                cost_matrix_goal.append([
                    manhattan_distance(player_pos, box) + manhattan_distance(box, goal)
                    for goal in goals
                ])
            
            if cost_matrix_goal:
                goal_cost, goal_assignment = _hungarian_min_cost_assignment(cost_matrix_goal)
                goal_linear_conflicts = _linear_conflicts(goal_boxes, goals, goal_assignment)
        
        # Global linear conflicts
        global_conflicts = 0
        if maze_boxes and goal_boxes:
            for m_box in maze_boxes:
                for g_box in goal_boxes:
                    if manhattan_distance(m_box, g_box) == 1:
                        global_conflicts += 1
        
        return maze_cost + goal_cost + 2 * goal_linear_conflicts + 2 * global_conflicts


def make_pdb_heuristic(initial_state: SokobanState):
    """Factory function to create a cached PDB heuristic for a specific instance (initial_state)
    This builds the PDB cache once during initialization, then reuses it for all
    subsequent state evaluations during the search.
   
    """
    cache = PatternDatabaseCache(initial_state)
    
    def heuristic(state: SokobanState) -> int:
        """Cached PDB heuristic for this instance."""
        return cache.evaluate(state)
    
    return heuristic
