from enum import StrEnum
import csv

class AsciiSokoban(StrEnum):
    EMPTY_CHAR = " "
    GOAL_CHAR = "."
    WALL_CHAR = "#"
    BOX_CHAR = "$"
    PLAYER_CHAR = "@"
    BOX_ON_GOAL_CHAR = "*"
    PLAYER_ON_GOAL_CHAR = "+"
    
class Position:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

class Direction:
    TOP = (-1,0)
    BOTTOM = (1,0)
    LEFT = (0,-1)
    RIGHT = (0,1)

class Player:
    def __init__(self, position: Position):
        self.position = position

class Goal:
    def __init__(self, position: Position):
        self.position = position

class Goals:
    def __init__(self, goals: list[Goal]):
        self.goals = goals

class Box:
    def __init__(self, position: Position):
        self.position = position

class Boxes:
    def __init__(self, boxes: list[Box]):
        self.boxes = boxes

class SokobanState:
    def __init__(self, player: Player, boxes: Boxes, goals: Goals, walls: list[Position]):
        self.player = player
        self.boxes = boxes
        self.goals = goals
        self.walls = walls


# create state matrix from map
def create_matrix(file: str): #-> SokobanState:
    #sokobanState = SokobanState()
    with open(f"{file}", "r") as f:
        reader = csv.reader(f)
    
        for row in reader:
            for field in row:
                for char in field:
                    print(char)
    #             if (char == AsciiSokoban.PLAYER_CHAR.value): sokobanState.player = Player(Position(row.index(char), reader.line_num))
    #             if (char == AsciiSokoban.BOX_CHAR.value): sokobanState.boxes.append(Box(Position(row.index(char), reader.line_num)))
    #             if (char == AsciiSokoban.GOAL_CHAR.value): sokobanState.goals.append(Goal(Position(row.index(char), reader.line_num)))
    #             if (char == AsciiSokoban.WALL_CHAR.value): sokobanState.walls.append(Position(row.index(char), reader.line_num))
    # return sokobanState
        

# Get player position from matrix
def get_player(matrix: set) -> Player:
    return

# Get box positions from matrix
def get_boxes(matrix: set) -> Boxes:
    return

# Get goal positions from matrix
def get_goals(matrix: set) -> Goals:
    return
    
# Move player
def move_player(state: SokobanState, direction: Direction ) -> SokobanState:
    dx, dy = direction

    new_x = state.player.position.x + dx
    new_y = state.player.position.y + dy

    new_pos = Position(new_x, new_y)
    return SokobanState(new_pos, state.boxes, state.goals, state.walls)