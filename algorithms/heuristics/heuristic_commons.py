from collections import deque
from utils.state import Position, ALL_DIRECTIONS, SokobanState

# Basic utilities
def manhattan_distance(pos1: Position, pos2: Position) -> int:
    return abs(pos1.row - pos2.row) + abs(pos1.col - pos2.col)

def in_bounds(pos: Position, rows: int, cols: int) -> bool:
    return 0 <= pos.row < rows and 0 <= pos.col < cols

# Reachability
def reachable_cells(player: Position, walls: frozenset, blocked: frozenset,
                    rows: int, cols: int) -> frozenset:
    if not in_bounds(player, rows, cols) or player in walls or player in blocked:
        return frozenset()

    visited = {player}
    queue = deque([player])
    while queue:
        pos = queue.popleft()
        for d in ALL_DIRECTIONS:
            nxt = pos + d
            if in_bounds(nxt, rows, cols) and nxt not in walls and nxt not in blocked and nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return frozenset(visited)

# Single-stone push distances (BFS)
def exact_single_stone_push_distances(player: Position, box: Position,
                                       walls: frozenset, rows: int,
                                       cols: int) -> dict:
    """Minimum pushes to move one stone to every reachable square (ignoring other stones)."""
    if not in_bounds(player, rows, cols) or not in_bounds(box, rows, cols):
        return {}
    if player in walls or box in walls or player == box:
        return {}

    start = (box, player)
    state_cost = {start: 0}
    box_cost = {box: 0}
    queue = deque([start])

    while queue:
        cur_box, cur_player = queue.popleft()
        cost = state_cost[(cur_box, cur_player)]
        reachable = reachable_cells(cur_player, walls, frozenset({cur_box}), rows, cols)

        for d in ALL_DIRECTIONS:
            push_from = Position(cur_box.row - d[0], cur_box.col - d[1])
            push_to = cur_box + d

            if not in_bounds(push_from, rows, cols) or not in_bounds(push_to, rows, cols):
                continue
            if push_to in walls or push_from not in reachable:
                continue

            nxt = (push_to, cur_box)
            if nxt in state_cost:
                continue

            new_cost = cost + 1
            state_cost[nxt] = new_cost
            queue.append(nxt)

            if box_cost.get(push_to, new_cost + 1) > new_cost:
                box_cost[push_to] = new_cost

    return box_cost


def exact_push_distance(player: Position, box: Position, goal: Position,
                        walls: frozenset, rows: int, cols: int) -> float:
    return exact_single_stone_push_distances(player, box, walls, rows, cols).get(
        goal, float("inf")
    )

def hungarian_min_cost_assignment(cost_matrix: list[list[int]]) -> tuple[int, list[int]]:
    """Compute minimum-cost perfect matching for a square cost matrix.

    Returns (min_cost, match) where match[i] is the column assigned to row i.
    O(n^3) Hungarian algorithm — correct and admissible base for all heuristics.
    """
    n = len(cost_matrix)
    if n == 0:
        return 0, []

    cost = [row[:] for row in cost_matrix]
    u   = [0] * (n + 1)
    v   = [0] * (n + 1)
    p   = [0] * (n + 1)
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
            for j in range(n + 1):
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

    return -v[0], match


# Shared: build cost matrix -> hungarian -> check inf
def _matching_cost_from_matrix(cost_matrix, big):
    """Run Hungarian on a cost matrix and return the cost, or inf if any box is unassignable."""
    matching_cost, assignment = hungarian_min_cost_assignment(cost_matrix)
    if any(cost_matrix[i][assignment[i]] >= big for i in range(len(cost_matrix))):
        return float("inf")
    return matching_cost

# Exact Minimum Matching cost (hMM)
def exact_minimum_matching_cost(state: SokobanState) -> float:
    boxes = list(state.boxes)
    goals = list(state.goals)
    if not boxes:
        return 0

    big = state.rows * state.cols * state.rows * state.cols + 1
    cost_matrix = []

    for box in boxes:
        distances = exact_single_stone_push_distances(state.player, box,
                                                       state.walls, state.rows, state.cols)
        row = []
        reachable_any = False
        for goal in goals:
            d = distances.get(goal)
            if d is None:
                row.append(big)
            else:
                reachable_any = True
                row.append(d)
        if not reachable_any:
            return float("inf")
        cost_matrix.append(row)

    return _matching_cost_from_matrix(cost_matrix, big)

# Relaxed push distances (reverse BFS ignoring player position)
def _relaxed_push_distance_map(goal: Position, walls: frozenset,
                               rows: int, cols: int) -> dict:
    dist = {goal: 0}
    queue = deque([goal])
    while queue:
        pos = queue.popleft()
        cost = dist[pos]
        for d in ALL_DIRECTIONS:
            box_prev = Position(pos.row + d[0], pos.col + d[1])
            player_pos = Position(pos.row + 2 * d[0], pos.col + 2 * d[1])
            if not in_bounds(box_prev, rows, cols) or not in_bounds(player_pos, rows, cols):
                continue
            if box_prev in walls or player_pos in walls:
                continue
            if box_prev not in dist:
                dist[box_prev] = cost + 1
                queue.append(box_prev)
    return dist


def relaxed_push_matching_cost(state: SokobanState) -> float:
    boxes = list(state.boxes)
    goals = list(state.goals)
    if not boxes or state.is_solved():
        return 0

    push_maps = {g: _relaxed_push_distance_map(g, state.walls, state.rows, state.cols)
                 for g in goals}

    big = state.rows * state.cols * 4
    cost_matrix = []

    for box in boxes:
        row = []
        reachable_any = False
        for goal in goals:
            d = push_maps[goal].get(box)
            if d is None:
                row.append(big)
            else:
                reachable_any = True
                row.append(d)
        if not reachable_any:
            return float("inf")
        cost_matrix.append(row)

    return _matching_cost_from_matrix(cost_matrix, big)

# Walk lower bound
def walk_before_first_push_lb(state: SokobanState) -> int:
    if not state.boxes or state.is_solved():
        return 0
    return max(min(manhattan_distance(state.player, box) for box in state.boxes) - 1, 0)


# Linear-conflict detection (Pereira et al.)
def _hmm_two_stones(b1, b2, man, goals, walls, rows, cols):
    """hMM on a reduced instance with only two stones."""
    goals_list = list(goals)
    d1 = {g: exact_push_distance(man, b1, g, walls, rows, cols) for g in goals_list}
    d2 = {g: exact_push_distance(man, b2, g, walls, rows, cols) for g in goals_list}

    best = float("inf")
    for i in range(len(goals_list)):
        for j in range(i + 1, len(goals_list)):
            g1, g2 = goals_list[i], goals_list[j]
            best = min(best, d1[g1] + d2[g2], d1[g2] + d2[g1])
    return best


def _two_stone_successors(b1, b2, man, walls, rows, cols):
    """Push successors of a two-stone instance."""
    boxes = frozenset({b1, b2})
    reachable = reachable_cells(man, walls, boxes, rows, cols)
    seen = set()
    result = []

    for box, other in ((b1, b2), (b2, b1)):
        for d in ALL_DIRECTIONS:
            push_from = Position(box.row - d[0], box.col - d[1])
            push_to = box + d

            if not in_bounds(push_from, rows, cols) or not in_bounds(push_to, rows, cols):
                continue
            if push_to in walls or push_to == other or push_from not in reachable:
                continue

            key = (push_to, other, box)
            if key not in seen:
                seen.add(key)
                result.append(key)

    return result


def _is_linear_conflict(b1, b2, man, goals, walls, rows, cols):
    if manhattan_distance(b1, b2) != 1:
        return False

    current = _hmm_two_stones(b1, b2, man, goals, walls, rows, cols)
    if current == float("inf"):
        return False

    successors = _two_stone_successors(b1, b2, man, walls, rows, cols)
    if not successors:
        return False

    for nb1, nb2, nman in successors:
        if _hmm_two_stones(nb1, nb2, nman, goals, walls, rows, cols) < current + 1:
            return False
    return True


def _maximum_matching_size(conflict_pairs, n):
    """Maximum matching in a general graph via recursive backtracking."""
    adj = [[] for _ in range(n)]
    for i, j in conflict_pairs:
        adj[i].append(j)
        adj[j].append(i)

    def solve(remaining):
        if not remaining:
            return 0
        node = min(remaining)
        without = remaining - {node}
        best = solve(without)
        for neighbor in adj[node]:
            if neighbor in remaining:
                best = max(best, 1 + solve(without - {neighbor}))
        return best

    return solve(set(range(n)))


def count_linear_conflicts(state: SokobanState) -> int:
    boxes = list(state.boxes)
    pairs = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            if _is_linear_conflict(boxes[i], boxes[j], state.player,
                                   state.goals, state.walls, state.rows, state.cols):
                pairs.append((i, j))
    return _maximum_matching_size(pairs, len(boxes))
