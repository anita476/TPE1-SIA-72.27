"""
Bar charts for search metrics on a single Sokoban level (matplotlib).

Requires: pip install matplotlib
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from algorithms.algorithms import ALGORITHMS, HEURISTICS
from algorithms.utils import SearchResult
from run_all_levels import run_level

try:
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.ticker import MaxNLocator, StrMethodFormatter
except ImportError as e:
    raise SystemExit(
        "matplotlib is required for this script. Install with: pip install matplotlib"
    ) from e

YAXIS_CHOICES = (
    "processing_time",
    "heuristic_time",
    "memory",
    "frontier_nodes",
    "expanded_nodes",
    "cost",
    "boxes_displaced",
    "heuristic_time_ratio",
)

HEURISTIC_ONLY_ALGORITHMS = frozenset({"astar", "greedy"})
INTEGER_YAXIS_METRICS = frozenset(
    {"expanded_nodes", "frontier_nodes", "cost", "boxes_displaced"}
)
TIME_METRICS = frozenset({"processing_time", "heuristic_time"})

# Distinct fill colors per metric series (grouped bar mode).
SERIES_PALETTE = [
    "#4a90d9",
    "#27ae60",
    "#e67e22",
    "#9b59b6",
    "#1abc9c",
    "#c0392b",
    "#34495e",
    "#f39c12",
]
SERIES_EDGE_NON_SD = [
    "#2c6cb0",
    "#1e8449",
    "#c45f1a",
    "#7d3c98",
    "#148f82",
    "#922b21",
    "#2c3e50",
    "#c08a0f",
]
IMAGE_SUFFIXES = frozenset({".png", ".pdf", ".svg", ".jpg", ".jpeg", ".webp"})

FIG_DPI = 144
FIG_SIZE = (11.0, 6.2)
SAVE_PAD_INCHES = 0.2
# Classic bar + SD style (symmetric caps top & bottom, dark lines).
ERROR_CAPSIZE = 8.0
ERROR_LINEWIDTH = 1.15
ERROR_CAPTHICK = 1.15

STYLE = {
    "figure_bg": "#ffffff",
    "axes_bg": "#ffffff",
    # Slightly grey plot area when showing SD (like SPSS-style charts).
    "axes_bg_sd": "#e8e8e8",
    "bar_ok": "#4a90d9",
    "bar_ok_edge": "#2c6cb0",
    "bar_bad": "#b8c2cc",
    "bar_bad_edge": "#95a5a6",
    "bar_edge_sd": "#000000",
    "grid": "#e8ecf0",
    "text_title": "#1e2d3d",
    "text_axis": "#5b6b7a",
    "text_muted": "#8b9bab",
    "err_bar": "#e67e22",
    "err_bar_sd": "#000000",
    "legend_frame": "#ffffff",
    "spine_sd": "#000000",
}

PLOT_RC = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial", "sans-serif"],
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#d0d8e0",
    "axes.linewidth": 0.8,
}


class RunRow(TypedDict):
    label: str
    runs: list[tuple[SearchResult | None, str | None]]


class PlotRow(TypedDict, total=False):
    label: str
    value: float | None
    yerr: float | None
    status: str


def metric_value(result: SearchResult | None, yaxis: str) -> float | None:
    if result is None:
        return None
    if yaxis == "cost":
        return float(result.cost) if result.success else None
    if yaxis == "boxes_displaced":
        return float(result.boxes_displaced) if result.success else None
    if yaxis == "heuristic_time_ratio":
        if result.processing_time and result.processing_time > 0:
            return result.heuristic_time / result.processing_time
        return None
    attr = {
        "processing_time": "processing_time",
        "heuristic_time": "heuristic_time",
        "memory": "memory_kb",
        "frontier_nodes": "frontier_nodes",
        "expanded_nodes": "expanded_nodes",
    }.get(yaxis)
    if attr is None:
        return None
    v = getattr(result, attr)
    return float(v) if attr != "memory_kb" else v


def yaxis_label(yaxis: str) -> str:
    return {
        "processing_time": "Processing time (s)",
        "heuristic_time": "Heuristic evaluation time (s)",
        "memory": "Peak memory (KB)",
        "frontier_nodes": "Frontier nodes",
        "expanded_nodes": "Expanded nodes",
        "cost": "Solution cost (path length)",
        "boxes_displaced": "Box pushes",
        "heuristic_time_ratio": "Heuristic time / total time",
    }.get(yaxis, yaxis)


# Shorter X tick labels (internal keys stay full names in HEURISTICS).
HEURISTIC_LABEL_DISPLAY = {
    "basic_hungarian_plus_player_distance": "basic_hungarian",
    "improved_hungarian_plus_player_distance": "improved_hungarian",
}


def format_bar_label(label: str) -> str:
    return HEURISTIC_LABEL_DISPLAY.get(label, label)


def metric_legend_label(metric: str) -> str:
    return {
        "processing_time": "Total time",
        "heuristic_time": "Heuristic time",
        "memory": "Memory (KB)",
        "frontier_nodes": "Frontier nodes",
        "expanded_nodes": "Expanded nodes",
        "cost": "Cost",
        "boxes_displaced": "Box pushes",
        "heuristic_time_ratio": "h-time / total",
    }.get(metric, metric)


def combined_ylabel_for_metrics(metrics: list[str], repeat: int) -> str:
    if TIME_METRICS.issuperset(metrics):
        base = "Time (s)"
    elif all(m in INTEGER_YAXIS_METRICS for m in metrics):
        base = "Value"
    else:
        base = "Value"
    if repeat > 1:
        base = f"{base} (mean)"
    return base


def _set_grouped_yaxis_formatter(ax: plt.Axes, metrics: list[str]) -> None:
    all_int = all(m in INTEGER_YAXIS_METRICS for m in metrics)
    if all_int:
        ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=True))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
    else:
        ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=False))
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.6g}"))


def row_status(result: SearchResult | None, error_msg: str | None) -> str:
    if error_msg == "Timeout":
        return "timeout"
    if result is None:
        return "error"
    if not result.success:
        return "nosolution"
    return "ok"


def aggregate_status(runs: list[tuple[SearchResult | None, str | None]]) -> str:
    errs = [e for _, e in runs]
    if errs and all(e == "Timeout" for e in errs):
        return "timeout"
    results = [r for r, _ in runs]
    if all(r is None for r in results):
        return "error"
    non_null = [r for r in results if r is not None]
    if non_null and all(not r.success for r in non_null):
        return "nosolution"
    return "ok"


def mean_and_std(samples: list[float], repeats: int) -> tuple[float, float | None]:
    """Sample mean and sample std; std is None when repeats==1 or <2 usable samples."""
    if not samples:
        return 0.0, None
    m = mean(samples)
    if repeats <= 1 or len(samples) < 2:
        return m, None
    return m, stdev(samples)


def collect_rows_algorithm_mode(
    level_path: Path,
    algorithms: list[str],
    heuristic_name: str,
    timeout: int | None,
    repeat: int,
) -> list[RunRow]:
    rows: list[RunRow] = []
    for algo in algorithms:
        runs: list[tuple[SearchResult | None, str | None]] = []
        for _ in range(repeat):
            _, result, err = run_level(
                level_path, algo, timeout, verbose=False, heuristic_name=heuristic_name
            )
            runs.append((result, err))
        rows.append({"label": algo, "runs": runs})
    return rows


def collect_rows_heuristic_mode(
    level_path: Path,
    algorithm: str,
    heuristics: list[str],
    timeout: int | None,
    repeat: int,
) -> list[RunRow]:
    rows: list[RunRow] = []
    for h in heuristics:
        runs: list[tuple[SearchResult | None, str | None]] = []
        for _ in range(repeat):
            _, result, err = run_level(
                level_path, algorithm, timeout, verbose=False, heuristic_name=h
            )
            runs.append((result, err))
        rows.append({"label": h, "runs": runs})
    return rows


def attach_values(rows: list[RunRow], yaxis: str, repeat: int) -> list[PlotRow]:
    out: list[PlotRow] = []
    for r in rows:
        runs = r["runs"]
        samples: list[float] = []
        for result, _err in runs:
            if result is None:
                continue
            v = metric_value(result, yaxis)
            if v is not None:
                samples.append(float(v))

        st = aggregate_status(runs)
        if repeat == 1:
            result, err = runs[0]
            st = row_status(result, err)
            v_one = metric_value(result, yaxis) if result else None
            if st == "timeout" or st == "error":
                out.append(
                    {"label": r["label"], "value": 0.0, "yerr": None, "status": st}
                )
            elif st == "nosolution":
                if v_one is not None:
                    out.append(
                        {
                            "label": r["label"],
                            "value": float(v_one),
                            "yerr": None,
                            "status": st,
                        }
                    )
                else:
                    out.append(
                        {"label": r["label"], "value": 0.0, "yerr": None, "status": st}
                    )
            elif v_one is None:
                out.append(
                    {"label": r["label"], "value": 0.0, "yerr": None, "status": st}
                )
            else:
                out.append(
                    {
                        "label": r["label"],
                        "value": float(v_one),
                        "yerr": None,
                        "status": "ok",
                    }
                )
            continue

        if not samples:
            out.append({"label": r["label"], "value": 0.0, "yerr": None, "status": st})
        else:
            m, sd = mean_and_std(samples, repeat)
            out.append(
                {
                    "label": r["label"],
                    "value": m,
                    "yerr": sd,
                    "status": "ok",
                }
            )
    return out


def _bar_series(
    rows: list[PlotRow], repeat: int
) -> tuple[list[float], list[str], list[str], list[float | None]]:
    values: list[float] = []
    colors: list[str] = []
    annotations: list[str] = []
    yerrs: list[float | None] = []
    for r in rows:
        st = r["status"]
        v = r.get("value")
        yerr = r.get("yerr")
        if st == "timeout" or st == "error":
            values.append(0.0)
            colors.append(STYLE["bar_bad"])
            annotations.append("⏱" if st == "timeout" else "✗")
            yerrs.append(None)
        elif st == "nosolution":
            if v is not None:
                values.append(float(v))
                colors.append(STYLE["bar_bad"])
                annotations.append("✗")
            else:
                values.append(0.0)
                colors.append(STYLE["bar_bad"])
                annotations.append("✗")
            yerrs.append(yerr if repeat > 1 else None)
        elif v is None:
            values.append(0.0)
            colors.append(STYLE["bar_bad"])
            annotations.append("–")
            yerrs.append(None)
        else:
            values.append(float(v))
            colors.append(STYLE["bar_ok"])
            annotations.append("")
            yerrs.append(yerr if repeat > 1 else None)
    return values, colors, annotations, yerrs


def plot_bars(
    rows: list[PlotRow],
    title: str,
    subtitle: str | None,
    yaxis: str,
    xlabel: str | None,
    repeat: int,
) -> plt.Figure:
    labels = [r["label"] for r in rows]
    tick_labels = [format_bar_label(l) for l in labels]
    values, colors, annotations, yerrs = _bar_series(rows, repeat)
    yerr_plot = (
        [0.0 if e is None else float(e) for e in yerrs] if repeat > 1 else None
    )
    edgecolors = (
        [STYLE["bar_edge_sd"]] * len(colors)
        if repeat > 1
        else [
            STYLE["bar_ok_edge"] if c == STYLE["bar_ok"] else STYLE["bar_bad_edge"]
            for c in colors
        ]
    )

    show_sd = repeat > 1 and yerr_plot is not None

    with plt.rc_context(PLOT_RC):
        fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=FIG_DPI)
        fig.patch.set_facecolor(STYLE["figure_bg"])
        ax.set_facecolor(STYLE["axes_bg_sd"] if show_sd else STYLE["axes_bg"])

        fig.suptitle(
            title,
            fontsize=13,
            fontweight="600",
            color=STYLE["text_title"],
            y=0.97,
        )
        if subtitle:
            fig.text(
                0.5,
                0.918,
                subtitle,
                ha="center",
                fontsize=10,
                color=STYLE["text_axis"],
                transform=fig.transFigure,
            )

        n = len(labels)
        if n == 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        else:
            x = range(n)
            bar_width = 0.72 if n <= 8 else max(0.35, 0.9 - 0.06 * n)
            kw: dict = {
                "x": x,
                "height": values,
                "width": bar_width,
                "color": colors,
                "edgecolor": edgecolors,
                "linewidth": 0.9 if repeat > 1 else 0.55,
                "zorder": 2,
            }
            if yerr_plot is not None:
                kw["yerr"] = yerr_plot
                kw["capsize"] = ERROR_CAPSIZE
                kw["error_kw"] = {
                    "elinewidth": ERROR_LINEWIDTH,
                    "capthick": ERROR_CAPTHICK,
                    "ecolor": STYLE["err_bar_sd"],
                    "color": STYLE["err_bar_sd"],
                    "zorder": 5,
                    "alpha": 1.0,
                }
            bar_container = ax.bar(**kw)

            ax.set_xticks(list(x))
            rot = 35 if tick_labels and max(len(str(l)) for l in tick_labels) > 12 else 0
            ha = "right" if rot else "center"
            ax.set_xticklabels(tick_labels, rotation=rot, ha=ha)
            if xlabel:
                ax.set_xlabel(xlabel, color=STYLE["text_axis"])

            y_label = yaxis_label(yaxis)
            if show_sd:
                y_label = f"{y_label} (mean)"
            ax.set_ylabel(y_label, color=STYLE["text_axis"])
            if show_sd:
                ax.grid(False)
            else:
                ax.grid(
                    axis="y",
                    linestyle="-",
                    linewidth=0.6,
                    alpha=0.55,
                    color=STYLE["grid"],
                    zorder=0,
                )
                ax.set_axisbelow(True)

            leg_ok_edge = STYLE["bar_edge_sd"] if show_sd else STYLE["bar_ok_edge"]
            leg_bad_edge = STYLE["bar_edge_sd"] if show_sd else STYLE["bar_bad_edge"]
            legend_patches = [
                mpatches.Patch(
                    facecolor=STYLE["bar_ok"],
                    edgecolor=leg_ok_edge,
                    linewidth=0.85 if show_sd else 0.6,
                    label="Measured",
                ),
                mpatches.Patch(
                    facecolor=STYLE["bar_bad"],
                    edgecolor=leg_bad_edge,
                    linewidth=0.85 if show_sd else 0.6,
                    label="Missing / issue",
                ),
            ]
            ax.legend(
                handles=legend_patches,
                loc="upper left",
                bbox_to_anchor=(1.02, 1.0),
                bbox_transform=ax.transAxes,
                borderaxespad=0.0,
                frameon=True,
                facecolor=STYLE["legend_frame"],
                edgecolor=STYLE["grid"],
                framealpha=0.98,
                fontsize=8,
            )

            tops = [values[i] + (yerr_plot[i] if yerr_plot else 0) for i in range(n)]
            ymax = max(tops) if tops else 1.0

            if yaxis in INTEGER_YAXIS_METRICS:
                ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=True))
                ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
            else:
                ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=False))
                ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.6g}"))

            patches = getattr(bar_container, "patches", None) or []
            for i, ann in enumerate(annotations):
                if ann and i < len(patches):
                    bar = patches[i]
                    ypos = bar.get_height()
                    if yerr_plot is not None:
                        ypos += yerr_plot[i]
                    off = ymax * 0.02 if ymax > 0 else 0.02
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        ypos + off,
                        ann,
                        ha="center",
                        va="bottom",
                        fontsize=10,
                        color=STYLE["text_muted"],
                        zorder=6,
                    )

            if show_sd:
                for spine in ax.spines.values():
                    spine.set_visible(True)
                    spine.set_color(STYLE["spine_sd"])
                    spine.set_linewidth(0.9)
                ax.tick_params(axis="both", colors=STYLE["spine_sd"], width=0.8, length=4)
            else:
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)

            bottom_margin = 0.22 if rot else 0.14
            fig.subplots_adjust(left=0.09, right=0.76, top=0.88, bottom=bottom_margin)

        return fig


def plot_grouped_bars(
    series_rows: list[list[PlotRow]],
    metrics: list[str],
    title: str,
    xlabel: str | None,
    repeat: int,
) -> plt.Figure:
    """One figure: grouped bars per category, one series per metric (same Y scale)."""
    k = len(metrics)
    n_cat = len(series_rows[0])
    assert all(len(sr) == n_cat for sr in series_rows), "Metrics must share the same categories"
    tick_labels = [format_bar_label(series_rows[0][i]["label"]) for i in range(n_cat)]
    show_sd = repeat > 1

    x = np.arange(n_cat, dtype=float)
    width = 0.8 / k
    fig_w = min(11.0 + n_cat * k * 0.11, 24.0)
    fig_h = FIG_SIZE[1]

    with plt.rc_context(PLOT_RC):
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=FIG_DPI)
    fig.patch.set_facecolor(STYLE["figure_bg"])
    ax.set_facecolor(STYLE["axes_bg_sd"] if show_sd else STYLE["axes_bg"])

    fig.suptitle(
        title,
        fontsize=13,
        fontweight="600",
        color=STYLE["text_title"],
        y=0.97,
    )

    if n_cat == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return fig

    ymax = 0.0
    capsize = max(3.0, ERROR_CAPSIZE - 0.5 * (k - 1))

    for j, metric in enumerate(metrics):
        vals, colors, annotations, yerrs = _bar_series(series_rows[j], repeat)
        plot_colors = [
            SERIES_PALETTE[j % len(SERIES_PALETTE)] if c == STYLE["bar_ok"] else c
            for c in colors
        ]
        edges: list[str] = []
        for c in colors:
            if show_sd:
                edges.append(STYLE["bar_edge_sd"])
            elif c == STYLE["bar_ok"]:
                edges.append(SERIES_EDGE_NON_SD[j % len(SERIES_EDGE_NON_SD)])
            else:
                edges.append(STYLE["bar_bad_edge"])

        yerr_plot: list[float] | None = None
        if repeat > 1:
            yerr_plot = [0.0 if e is None else float(e) for e in yerrs]

        for i, v in enumerate(vals):
            ye = yerr_plot[i] if yerr_plot is not None else 0.0
            ymax = max(ymax, float(v) + float(ye))

        offset = width * (j - (k - 1) / 2)
        kw: dict = {
            "x": x + offset,
            "height": vals,
            "width": width,
            "color": plot_colors,
            "edgecolor": edges,
            "linewidth": 0.9 if show_sd else 0.55,
            "zorder": 2,
            "label": metric_legend_label(metric),
        }
        if yerr_plot is not None:
            kw["yerr"] = yerr_plot
            kw["capsize"] = capsize
            kw["error_kw"] = {
                "elinewidth": ERROR_LINEWIDTH,
                "capthick": ERROR_CAPTHICK,
                "ecolor": STYLE["err_bar_sd"],
                "color": STYLE["err_bar_sd"],
                "zorder": 5,
                "alpha": 1.0,
            }
        bar_container = ax.bar(**kw)

        patches = getattr(bar_container, "patches", None) or []
        for i, ann in enumerate(annotations):
            if ann and i < len(patches):
                bar = patches[i]
                ypos = float(bar.get_height())
                if yerr_plot is not None:
                    ypos += yerr_plot[i]
                off = ymax * 0.02 if ymax > 0 else 0.02
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    ypos + off,
                    ann,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=STYLE["text_muted"],
                    zorder=6,
                )

    ax.set_xticks(x)
    rot = 35 if tick_labels and max(len(str(t)) for t in tick_labels) > 12 else 0
    ha = "right" if rot else "center"
    ax.set_xticklabels(tick_labels, rotation=rot, ha=ha)
    if xlabel:
        ax.set_xlabel(xlabel, color=STYLE["text_axis"])

    ax.set_ylabel(
        combined_ylabel_for_metrics(metrics, repeat),
        color=STYLE["text_axis"],
    )
    _set_grouped_yaxis_formatter(ax, metrics)

    if show_sd:
        ax.grid(False)
    else:
        ax.grid(
            axis="y",
            linestyle="-",
            linewidth=0.6,
            alpha=0.55,
            color=STYLE["grid"],
            zorder=0,
        )
        ax.set_axisbelow(True)

    leg_edges = [
        STYLE["bar_edge_sd"] if show_sd else SERIES_EDGE_NON_SD[j % len(SERIES_EDGE_NON_SD)]
        for j in range(k)
    ]
    legend_handles = [
        mpatches.Patch(
            facecolor=SERIES_PALETTE[j % len(SERIES_PALETTE)],
            edgecolor=leg_edges[j],
            linewidth=0.85 if show_sd else 0.55,
            label=metric_legend_label(metrics[j]),
        )
        for j in range(k)
    ]
    legend_handles.append(
        mpatches.Patch(
            facecolor=STYLE["bar_bad"],
            edgecolor=STYLE["bar_bad_edge"],
            linewidth=0.85 if show_sd else 0.6,
            label="Missing / issue",
        )
    )
    ncol = 2 if k >= 4 else 1
    ax.legend(
        handles=legend_handles,
        loc="upper left",
        bbox_to_anchor=(1.02, 1.0),
        bbox_transform=ax.transAxes,
        borderaxespad=0.0,
        frameon=True,
        facecolor=STYLE["legend_frame"],
        edgecolor=STYLE["grid"],
        framealpha=0.98,
        fontsize=8,
        ncol=ncol,
    )

    if show_sd:
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(STYLE["spine_sd"])
            spine.set_linewidth(0.9)
        ax.tick_params(axis="both", colors=STYLE["spine_sd"], width=0.8, length=4)
    else:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    bottom_margin = 0.22 if rot else 0.14
    fig.subplots_adjust(left=0.09, right=0.72 if k >= 4 else 0.76, top=0.88, bottom=bottom_margin)

    return fig


def _safe_filename_part(s: str) -> str:
    s = re.sub(r"[^\w.\-]+", "_", s, flags=re.UNICODE)
    return s.strip("_") or "out"


def build_scenario_slug(
    onlyheuristics: bool,
    algorithms: list[str] | None,
    heuristic_fixed: str,
    heuristics_list: list[str] | None,
) -> str:
    if onlyheuristics:
        algo = (algorithms or [""])[0]
        if heuristics_list is not None and len(heuristics_list) < len(HEURISTICS):
            head = "_".join(heuristics_list[:5])
            if len(heuristics_list) > 5:
                head += f"_plus{len(heuristics_list) - 5}"
            htag = f"subset_{head}"
        else:
            htag = "all_heuristics"
        raw = f"{algo}_vs_{htag}"
        raw = raw[:180] if len(raw) > 180 else raw
        return _safe_filename_part(raw)
    h = _safe_filename_part(heuristic_fixed)
    return _safe_filename_part(f"algorithms_h_{h}")


def default_output_basename(
    level_stem: str,
    scenario_slug: str,
    metric: str,
    fmt: str,
) -> str:
    ext = fmt.lstrip(".")
    return f"{_safe_filename_part(level_stem)}__{scenario_slug}__{metric}.{ext}"


def default_grouped_basename(
    level_stem: str,
    scenario_slug: str,
    metrics: list[str],
    fmt: str,
) -> str:
    ext = fmt.lstrip(".")
    tag = "_".join(_safe_filename_part(m) for m in metrics[:8])
    if len(metrics) > 8:
        tag += f"_plus{len(metrics) - 8}"
    return f"{_safe_filename_part(level_stem)}__{scenario_slug}__grouped_{tag}.{ext}"


def validate_cli(ns: argparse.Namespace) -> None:
    if ns.onlyheuristics:
        algs = ns.algorithms or []
        if len(algs) != 1:
            raise SystemExit(
                "With --onlyheuristics, --algorithm must be exactly one of: astar, greedy."
            )
        if algs[0] not in HEURISTIC_ONLY_ALGORITHMS:
            raise SystemExit(
                f"With --onlyheuristics, --algorithm must be astar or greedy (got: {algs[0]})."
            )
    elif ns.heuristics is not None:
        raise SystemExit(
            "Use --heuristics only with --onlyheuristics; "
            "in algorithm mode use --heuristic for greedy/astar."
        )


def out_is_directory(path: Path) -> bool:
    if path.exists():
        return path.is_dir()
    return path.suffix.lower() not in IMAGE_SUFFIXES


def resolve_metrics(yaxis_arg: list[str] | None) -> list[str]:
    if yaxis_arg is None or len(yaxis_arg) == 0:
        return list(YAXIS_CHOICES)
    return list(yaxis_arg)


@dataclass(frozen=True)
class OutputPlan:
    interactive: bool
    batch_dir: Path | None = None
    save_file: Path | None = None


def resolve_output(out_raw: str | None, multi_metric: bool) -> OutputPlan:
    if out_raw is None:
        if multi_metric:
            raise SystemExit(
                "With multiple metrics (default: all), pass --out DIR to save files, "
                "or set --yaxis to a single metric for an interactive plot."
            )
        return OutputPlan(interactive=True)

    out_path = Path(out_raw)
    if not out_path.is_absolute():
        out_path = (Path.cwd() / out_path).resolve()

    if out_is_directory(out_path):
        out_path.mkdir(parents=True, exist_ok=True)
        return OutputPlan(interactive=False, batch_dir=out_path)

    if multi_metric:
        raise SystemExit("A single output file requires exactly one metric in --yaxis.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return OutputPlan(interactive=False, save_file=out_path)


def save_figure(fig: plt.Figure, path: Path, fmt: str | None = None) -> None:
    kw: dict = {"dpi": FIG_DPI, "bbox_inches": "tight", "pad_inches": SAVE_PAD_INCHES}
    if fmt:
        kw["format"] = "jpeg" if fmt == "jpg" else fmt
    fig.savefig(path, **kw)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bar charts for one Sokoban level. One image per metric (default), or grouped "
        "bars with --group-yaxis. Optional repeated runs with std.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --level levels/level1.txt --yaxis expanded_nodes
  %(prog)s --level levels/level1.txt --out plots/
  %(prog)s --level levels/level1.txt --runs 5 --out plots/
      (each bar: mean ± sample std over 5 runs)
  %(prog)s --level levels/level1.txt --onlyheuristics --algorithm astar \\
      --group-yaxis --yaxis processing_time heuristic_time -o plots/
""",
    )
    parser.add_argument(
        "--level",
        type=str,
        required=True,
        metavar="PATH",
        help="Level .txt path (e.g. levels/level1.txt)",
    )
    parser.add_argument(
        "--onlyheuristics",
        action="store_true",
        help="X-axis = heuristics; --algorithm must be astar or greedy (default: compare all algorithms)",
    )
    parser.add_argument(
        "--algorithm",
        nargs="*",
        default=None,
        dest="algorithms",
        metavar="NAME",
        help="Algorithms to plot (default: all). With --onlyheuristics: exactly astar or greedy",
    )
    parser.add_argument(
        "--heuristic",
        type=str,
        default="emm",
        choices=sorted(HEURISTICS.keys()),
        help="Fixed heuristic for greedy/astar in algorithm mode (default: %(default)s)",
    )
    parser.add_argument(
        "--heuristics",
        nargs="+",
        default=None,
        metavar="H",
        choices=sorted(HEURISTICS.keys()),
        help="Heuristics to compare with --onlyheuristics (default: all)",
    )
    parser.add_argument(
        "--yaxis",
        nargs="*",
        default=None,
        metavar="METRIC",
        choices=YAXIS_CHOICES,
        help="Metrics to plot (default: all). One file per metric when saving to a directory",
    )
    parser.add_argument(
        "--group-yaxis",
        action="store_true",
        help="Plot all metrics in --yaxis as grouped bars in one figure (requires explicit "
        "--yaxis with 2+ metrics; same Y scale — use comparable quantities, e.g. two times)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        metavar="SEC",
        help="Per-run time limit in seconds (default: none)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        metavar="N",
        help="Repeat each search N times per bar; show mean ± std when N>1 (default: 1)",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=str,
        default=None,
        metavar="PATH",
        help="Output: .png/.pdf file (single metric only) or directory (auto-named files). "
        "With --group-yaxis the file basename is ignored: auto-named file in that directory.",
    )
    ns = parser.parse_args()

    if ns.runs < 1:
        raise SystemExit("--runs must be >= 1")

    root = Path(__file__).resolve().parent.parent
    level_path = Path(ns.level)
    if not level_path.is_absolute():
        level_path = (root / level_path).resolve()
    if not level_path.is_file():
        raise SystemExit(f"Level file not found: {level_path}")

    validate_cli(ns)
    if ns.group_yaxis and (not ns.yaxis or len(ns.yaxis) < 2):
        raise SystemExit(
            "--group-yaxis requires explicit --yaxis with at least two metrics "
            "(e.g. --yaxis processing_time heuristic_time)."
        )
    metrics = resolve_metrics(ns.yaxis)
    multi = len(metrics) > 1 and not ns.group_yaxis
    out = resolve_output(ns.out, multi)

    if not out.interactive:
        plt.ioff()

    repeat = ns.runs

    if ns.onlyheuristics:
        algo = ns.algorithms[0]
        heur_list = (
            list(ns.heuristics) if ns.heuristics is not None else sorted(HEURISTICS.keys())
        )
        base_rows = collect_rows_heuristic_mode(
            level_path, algo, heur_list, ns.timeout, repeat
        )
        scenario = build_scenario_slug(True, ns.algorithms, ns.heuristic, ns.heuristics)
        title_base = f"{level_path.name} — {algo.upper()} vs heuristics"
        if repeat > 1:
            title_base = f"{title_base} (n = {repeat})"
        xlabel = "Heuristic"
    else:
        algs = list(ns.algorithms) if ns.algorithms else list(ALGORITHMS.keys())
        for a in algs:
            if a not in ALGORITHMS:
                raise SystemExit(f"Unknown algorithm: {a}")
        base_rows = collect_rows_algorithm_mode(
            level_path, algs, ns.heuristic, ns.timeout, repeat
        )
        scenario = build_scenario_slug(False, ns.algorithms, ns.heuristic, None)
        title_base = f"{level_path.name} — algorithms (fixed h={ns.heuristic})"
        if repeat > 1:
            title_base = f"{title_base} (n = {repeat})"
        xlabel = "Algorithm"

    save_fmt = out.save_file.suffix[1:].lower() if out.save_file else "png"
    if out.save_file and out.save_file.suffix.lower() not in IMAGE_SUFFIXES:
        raise SystemExit(
            f"Unsupported image type {out.save_file.suffix!r}; use one of {sorted(IMAGE_SUFFIXES)}"
        )

    if ns.group_yaxis:
        series_rows = [attach_values(base_rows, m, repeat) for m in metrics]
        fig = plot_grouped_bars(series_rows, metrics, title_base, xlabel, repeat)
        if out.interactive:
            plt.show()
            plt.close(fig)
        elif out.save_file is not None:
            auto_name = default_grouped_basename(
                level_path.stem, scenario, metrics, save_fmt
            )
            save_path = out.save_file.parent / auto_name
            save_figure(fig, save_path, save_fmt)
            print(f"Wrote {save_path}")
            plt.close(fig)
        elif out.batch_dir is not None:
            fname = default_grouped_basename(level_path.stem, scenario, metrics, "png")
            save_path = out.batch_dir / fname
            save_figure(fig, save_path, "png")
            print(f"Wrote {save_path}")
            plt.close(fig)
    else:
        for yaxis in metrics:
            rows = attach_values(base_rows, yaxis, repeat)
            subtitle = yaxis_label(yaxis)
            fig = plot_bars(rows, title_base, subtitle, yaxis, xlabel, repeat)

            if out.interactive:
                plt.show()
                plt.close(fig)
            elif out.save_file is not None:
                save_figure(fig, out.save_file, save_fmt)
                plt.close(fig)
            elif out.batch_dir is not None:
                fname = default_output_basename(level_path.stem, scenario, yaxis, "png")
                save_figure(fig, out.batch_dir / fname, "png")
                plt.close(fig)

    if out.batch_dir is not None and not out.interactive and not ns.group_yaxis:
        print(f"Wrote {len(metrics)} figure(s) to {out.batch_dir}")


if __name__ == "__main__":
    main()
