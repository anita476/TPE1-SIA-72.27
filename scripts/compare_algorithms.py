import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from pathlib import Path

from algorithms.algorithms import ALGORITHMS
from run_all_levels import run_level

SEPARATOR = "-" * 80


def run_level_all_algorithms(level_path: Path, algorithms: list[str], timeout: int) -> dict:
    results = {}
    for algorithm in algorithms:
        level_name, result, error_msg = run_level(
            level_path, algorithm, timeout, verbose=False
        )
        results[algorithm] = (result, error_msg)
    return results


def format_cell(result, error_msg: str | None, timeout: int) -> str:
    if error_msg == "Timeout":
        return f"TIMEOUT"
    if result is None:
        return "ERR"
    if result.success:
        return f"OK c={result.cost} b={result.boxes_displaced} n={result.expanded_nodes} t={result.processing_time:.2f}s m={result.memory_kb:.0f}KB"
    return "FAILED"


def main():
    parser = argparse.ArgumentParser(description="Compare all algorithms on all levels")
    parser.add_argument("--timeout", type=int, default=60, help="Seconds per level")
    parser.add_argument(
        "--algorithms",
        nargs="+",
        default=list(ALGORITHMS.keys()),
        choices=list(ALGORITHMS.keys()),
        help="Algorithms to compare (space-separated)",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    levels_dir = root / "levels"
    level_files = sorted(
        levels_dir.glob("level*.txt"),
        key=lambda p: int((p.stem.replace("level", "") or "0")),
    )

    if not level_files:
        print(f"No level files found in {levels_dir}")
        return

    algorithms = args.algorithms
    all_results = {}

    print(f"Comparing {len(algorithms)} algorithms on {len(level_files)} levels (timeout: {args.timeout}s)\n")
    print(SEPARATOR)

    for level_path in level_files:
        level_name = level_path.stem
        all_results[level_name] = run_level_all_algorithms(
            level_path, algorithms, args.timeout
        )

        print(f"\n{level_name}")
        for alg in algorithms:
            result, error_msg = all_results[level_name][alg]
            cell = format_cell(result, error_msg, args.timeout)
            print(f"  {alg:8}: {cell}")

    print(SEPARATOR)
    print("\nSummary (solved / total):")
    for alg in algorithms:
        solved = sum(
            1 for r in all_results.values()
            for res, err in [r[alg]]
            if res and res.success
        )
        print(f"  {alg}: {solved}/{len(level_files)}")


if __name__ == "__main__":
    main()
