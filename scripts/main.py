import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from utils.state import parse_level
from algorithms.algorithms import ALGORITHMS, HEURISTICS, HEURISTIC_ALGORITHMS


def main():
    parser = argparse.ArgumentParser(description="Sokoban Solver")
    parser.add_argument("--level", type=str, default="levels/level1.txt", help="Path to level file")
    parser.add_argument("--algorithm", type=str, default="dfs", choices=ALGORITHMS.keys(), help="Search algorithm")
    parser.add_argument(
        "--heuristic",
        type=str,
        default="emm",
        choices=HEURISTICS.keys(),
        help="Heuristic function (only used by greedy and astar)",
    )
    args = parser.parse_args()

    state = parse_level(args.level)
    print("Initial state:")
    print(state)
    print()

    search_fn = ALGORITHMS[args.algorithm]
    if args.algorithm in HEURISTIC_ALGORITHMS:
        result = search_fn(state, heuristic=HEURISTICS[args.heuristic])
    else:
        result = search_fn(state)
    print(result)


if __name__ == "__main__":
    main()
