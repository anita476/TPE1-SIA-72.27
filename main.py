import sys
from utils.state import parse_level, move, Direction


def main():
    level_file = sys.argv[1] if len(sys.argv) > 1 else "levels/level1.txt"
    state = parse_level(level_file)

    directions = {
        "w": Direction.UP,
        "s": Direction.DOWN,
        "a": Direction.LEFT,
        "d": Direction.RIGHT,
    }

    print("Sokoban - Use WASD to move, Q to quit")
    print(state)

    while not state.is_solved():
        key = input("Move: ").strip().lower()
        if key == "q":
            print("Goodbye!")
            return
        if key in directions:
            state = move(state, directions[key])
            print(state)
        else:
            print("Invalid input. Use WASD to move, Q to quit.")

    print("Congratulations! Level solved!")


if __name__ == "__main__":
    main()
