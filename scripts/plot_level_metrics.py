"""
Bar charts for search metrics on one or more Sokoban levels (matplotlib).

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
VARIABLE_METRICS = frozenset({"processing_time", "heuristic_time", "heuristic_time_ratio"})
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
    "figure_bg": "#fff5ec",
    "axes_bg": "#fff5ec",
    # Slightly grey plot area when showing SD (like SPSS-style charts).
    "axes_bg_sd": "#e8e8e8",
    "bar_ok": "#4a90d9",
    "bar_ok_edge": "#2c6cb0",
    "bar_bad": "#b8c2cc",
    "bar_bad_edge": "#95a5a6",
    "bar_edge_sd": "#343434",
    "grid": "#e8dcd0",
    "grid_minor": "#d4c8bc",
    "text_title": "#343434",
    "text_axis": "#343434",
    "text_muted": "#6b6560",
    "err_bar": "#e67e22",
    "err_bar_sd": "#343434",
    "legend_frame": "#fff5ec",
    "spine_sd": "#343434",
}

PLOT_RC = {
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Helvetica", "Arial", "sans-serif"],
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "axes.spines.top": True,
    "axes.spines.right": True,
    "axes.edgecolor": "#343434",
    "axes.labelcolor": "#343434",
    "axes.linewidth": 0.8,
    "xtick.color": "#343434",
    "ytick.color": "#343434",
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


def format_value_label(value: float, yaxis: str) -> str:
    if value == 0.0:
        return "0"
    if yaxis in INTEGER_YAXIS_METRICS or yaxis == "memory":
        return str(int(round(value)))
    return f"{value:.2f}"


def yaxis_label(yaxis: str) -> str:
    return {
        "processing_time": "Tiempo de procesamiento (s)",
        "heuristic_time": "Tiempo de evaluación heurística (s)",
        "memory": "Memoria pico (KB)",
        "frontier_nodes": "Nodos frontera",
        "expanded_nodes": "Nodos expandidos",
        "cost": "Costo de solución (longitud del camino)",
        "boxes_displaced": "Empujes de cajas",
        "heuristic_time_ratio": "Tiempo heurística / tiempo total",
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
        "processing_time": "Tiempo total",
        "heuristic_time": "Tiempo heurística",
        "memory": "Memoria (KB)",
        "frontier_nodes": "Nodos frontera",
        "expanded_nodes": "Nodos expandidos",
        "cost": "Costo",
        "boxes_displaced": "Empujes de cajas",
        "heuristic_time_ratio": "t. heurística / total",
    }.get(metric, metric)


def algorithm_legend_label(algorithm: str) -> str:
    return {"astar": "A*", "greedy": "Greedy"}.get(algorithm, algorithm.upper())


def combined_ylabel_for_metrics(metrics: list[str], repeat: int) -> str:
    if TIME_METRICS.issuperset(metrics):
        base = "Tiempo (s)"
    elif all(m in INTEGER_YAXIS_METRICS for m in metrics):
        base = "Valor"
    else:
        base = "Valor"
    if repeat > 1 and any(m in VARIABLE_METRICS for m in metrics):
        base = f"{base} (promedio)"
    return base


def single_metric_ylabel(metric: str, repeat: int) -> str:
    label = yaxis_label(metric)
    if repeat > 1 and metric in VARIABLE_METRICS:
        label = f"{label} (promedio)"
    return label


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
    yaxis: str,
    xlabel: str | None,
    repeat: int,
) -> plt.Figure:
    labels = [r["label"] for r in rows]
    tick_labels = [format_bar_label(l) for l in labels]
    values, colors, annotations, yerrs = _bar_series(rows, repeat)
    yerr_plot = (
        [0.0 if e is None else float(e) for e in yerrs]
        if repeat > 1 and yaxis in VARIABLE_METRICS
        else None
    )
    show_sd = repeat > 1 and yerr_plot is not None

    with plt.rc_context(PLOT_RC):
        fig, ax = plt.subplots(figsize=FIG_SIZE, dpi=FIG_DPI)
        fig.patch.set_facecolor(STYLE["figure_bg"])
        ax.set_facecolor(STYLE["axes_bg"])

        fig.suptitle(
            title,
            fontsize=13,
            fontweight="600",
            color=STYLE["text_title"],
            y=0.97,
        )

        n = len(labels)
        if n == 0:
            ax.text(
                0.5,
                0.5,
                "Sin datos",
                ha="center",
                va="center",
                transform=ax.transAxes,
                color=STYLE["text_axis"],
            )
        else:
            x = range(n)
            bar_width = 0.72 if n <= 8 else max(0.35, 0.9 - 0.06 * n)
            kw: dict = {
                "x": x,
                "height": values,
                "width": bar_width,
                "color": colors,
                "edgecolor": "none",
                "linewidth": 0,
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
            rot = 35
            ha = "right"
            ax.set_xticklabels(tick_labels, rotation=rot, ha=ha)
            if xlabel:
                ax.set_xlabel(xlabel, color=STYLE["text_axis"])

            y_label = yaxis_label(yaxis)
            if show_sd:
                y_label = f"{y_label} (promedio)"
            ax.set_ylabel(y_label, color=STYLE["text_axis"])
            ax.grid(
                axis="y",
                which="major",
                linestyle="-",
                linewidth=0.6,
                alpha=0.55,
                color=STYLE["grid"],
                zorder=0,
            )
            ax.minorticks_on()
            ax.grid(
                axis="y",
                which="minor",
                linestyle=":",
                linewidth=0.4,
                alpha=0.45,
                color=STYLE["grid_minor"],
                zorder=0,
            )
            ax.tick_params(axis="x", which="minor", bottom=False)
            ax.tick_params(axis="both", colors=STYLE["text_axis"])
            ax.set_axisbelow(True)

            tops = [values[i] + (yerr_plot[i] if yerr_plot else 0) for i in range(n)]
            ymax = max(tops) if tops else 1.0

            if yaxis in INTEGER_YAXIS_METRICS:
                ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=True))
                ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
            else:
                ax.yaxis.set_major_locator(MaxNLocator(nbins="auto", integer=False))
                ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.6g}"))

            patches = getattr(bar_container, "patches", None) or []
            for i in range(min(len(patches), n)):
                bar = patches[i]
                ypos = bar.get_height()
                if yerr_plot is not None:
                    ypos += yerr_plot[i]
                off = ymax * 0.02 if ymax > 0 else 0.02
                label_text = annotations[i] if annotations[i] else format_value_label(values[i], yaxis)
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    ypos + off,
                    label_text,
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    color=STYLE["text_axis"],
                    zorder=6,
                    rotation=0,
                )

            for spine in ax.spines.values():
                spine.set_visible(True)
                spine.set_color(STYLE["text_axis"])

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
    return plot_grouped_series(
        series_rows=series_rows,
        series_labels=[metric_legend_label(metric) for metric in metrics],
        value_metrics=metrics,
        title=title,
        xlabel=xlabel,
        ylabel=combined_ylabel_for_metrics(metrics, repeat),
        repeat=repeat,
    )


def plot_grouped_series(
    series_rows: list[list[PlotRow]],
    series_labels: list[str],
    value_metrics: list[str],
    title: str,
    xlabel: str | None,
    ylabel: str,
    repeat: int,
) -> plt.Figure:
    """One figure: grouped bars per category, one series per input row set."""
    if len(series_rows) != len(series_labels):
        raise ValueError("Each grouped series must have a matching legend label.")

    k = len(series_labels)
    n_cat = len(series_rows[0]) if series_rows else 0
    assert all(len(sr) == n_cat for sr in series_rows), "Grouped series must share categories"
    tick_labels = [format_bar_label(series_rows[0][i]["label"]) for i in range(n_cat)]
    any_variable = any(m in VARIABLE_METRICS for m in value_metrics)
    show_sd = repeat > 1 and any_variable

    x = np.arange(n_cat, dtype=float)
    width = 0.8 / max(k, 1)
    fig_w = min(11.0 + n_cat * k * 0.11, 24.0)
    fig_h = FIG_SIZE[1]

    with plt.rc_context(PLOT_RC):
        fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=FIG_DPI)
    fig.patch.set_facecolor(STYLE["figure_bg"])
    ax.set_facecolor(STYLE["axes_bg"])

    fig.suptitle(
        title,
        fontsize=13,
        fontweight="600",
        color=STYLE["text_title"],
        y=0.97,
    )

    if n_cat == 0:
        ax.text(
            0.5,
            0.5,
            "Sin datos",
            ha="center",
            va="center",
            transform=ax.transAxes,
            color=STYLE["text_axis"],
        )
        return fig

    ymax = 0.0
    capsize = max(3.0, ERROR_CAPSIZE - 0.5 * (k - 1))
    label_stack_state: dict[int, list[float]] = {}
    max_label_y = 0.0

    for j, series_label in enumerate(series_labels):
        vals, colors, annotations, yerrs = _bar_series(series_rows[j], repeat)
        plot_colors = [
            SERIES_PALETTE[j % len(SERIES_PALETTE)] if c == STYLE["bar_ok"] else c
            for c in colors
        ]
        metric_is_variable = j < len(value_metrics) and value_metrics[j] in VARIABLE_METRICS
        yerr_plot: list[float] | None = None
        if repeat > 1 and metric_is_variable:
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
            "edgecolor": "none",
            "linewidth": 0,
            "zorder": 2,
            "label": series_label,
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

        series_metric = value_metrics[j] if j < len(value_metrics) else ""
        patches = getattr(bar_container, "patches", None) or []
        for i in range(min(len(patches), len(vals))):
            bar = patches[i]
            ypos = float(bar.get_height())
            if yerr_plot is not None:
                ypos += yerr_plot[i]
            off = ymax * 0.02 if ymax > 0 else 0.02
            label_text = annotations[i] if annotations[i] else format_value_label(vals[i], series_metric)
            needs_stacking = len(label_text) > 3 and bar.get_width() <= 0.45
            same_height_count = 0
            if needs_stacking:
                same_height_count = sum(
                    1
                    for previous_top in label_stack_state.get(i, [])
                    if abs(previous_top - ypos) <= off * 0.5
                )
            label_y = ypos + off * (1.0 + 1.5 * same_height_count)
            label_stack_state.setdefault(i, []).append(ypos)
            max_label_y = max(max_label_y, label_y)
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                label_y,
                label_text,
                ha="center",
                va="bottom",
                fontsize=7,
                color=STYLE["text_axis"],
                zorder=6,
                rotation=0,
            )

    ax.set_xticks(x)
    rot = 35
    ha = "right"
    ax.set_xticklabels(tick_labels, rotation=rot, ha=ha)
    if xlabel:
        ax.set_xlabel(xlabel, color=STYLE["text_axis"])

    ax.set_ylabel(ylabel, color=STYLE["text_axis"])
    _set_grouped_yaxis_formatter(ax, value_metrics)

    ax.grid(
        axis="y",
        which="major",
        linestyle="-",
        linewidth=0.6,
        alpha=0.55,
        color=STYLE["grid"],
        zorder=0,
    )
    ax.minorticks_on()
    ax.grid(
        axis="y",
        which="minor",
        linestyle=":",
        linewidth=0.4,
        alpha=0.45,
        color=STYLE["grid_minor"],
        zorder=0,
    )
    ax.tick_params(axis="x", which="minor", bottom=False)
    ax.tick_params(axis="both", colors=STYLE["text_axis"])
    ax.set_axisbelow(True)
    if max_label_y > 0:
        ax.set_ylim(top=max(ax.get_ylim()[1], max_label_y + off * 2.0))

    legend_handles = [
        mpatches.Patch(
            facecolor=SERIES_PALETTE[j % len(SERIES_PALETTE)],
            edgecolor="none",
            linewidth=0,
            label=series_labels[j],
        )
        for j in range(k)
    ]
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
        labelcolor=STYLE["text_axis"],
    )

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(STYLE["text_axis"])

    bottom_margin = 0.22 if rot else 0.14
    right_margin = 0.72 if k >= 4 else 0.76
    fig.subplots_adjust(left=0.09, right=right_margin, top=0.88, bottom=bottom_margin)

    return fig


def collect_series_rows_algorithm_comparison_mode(
    level_path: Path,
    algorithms: list[str],
    heuristics: list[str],
    timeout: int | None,
    repeat: int,
) -> list[tuple[str, list[RunRow]]]:
    return [
        (
            algo,
            collect_rows_heuristic_mode(level_path, algo, heuristics, timeout, repeat),
        )
        for algo in algorithms
    ]


def _safe_filename_part(s: str) -> str:
    s = re.sub(r"[^\w.\-]+", "_", s, flags=re.UNICODE)
    return s.strip("_") or "out"


def build_heuristics_tag(heuristics_list: list[str] | None) -> str:
    if heuristics_list is not None and len(heuristics_list) < len(HEURISTICS):
        head = "_".join(heuristics_list[:5])
        if len(heuristics_list) > 5:
            head += f"_plus{len(heuristics_list) - 5}"
        return f"subset_{head}"
    return "all_heuristics"


def build_scenario_slug(
    mode: str,
    algorithms: list[str] | None,
    heuristic_fixed: str,
    heuristics_list: list[str] | None,
) -> str:
    if mode == "onlyheuristics":
        algo = (algorithms or [""])[0]
        htag = build_heuristics_tag(heuristics_list)
        raw = f"{algo}_vs_{htag}"
        raw = raw[:180] if len(raw) > 180 else raw
        return _safe_filename_part(raw)
    if mode == "compare_algorithms_by_heuristic":
        alg_tag = "_vs_".join(algorithms or list(HEURISTIC_ONLY_ALGORITHMS))
        raw = f"{alg_tag}_vs_{build_heuristics_tag(heuristics_list)}"
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
    if ns.onlyheuristics and ns.compare_algorithms_by_heuristic:
        raise SystemExit(
            "Choose only one of --onlyheuristics or --compare-algorithms-by-heuristic."
        )

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
    elif ns.compare_algorithms_by_heuristic:
        algs = list(ns.algorithms) if ns.algorithms else list(HEURISTIC_ONLY_ALGORITHMS)
        if not algs:
            raise SystemExit(
                "With --compare-algorithms-by-heuristic, --algorithm must include at least one of: greedy, astar."
            )
        bad = [a for a in algs if a not in HEURISTIC_ONLY_ALGORITHMS]
        if bad:
            invalid = ", ".join(bad)
            raise SystemExit(
                "With --compare-algorithms-by-heuristic, --algorithm must use only greedy and/or astar "
                f"(got: {invalid})."
            )
    elif ns.heuristics is not None:
        raise SystemExit(
            "Use --heuristics only with --onlyheuristics or --compare-algorithms-by-heuristic; "
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


def resolve_level_paths(root: Path, level_raw: str | None, all_levels: bool) -> list[Path]:
    if all_levels:
        levels_dir = root / "microban_levels"
        level_files = sorted(
            levels_dir.glob("level*.txt"),
            key=lambda p: (
                int(re.search(r"(\d+)$", p.stem).group(1))
                if re.search(r"(\d+)$", p.stem)
                else sys.maxsize,
                p.stem,
            ),
        )
        if not level_files:
            raise SystemExit(f"No level files found in {levels_dir}")
        return level_files

    if level_raw is None:
        raise SystemExit("Pass --level PATH or --all-levels.")

    level_path = Path(level_raw)
    if not level_path.is_absolute():
        level_path = (root / level_path).resolve()
    if not level_path.is_file():
        raise SystemExit(f"Level file not found: {level_path}")
    return [level_path]


def resolve_output(
    out_raw: str | None,
    multi_metric: bool,
    multi_level: bool,
) -> OutputPlan:
    if out_raw is None:
        if multi_level:
            raise SystemExit("With --all-levels, pass --out DIR to save files.")
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

    if multi_level:
        raise SystemExit("With --all-levels, --out must be a directory.")
    if multi_metric:
        raise SystemExit("A single output file requires exactly one metric in --yaxis.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    return OutputPlan(interactive=False, save_file=out_path)


def save_figure(fig: plt.Figure, path: Path, fmt: str | None = None) -> None:
    kw: dict = {"dpi": FIG_DPI, "bbox_inches": "tight", "pad_inches": SAVE_PAD_INCHES}
    if fmt:
        kw["format"] = "jpeg" if fmt == "jpg" else fmt
    fig.savefig(path, **kw)


def emit_figure(
    fig: plt.Figure,
    out: OutputPlan,
    level_stem: str,
    scenario: str,
    save_fmt: str,
    *,
    grouped: bool,
    metrics: list[str],
    metric: str | None = None,
) -> Path | None:
    if out.interactive:
        plt.show()
        plt.close(fig)
        return None

    if out.save_file is not None:
        if grouped:
            save_path = out.save_file.parent / default_grouped_basename(
                level_stem, scenario, metrics, save_fmt
            )
            save_figure(fig, save_path, save_fmt)
        else:
            save_path = out.save_file
            save_figure(fig, save_path, save_fmt)
        plt.close(fig)
        return save_path

    if out.batch_dir is None:
        plt.close(fig)
        return None

    if grouped:
        save_path = out.batch_dir / default_grouped_basename(
            level_stem, scenario, metrics, "png"
        )
        save_figure(fig, save_path, "png")
    else:
        if metric is None:
            raise ValueError("metric is required when saving a single-metric figure")
        save_path = out.batch_dir / default_output_basename(
            level_stem, scenario, metric, "png"
        )
        save_figure(fig, save_path, "png")
    plt.close(fig)
    return save_path


def render_level_plots(
    *,
    level_path: Path,
    mode: str,
    algorithms: list[str],
    heuristics_list: list[str] | None,
    heuristic_fixed: str,
    metrics: list[str],
    repeat: int,
    timeout: int | None,
    group_yaxis: bool,
    out: OutputPlan,
    save_fmt: str,
) -> list[Path]:
    scenario = build_scenario_slug(mode, algorithms, heuristic_fixed, heuristics_list)
    xlabel = "Algoritmo"
    title_base = f"{level_path.name} - algoritmos (h fija={heuristic_fixed})"
    written_paths: list[Path] = []

    if mode == "onlyheuristics":
        algo = algorithms[0]
        heur_list = heuristics_list or sorted(HEURISTICS.keys())
        base_rows = collect_rows_heuristic_mode(
            level_path, algo, heur_list, timeout, repeat
        )
        title_base = f"{level_path.name} - {algorithm_legend_label(algo)} vs heurísticas"
        xlabel = "Heurística"
    elif mode == "compare_algorithms_by_heuristic":
        heur_list = heuristics_list or sorted(HEURISTICS.keys())
        series_run_rows = collect_series_rows_algorithm_comparison_mode(
            level_path, algorithms, heur_list, timeout, repeat
        )
        alg_tag = " vs ".join(algorithm_legend_label(algorithm) for algorithm in algorithms)
        title_base = f"{level_path.name} - heurísticas ({alg_tag})"
        xlabel = "Heurística"
    else:
        base_rows = collect_rows_algorithm_mode(
            level_path, algorithms, heuristic_fixed, timeout, repeat
        )

    if repeat > 1:
        title_base = f"{title_base} (n = {repeat})"

    if mode == "compare_algorithms_by_heuristic":
        if group_yaxis:
            series_rows: list[list[PlotRow]] = []
            series_labels: list[str] = []
            value_metrics: list[str] = []
            for metric_name in metrics:
                for algorithm, run_rows in series_run_rows:
                    series_rows.append(attach_values(run_rows, metric_name, repeat))
                    series_labels.append(
                        f"{metric_legend_label(metric_name)} - {algorithm_legend_label(algorithm)}"
                    )
                    value_metrics.append(metric_name)

            fig = plot_grouped_series(
                series_rows=series_rows,
                series_labels=series_labels,
                value_metrics=value_metrics,
                title=title_base,
                xlabel=xlabel,
                ylabel=combined_ylabel_for_metrics(metrics, repeat),
                repeat=repeat,
            )
            save_path = emit_figure(
                fig,
                out,
                level_path.stem,
                scenario,
                save_fmt,
                grouped=True,
                metrics=metrics,
            )
            if save_path is not None:
                written_paths.append(save_path)
            return written_paths

        for metric_name in metrics:
            series_rows = [
                attach_values(run_rows, metric_name, repeat)
                for _algorithm, run_rows in series_run_rows
            ]
            series_labels = [
                algorithm_legend_label(algorithm)
                for algorithm, _run_rows in series_run_rows
            ]
            fig = plot_grouped_series(
                series_rows=series_rows,
                series_labels=series_labels,
                value_metrics=[metric_name] * max(len(series_rows), 1),
                title=title_base,
                xlabel=xlabel,
                ylabel=single_metric_ylabel(metric_name, repeat),
                repeat=repeat,
            )
            save_path = emit_figure(
                fig,
                out,
                level_path.stem,
                scenario,
                save_fmt,
                grouped=False,
                metrics=[metric_name],
                metric=metric_name,
            )
            if save_path is not None:
                written_paths.append(save_path)
        return written_paths

    if group_yaxis:
        series_rows = [attach_values(base_rows, metric_name, repeat) for metric_name in metrics]
        fig = plot_grouped_bars(series_rows, metrics, title_base, xlabel, repeat)
        save_path = emit_figure(
            fig,
            out,
            level_path.stem,
            scenario,
            save_fmt,
            grouped=True,
            metrics=metrics,
        )
        if save_path is not None:
            written_paths.append(save_path)
        return written_paths

    for metric_name in metrics:
        rows = attach_values(base_rows, metric_name, repeat)
        fig = plot_bars(
            rows,
            title_base,
            metric_name,
            xlabel,
            repeat,
        )
        save_path = emit_figure(
            fig,
            out,
            level_path.stem,
            scenario,
            save_fmt,
            grouped=False,
            metrics=[metric_name],
            metric=metric_name,
        )
        if save_path is not None:
            written_paths.append(save_path)

    return written_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bar charts for one Sokoban level or all Microban levels. One image per metric "
        "(default), or grouped bars with --group-yaxis. Optional repeated runs with std.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --level levels/level1.txt --yaxis expanded_nodes
  %(prog)s --level levels/level1.txt --out plots/
  %(prog)s --level levels/level1.txt --runs 5 --out plots/
      (each bar: mean ± sample std over 5 runs)
  %(prog)s --level levels/level1.txt --onlyheuristics --algorithm astar \\
      --group-yaxis --yaxis processing_time heuristic_time -o plots/
  %(prog)s --all-levels --compare-algorithms-by-heuristic -o plots/
""",
    )
    level_group = parser.add_mutually_exclusive_group(required=True)
    level_group.add_argument(
        "--level",
        type=str,
        metavar="PATH",
        help="Level .txt path (e.g. levels/level1.txt)",
    )
    level_group.add_argument(
        "--all-levels",
        action="store_true",
        help="Process every level*.txt under microban_levels/ (requires --out DIR)",
    )
    parser.add_argument(
        "--onlyheuristics",
        action="store_true",
        help="X-axis = heuristics; --algorithm must be astar or greedy (default: compare all algorithms)",
    )
    parser.add_argument(
        "--compare-algorithms-by-heuristic",
        action="store_true",
        help="X-axis = heuristics; compare greedy and/or astar side by side for each heuristic",
    )
    parser.add_argument(
        "--algorithm",
        nargs="*",
        default=None,
        dest="algorithms",
        metavar="NAME",
        help="Algorithms to plot (default: all, or greedy astar with --compare-algorithms-by-heuristic). "
        "With --onlyheuristics: exactly astar or greedy",
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
        help="Heuristics to compare with --onlyheuristics or --compare-algorithms-by-heuristic "
        "(default: all)",
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
    validate_cli(ns)
    if ns.group_yaxis and (not ns.yaxis or len(ns.yaxis) < 2):
        raise SystemExit(
            "--group-yaxis requires explicit --yaxis with at least two metrics "
            "(e.g. --yaxis processing_time heuristic_time)."
        )
    level_paths = resolve_level_paths(root, ns.level, ns.all_levels)
    metrics = resolve_metrics(ns.yaxis)
    multi = len(metrics) > 1 and not ns.group_yaxis
    out = resolve_output(ns.out, multi, len(level_paths) > 1)

    if not out.interactive:
        plt.ioff()

    repeat = ns.runs
    heur_list = list(ns.heuristics) if ns.heuristics is not None else None

    if ns.onlyheuristics:
        mode = "onlyheuristics"
        algorithms = [ns.algorithms[0]]
    elif ns.compare_algorithms_by_heuristic:
        mode = "compare_algorithms_by_heuristic"
        algorithms = (
            list(ns.algorithms)
            if ns.algorithms
            else list(HEURISTIC_ONLY_ALGORITHMS)
        )
    else:
        mode = "algorithm"
        algorithms = list(ns.algorithms) if ns.algorithms else list(ALGORITHMS.keys())
        for algorithm in algorithms:
            if algorithm not in ALGORITHMS:
                raise SystemExit(f"Unknown algorithm: {algorithm}")

    save_fmt = out.save_file.suffix[1:].lower() if out.save_file else "png"
    if out.save_file and out.save_file.suffix.lower() not in IMAGE_SUFFIXES:
        raise SystemExit(
            f"Unsupported image type {out.save_file.suffix!r}; use one of {sorted(IMAGE_SUFFIXES)}"
        )

    written_paths: list[Path] = []
    for level_path in level_paths:
        written_paths.extend(
            render_level_plots(
                level_path=level_path,
                mode=mode,
                algorithms=algorithms,
                heuristics_list=heur_list,
                heuristic_fixed=ns.heuristic,
                metrics=metrics,
                repeat=repeat,
                timeout=ns.timeout,
                group_yaxis=ns.group_yaxis,
                out=out,
                save_fmt=save_fmt,
            )
        )

    if out.save_file is not None and written_paths:
        print(f"Generado: {written_paths[0]}")
    elif out.batch_dir is not None and not out.interactive:
        print(f"Generadas {len(written_paths)} figura(s) en {out.batch_dir}")


if __name__ == "__main__":
    main()
