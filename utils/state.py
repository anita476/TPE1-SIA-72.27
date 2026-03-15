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
    def __init__(self, player: Position, boxes: frozenset, goals: frozenset, walls: frozenset, rows: int, cols: int):
        self.player = player
        self.boxes = boxes
        self.goals = goals
        self.walls = walls
        self.rows = rows
        self.cols = cols

    def is_solved(self) -> bool:
        return self.boxes == self.goals

    def __eq__(self, other):
        return isinstance(other, SokobanState) and self.player == other.player and self.boxes == other.boxes

    def __hash__(self):
        return hash((self.player, self.boxes))

    def __str__(self):
        result = []
        for row in range(self.rows):
            line = []
            for col in range(self.cols):
                pos = Position(row, col)
                if pos in self.walls:
                    line.append(AsciiSokoban.WALL)
                elif pos == self.player and pos in self.goals:
                    line.append(AsciiSokoban.PLAYER_ON_GOAL)
                elif pos == self.player:
                    line.append(AsciiSokoban.PLAYER)
                elif pos in self.boxes and pos in self.goals:
                    line.append(AsciiSokoban.BOX_ON_GOAL)
                elif pos in self.boxes:
                    line.append(AsciiSokoban.BOX)
                elif pos in self.goals:
                    line.append(AsciiSokoban.GOAL)
                else:
                    line.append(AsciiSokoban.EMPTY)
            result.append("".join(line))
        return "\n".join(result)


def parse_level(file_path: str) -> SokobanState:
    with open(file_path, "r") as f:
        lines = f.read().splitlines()

    player = None
    boxes = set()
    goals = set()
    walls = set()

    for row, line in enumerate(lines):
        for col, char in enumerate(line):
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

    rows = len(lines)
    cols = max(len(line) for line in lines) if lines else 0

    return SokobanState(player, frozenset(boxes), frozenset(goals), frozenset(walls), rows, cols)


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
