import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

from algorithms.algorithms import HEURISTICS
from run_all_levels import run_level

SEPARATOR = "-" * 60


def run_level_all_heuristics(level_path: Path, heuristics: list[str], timeout: int) -> dict:
    results = {}
    for heuristic in heuristics:
        _, result, error_msg = run_level(
            level_path, "astar", timeout, verbose=False,
            heuristic_name=heuristic,
        )
        results[heuristic] = (result, error_msg)
    return results


def format_cell(result, error_msg: str | None) -> str:
    if error_msg == "Timeout":
        return "TIMEOUT"
    if result is None:
        return f"ERR ({error_msg})"
    if result.success:
        return (
            f"OK costo={result.cost} pushes={result.boxes_displaced} "
            f"nodos expandidos={result.expanded_nodes} tiempo={result.processing_time:.2f}s "
            f"memoria={result.memory_kb:.0f}KB"
        )
    return "FAILED"


def main():
    parser = argparse.ArgumentParser(description="Compare heuristics using A* on all levels")
    parser.add_argument("--timeout", type=int, default=60, help="Seconds per level")
    parser.add_argument(
        "--heuristics",
        nargs="+",
        default=list(HEURISTICS.keys()),
        choices=list(HEURISTICS.keys()),
        help="Heuristics to compare (space-separated)",
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

    heuristics = args.heuristics
    print(f"Comparing {len(heuristics)} heuristics (A*) on {len(level_files)} levels (timeout: {args.timeout}s)\n")
    print(SEPARATOR)

    all_results = {}
    for level_path in level_files:
        level_name = level_path.stem
        all_results[level_name] = run_level_all_heuristics(
            level_path, heuristics, args.timeout,
        )
        print(f"\n{level_name}")
        for h in heuristics:
            result, error_msg = all_results[level_name][h]
            print(f"  {h:45}: {format_cell(result, error_msg)}")

    print(f"\n{SEPARATOR}")
    print("\nSummary (solved / total):")
    for h in heuristics:
        solved = sum(
            1 for r in all_results.values()
            for res, err in [r[h]]
            if res and res.success
        )
        print(f"  {h:45}: {solved}/{len(level_files)}")


if __name__ == "__main__":
    main()
