import argparse
from multiprocessing import Process, Queue
from pathlib import Path

from utils.state import parse_level, DIRECTION_NAMES
from algorithms.algorithms import ALGORITHMS

SEPARATOR = "-" * 60


def run_search(level_path: str, algorithm: str, result_queue: Queue) -> None:
    try:
        state = parse_level(level_path)
        result = ALGORITHMS[algorithm](state)
        result_queue.put(("ok", result))
    except Exception as e:
        result_queue.put(("error", str(e)))


def run_level(level_path: Path, algorithm: str, timeout: int, verbose: bool) -> tuple:
    level_name = level_path.stem
    level_str = str(level_path.resolve())

    try:
        state = parse_level(level_str)
    except Exception as e:
        return (level_name, None, str(e))

    if verbose:
        print(f"\n{level_name}\n{state}\n")

    result_queue = Queue()
    proc = Process(target=run_search, args=(level_str, algorithm, result_queue))
    proc.start()
    proc.join(timeout=timeout)

    if proc.is_alive():
        proc.terminate()
        proc.join()
        return (level_name, None, "Timeout")

    try:
        queue_status, data = result_queue.get_nowait()
    except Exception:
        return (level_name, None, "Worker error")

    if queue_status == "error":
        return (level_name, None, data)

    result = data
    if result.success:
        error_msg = None
    else:
        error_msg = "No solution found"

    return (level_name, result, error_msg)


def format_result(level_name: str, result, error_msg: str | None, timeout: int) -> str:
    if error_msg == "Timeout":
        return f"{level_name}: TIMEOUT ({timeout}s)"
    if result is None:
        return f"{level_name}: ERROR - {error_msg}"
    if result.success:
        return (
            f"{level_name}: OK "
            f"(cost={result.cost}, expanded={result.expanded_nodes}, "
            f"time={result.processing_time:.2f}s, memory={result.memory_kb:.0f} KB)"
        )
    return f"{level_name}: FAILED"


def main():
    parser = argparse.ArgumentParser(description="Run all Sokoban levels sequentially")
    parser.add_argument("--algorithm", default="bfs", choices=ALGORITHMS.keys())
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--timeout", type=int, default=60, help="Seconds per level")
    args = parser.parse_args()

    levels_dir = Path("levels")
    level_files = sorted(
        levels_dir.glob("level*.txt"),
        key=lambda p: int((p.stem.replace("level", "") or "0")),
    )

    if not level_files:
        print(f"No level files found in {levels_dir}")
        return

    print(f"Running {len(level_files)} levels with {args.algorithm} (timeout: {args.timeout}s)\n")
    print(SEPARATOR)

    results = []
    for level_path in level_files:
        level_name, result, error_msg = run_level(
            level_path, args.algorithm, args.timeout, args.verbose
        )
        results.append((level_name, result, error_msg))

        msg = format_result(level_name, result, error_msg, args.timeout)
        print(msg)

        if args.verbose and result and result.success:
            path_str = " -> ".join(DIRECTION_NAMES[d] for d in result.path)
            print(f"  Solution: {path_str}\n")

    print(SEPARATOR)
    solved = sum(1 for _, r, _ in results if r and r.success)
    print(f"\nSummary: {solved}/{len(results)} levels solved")


if __name__ == "__main__":
    main()
