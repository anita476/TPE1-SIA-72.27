import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from utils.state import parse_level
from algorithms.algorithms import ALGORITHMS


def main():
    parser = argparse.ArgumentParser(description="Sokoban Solver")
    parser.add_argument("--level", type=str, default="levels/level1.txt", help="Path to level file")
    parser.add_argument("--algorithm", type=str, default="dfs", choices=ALGORITHMS.keys(), help="Search algorithm")
    args = parser.parse_args()

    state = parse_level(args.level)
    print("Initial state:")
    print(state)
    print()

    search_fn = ALGORITHMS[args.algorithm]
    result = search_fn(state)
    print(result)


if __name__ == "__main__":
    main()
