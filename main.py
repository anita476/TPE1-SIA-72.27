import sys
from utils.state import parse_level
from utils.search import dfs


def main():
    level_file = sys.argv[1] if len(sys.argv) > 1 else "levels/level1.txt"

    state = parse_level(level_file)
    print("Initial state:")
    print(state)
    print()

    result = dfs(state)
    print(result)


if __name__ == "__main__":
    main()
