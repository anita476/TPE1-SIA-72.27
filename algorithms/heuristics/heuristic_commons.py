from utils.state import Position



def manhattan_distance(pos1: Position, pos2: Position) -> int:
    return abs(pos1.row - pos2.row) + abs(pos1.col - pos2.col)


def hungarian_min_cost_assignment(cost_matrix: list[list[int]]) -> tuple[int, list[int]]:
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






