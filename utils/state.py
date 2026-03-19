from enum import StrEnum


class AsciiSokoban(StrEnum):
    EMPTY = " "
    GOAL = "."
    WALL = "#"
    BOX = "$"
    PLAYER = "@"
    BOX_ON_GOAL = "*"
    PLAYER_ON_GOAL = "+"


class Direction:
    UP = (-1, 0)
    DOWN = (1, 0)
    LEFT = (0, -1)
    RIGHT = (0, 1)


ALL_DIRECTIONS = [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]


DIRECTION_NAMES = {
    Direction.UP: "UP",
    Direction.DOWN: "DOWN",
    Direction.LEFT: "LEFT",
    Direction.RIGHT: "RIGHT",
}


class Position:
    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col

    def __add__(self, direction: tuple) -> "Position":
        return Position(self.row + direction[0], self.col + direction[1])

    def __eq__(self, other):
        return isinstance(other, Position) and self.row == other.row and self.col == other.col

    def __hash__(self):
        return hash((self.row, self.col))

    def __repr__(self):
        return f"({self.row}, {self.col})"


class SokobanState:
    def __init__(self, player: Position, boxes: frozenset, goals: frozenset, walls: frozenset, rows: int, cols: int, matrix=None):
        self.player = player
        self.boxes = boxes
        self.goals = goals
        self.walls = walls
        self.rows = rows
        self.cols = cols

        self.matrix = matrix if matrix is not None else self._build_matrix()

    def _build_matrix(self):
        grid = [[AsciiSokoban.EMPTY for _ in range(self.cols)] for _ in range(self.rows)]

        for wall in self.walls:
            grid[wall.row][wall.col] = AsciiSokoban.WALL

        for goal in self.goals:
            if grid[goal.row][goal.col] == AsciiSokoban.WALL:
                continue
            grid[goal.row][goal.col] = AsciiSokoban.GOAL

        for box in self.boxes:
            if grid[box.row][box.col] == AsciiSokoban.GOAL:
                grid[box.row][box.col] = AsciiSokoban.BOX_ON_GOAL
            else:
                grid[box.row][box.col] = AsciiSokoban.BOX

        if self.player is not None:
            p = self.player
            if grid[p.row][p.col] == AsciiSokoban.GOAL:
                grid[p.row][p.col] = AsciiSokoban.PLAYER_ON_GOAL
            else:
                grid[p.row][p.col] = AsciiSokoban.PLAYER

        return tuple(tuple(row) for row in grid)

    def cell_type(self, pos: Position):
        """Return the AsciiSokoban value for a position, or None if out of bounds."""
        if pos.row < 0 or pos.row >= self.rows or pos.col < 0 or pos.col >= self.cols:
            return None
        return self.matrix[pos.row][pos.col]

    def is_solved(self) -> bool:
        return self.boxes == self.goals

    def __eq__(self, other):
        return isinstance(other, SokobanState) and self.player == other.player and self.boxes == other.boxes

    def __hash__(self):
        return hash((self.player, self.boxes))

    def __str__(self):
        return "\n".join("".join(row) for row in self.matrix)


def parse_level(file_path: str) -> SokobanState:
    with open(file_path, "r") as f:
        lines = f.read().splitlines()

    rows = len(lines)
    cols = max(len(line) for line in lines) if lines else 0

    # Build matrix and extract positions during parsing
    matrix = [[AsciiSokoban.EMPTY for _ in range(cols)] for _ in range(rows)]
    player = None
    boxes = set()
    goals = set()
    walls = set()

    for row, line in enumerate(lines):
        for col, char in enumerate(line):
            #  all cells are initialized (pad with EMPTY if needed)
            if col < len(line):
                matrix[row][col] = char
            pos = Position(row, col)

            if char == AsciiSokoban.WALL:
                walls.add(pos)
            elif char == AsciiSokoban.PLAYER:
                player = pos
            elif char == AsciiSokoban.BOX:
                boxes.add(pos)
            elif char == AsciiSokoban.GOAL:
                goals.add(pos)
            elif char == AsciiSokoban.BOX_ON_GOAL:
                boxes.add(pos)
                goals.add(pos)
            elif char == AsciiSokoban.PLAYER_ON_GOAL:
                player = pos
                goals.add(pos)

    if player is None:
        raise ValueError(f"No player found in level file: {file_path}")

    if len(boxes) != len(goals):
        raise ValueError(f"Number of boxes ({len(boxes)}) does not match number of goals ({len(goals)})")

    # Convert matrix to immutable form and pass it directly
    matrix_tuple = tuple(tuple(row) for row in matrix)
    return SokobanState(player, frozenset(boxes), frozenset(goals), frozenset(walls), rows, cols, matrix_tuple)


def move(state: SokobanState, direction: tuple) -> SokobanState:
    new_player_pos = state.player + direction

    # Can't move into a wall
    if new_player_pos in state.walls:
        return state

    # Moving into a box: check if box can be pushed
    if new_player_pos in state.boxes:
        new_box_pos = new_player_pos + direction
        if new_box_pos in state.walls or new_box_pos in state.boxes:
            return state
        new_boxes = (state.boxes - {new_player_pos}) | {new_box_pos}
        return SokobanState(new_player_pos, frozenset(new_boxes), state.goals, state.walls, state.rows, state.cols)

    # Normal move into empty space
    return SokobanState(new_player_pos, state.boxes, state.goals, state.walls, state.rows, state.cols)


def get_successors(state: SokobanState) -> list[tuple[tuple, SokobanState]]:
    successors = []
    for direction in ALL_DIRECTIONS:
        new_state = move(state, direction)
        if new_state != state:
            successors.append((direction, new_state))
    return successors
