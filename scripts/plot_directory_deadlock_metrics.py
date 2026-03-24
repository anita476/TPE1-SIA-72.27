"""
Plot per-level expanded nodes, deadlocks, and ratio-based metrics.

Runs each .txt level with either greedy or astar, forcing the deadlock heuristic.
Produces three separate figures:
  - expanded nodes per level
  - deadlock positions per level
  - expanded_nodes / deadlock_count per level
  - frontier / (expanded + frontier) per level

Requires: pip install matplotlib
"""

from __future__ import annotations

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, StrMethodFormatter

from algorithms.heuristics.deadlock import _compute_all_deadlock_positions
from run_all_levels import run_level
from utils.state import parse_level


IMAGE_SUFFIXES = frozenset({".png", ".pdf", ".svg", ".jpg", ".jpeg", ".webp"})


def find_level_files(levels_dir: Path) -> list[Path]:
    files = sorted(levels_dir.glob("*.txt"))
    if not files:
        raise SystemExit(f"No .txt level files found in {levels_dir}")
    return files


def level_numeric_key(path: Path) -> tuple[int, str]:
    stem = path.stem
    digits = "".join(ch for ch in stem if ch.isdigit())
    n = int(digits) if digits else 10**9
    return (n, stem)


def resolve_levels_dir(levels_dir_raw: str) -> Path:
    root = Path(__file__).resolve().parent.parent
    levels_dir = Path(levels_dir_raw)
    if not levels_dir.is_absolute():
        levels_dir = (root / levels_dir).resolve()
    if not levels_dir.is_dir():
        raise SystemExit(f"Directory not found: {levels_dir}")
    return levels_dir


def resolve_out_path(out_raw: str | None) -> Path | None:
    if out_raw is None:
        return None
    out = Path(out_raw)
    if not out.is_absolute():
        out = (Path.cwd() / out).resolve()
    if out.suffix.lower() not in IMAGE_SUFFIXES:
        out.mkdir(parents=True, exist_ok=True)
        out = out / "directory_deadlock_metrics"
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
    return out


def collect_metrics(
    level_files: list[Path], algorithm: str, timeout: int | None
) -> tuple[list[str], list[int], list[int], list[int], list[str]]:
    labels: list[str] = []
    expanded_nodes: list[int] = []
    deadlock_counts: list[int] = []
    frontier_nodes: list[int] = []
    errors: list[str] = []

    for level_path in sorted(level_files, key=level_numeric_key):
        state = parse_level(str(level_path.resolve()))
        # The deadlock module currently prints a full map; suppress it here.
        with redirect_stdout(io.StringIO()):
            deadlocks = len(_compute_all_deadlock_positions(state))

        level_name, result, error_msg = run_level(
            level_path,
            algorithm,
            timeout,
            verbose=False,
            heuristic_name="combination",
        )

        labels.append(level_name)
        deadlock_counts.append(deadlocks)

        if result is None:
            expanded_nodes.append(0)
            frontier_nodes.append(0)
            errors.append(f"{level_name}: {error_msg or 'error'}")
            continue

        expanded_nodes.append(int(result.expanded_nodes))
        frontier_nodes.append(int(result.frontier_nodes))
        if error_msg is not None:
            errors.append(f"{level_name}: {error_msg}")

    return labels, expanded_nodes, deadlock_counts, frontier_nodes, errors


def _plot_single_metric(
    labels: list[str],
    values: list[float],
    ylabel: str,
    color: str,
    edgecolor: str,
    integer_yaxis: bool,
    log_yaxis: bool,
    y_min: float | None,
    y_max: float | None,
    title: str,
) -> plt.Figure:
    x = list(range(len(labels)))
    rotate = 35 if labels and max(len(name) for name in labels) > 10 else 0

    fig, ax = plt.subplots(nrows=1, ncols=1, figsize=(12.0, 4.0), dpi=140)
    fig.suptitle(title, fontsize=13, fontweight="600")

    plot_values = values
    if log_yaxis:
        # Log scale cannot display zero/negative values; clamp them to a tiny positive number.
        plot_values = [v if v > 0 else 1e-6 for v in values]

    ax.bar(x, plot_values, color=color, edgecolor=edgecolor, linewidth=0.6)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Level")
    if log_yaxis:
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
    elif integer_yaxis:
        ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=True))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
    else:
        ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=False))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.6g}"))
    ax.grid(axis="y", linestyle="-", linewidth=0.6, alpha=0.5, color="#e8ecf0")
    ax.set_axisbelow(True)
    if y_min is not None or y_max is not None:
        ax.set_ylim(bottom=y_min, top=y_max)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=rotate, ha="right" if rotate else "center")

    ymax = max(values) if values else 0.0
    yoff = ymax * 0.015 if ymax > 0 else 0.02
    for idx, v in enumerate(values):
        label = f"{int(v)}" if integer_yaxis else f"{v:.3g}"
        ax.text(
            idx,
            (plot_values[idx] if log_yaxis else v) + yoff,
            label,
            ha="center",
            va="bottom",
            fontsize=8,
            color="#2b2b2b",
            zorder=5,
        )

    fig.subplots_adjust(left=0.09, right=0.98, top=0.86, bottom=0.2 if rotate == 0 else 0.32)
    return fig


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run all levels in a directory with greedy/astar + deadlock heuristic, "
            "then generate separate images for expanded nodes, deadlocks, "
            "expanded/deadlock, and frontier/(expanded+frontier) per level."
        )
    )
    parser.add_argument(
        "--levels-dir",
        required=True,
        metavar="DIR",
        help="Directory containing .txt Sokoban levels.",
    )
    parser.add_argument(
        "--algorithm",
        required=True,
        choices=("greedy", "astar"),
        help="Search algorithm (only greedy or astar).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SEC",
        help="Per-level timeout in seconds (default: none).",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Optional output base path or directory. If omitted, shows interactive plots. "
            "When provided, four files are written."
        ),
    )
    ns = parser.parse_args()

    levels_dir = resolve_levels_dir(ns.levels_dir)
    level_files = find_level_files(levels_dir)
    print(f"Found {len(level_files)} level(s) in {levels_dir}")
    print(f"Running {ns.algorithm} with heuristic=deadlock")

    labels, expanded, deadlocks, frontier, errors = collect_metrics(
        level_files=level_files,
        algorithm=ns.algorithm,
        timeout=ns.timeout,
    )

    expanded_per_deadlock = [
        (float(expanded_nodes) / deadlock_count) if deadlock_count > 0 else 0.0
        for expanded_nodes, deadlock_count in zip(expanded, deadlocks)
    ]
    frontier_over_total = [
        (float(frontier_nodes) / (expanded_nodes + frontier_nodes))
        if (expanded_nodes + frontier_nodes) > 0
        else 0.0
        for expanded_nodes, frontier_nodes in zip(expanded, frontier)
    ]

    title_base = f"{levels_dir.name} — {ns.algorithm.upper()} + deadlock heuristic"
    fig_expanded = _plot_single_metric(
        labels=labels,
        values=[float(v) for v in expanded],
        ylabel="Expanded nodes",
        color="#4a90d9",
        edgecolor="#2c6cb0",
        integer_yaxis=True,
        log_yaxis=True,
        y_min=None,
        y_max=None,
        title=f"{title_base} — Expanded nodes",
    )
    fig_deadlocks = _plot_single_metric(
        labels=labels,
        values=[float(v) for v in deadlocks],
        ylabel="Deadlock positions",
        color="#e67e22",
        edgecolor="#c45f1a",
        integer_yaxis=True,
        log_yaxis=True,
        y_min=None,
        y_max=None,
        title=f"{title_base} — Deadlock positions",
    )
    fig_ratio = _plot_single_metric(
        labels=labels,
        values=expanded_per_deadlock,
        ylabel="Expanded / deadlock",
        color="#27ae60",
        edgecolor="#1e8449",
        integer_yaxis=False,
        log_yaxis=True,
        y_min=None,
        y_max=None,
        title=f"{title_base} — Expanded / deadlock",
    )
    fig_frontier_ratio = _plot_single_metric(
        labels=labels,
        values=frontier_over_total,
        ylabel="Frontier / (expanded + frontier)",
        color="#8e44ad",
        edgecolor="#6c3483",
        integer_yaxis=False,
        log_yaxis=False,
        y_min=0.0,
        y_max=1.0,
        title=f"{title_base} — Frontier / (expanded + frontier)",
    )

    out_path = resolve_out_path(ns.out)
    if out_path is None:
        plt.show()
    else:
        if out_path.suffix.lower() in IMAGE_SUFFIXES:
            save_fmt = out_path.suffix[1:].lower()
            base = out_path.with_suffix("")
            out_expanded = base.with_name(f"{base.name}__expanded_nodes").with_suffix(out_path.suffix)
            out_deadlocks = base.with_name(f"{base.name}__deadlock_count").with_suffix(out_path.suffix)
            out_ratio = base.with_name(f"{base.name}__expanded_over_deadlock").with_suffix(out_path.suffix)
            out_frontier_ratio = base.with_name(
                f"{base.name}__frontier_over_total"
            ).with_suffix(out_path.suffix)
        else:
            # Fallback, should not happen because resolve_out_path normalizes dirs to base file name.
            save_fmt = "png"
            out_expanded = out_path.parent / f"{out_path.name}__expanded_nodes.png"
            out_deadlocks = out_path.parent / f"{out_path.name}__deadlock_count.png"
            out_ratio = out_path.parent / f"{out_path.name}__expanded_over_deadlock.png"
            out_frontier_ratio = out_path.parent / f"{out_path.name}__frontier_over_total.png"

        for fig, path in (
            (fig_expanded, out_expanded),
            (fig_deadlocks, out_deadlocks),
            (fig_ratio, out_ratio),
            (fig_frontier_ratio, out_frontier_ratio),
        ):
            fig.savefig(
                path,
                dpi=140,
                bbox_inches="tight",
                pad_inches=0.2,
                format="jpeg" if save_fmt == "jpg" else save_fmt,
            )
            print(f"Wrote {path}")

    plt.close(fig_expanded)
    plt.close(fig_deadlocks)
    plt.close(fig_ratio)
    plt.close(fig_frontier_ratio)

    if errors:
        print("\nLevels with issues:")
        for err in errors:
            print(f"  - {err}")


if __name__ == "__main__":
    main()
