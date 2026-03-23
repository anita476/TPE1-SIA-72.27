# TPE1-SIA-72.27

## Build

No compilation required. Python 3.10+ with standard library only.

Optional: for bar charts (`scripts/plot_level_metrics.py`), install matplotlib:

```bash
pip install -r requirements.txt
```

## Run

From the project root:

```bash
python scripts/main.py --level levels/level1.txt --algorithm bfs
python scripts/run_all_levels.py --algorithm astar --heuristic emm
python scripts/compare_algorithms.py
python scripts/compare_heuristics.py --heuristics emm mm manhattan
python scripts/plot_level_metrics.py --level levels/level1.txt --yaxis expanded_nodes
python scripts/plot_level_metrics.py --level levels/level1.txt -o plot.png --yaxis expanded_nodes
python scripts/plot_level_metrics.py --level levels/level1.txt -o plots/
python scripts/plot_level_metrics.py --level levels/level1.txt --onlyheuristics --algorithm astar -o plots/
```

- **No `-o`**, **one** metric in `--yaxis`: opens an interactive window.
- **No `-o`**, **default metrics** (all) or **several** metrics: not allowed — pass **`-o DIR`** to save one PNG per metric (auto filenames).
- **`-o file.png`**: exactly **one** metric in `--yaxis`.
- **`-o directory/`**: any number of metrics (default: all); PNGs use names like `level1__astar_vs_all_heuristics__expanded_nodes.png`.

### main.py — Solve a single level

| Argument | Default | Description |
|---|---|---|
| `--level` | `levels/level1.txt` | Path to level file |
| `--algorithm` | `dfs` | `bfs`, `dfs`, `iddfs`, `greedy`, `astar` |
| `--heuristic` | `emm` | `emm`, `manhattan` — only used by `greedy` and `astar` |

### run_all_levels.py — Run all levels with one algorithm

| Argument | Default | Description |
|---|---|---|
| `--algorithm` | `bfs` | `bfs`, `dfs`, `iddfs`, `greedy`, `astar` |
| `--heuristic` | `emm` | `emm`, `manhattan` — only used by `greedy` and `astar` |
| `--timeout` | `60` | Seconds per level |
| `--verbose` | — | Show level state and solution path |

### compare_algorithms.py — Compare algorithms on all levels

| Argument | Default | Description |
|---|---|---|
| `--algorithms` | all | Space-separated list: `bfs dfs iddfs greedy astar` |
| `--heuristic` | `emm` | `emm`, `manhattan` — only used by `greedy` and `astar` |
| `--timeout` | `60` | Seconds per level per algorithm |

### compare_heuristics.py — Compare heuristics (A*) on all levels

| Argument | Default | Description |
|---|---|---|
| `--heuristics` | all | Space-separated list: `emm mm manhattan push_distance combination deadlock basic_hungarian_plus_player_distance improved_hungarian_plus_player_distance` |
| `--timeout` | `60` | Seconds per level per heuristic |

### plot_level_metrics.py — Bar charts for one level (requires matplotlib)

| Argument | Default | Description |
|---|---|---|
| `--level` | (required) | Path to `.txt` level |
| `--onlyheuristics` | off | X-axis = heuristics; `--algorithm` must be `astar` or `greedy` |
| `--algorithm` | all / see mode | Algorithms to compare, or single `astar`/`greedy` with `--onlyheuristics` |
| `--heuristic` | `emm` | Fixed heuristic for `greedy`/`astar` in algorithm mode |
| `--heuristics` | all | Subset of heuristics with `--onlyheuristics` |
| `--yaxis` | **all** | Metrics to plot (`processing_time`, `expanded_nodes`, …); omit = all |
| `--timeout` | none | Per-run limit (seconds) |
| `--runs` | `1` | Repeat each search **N** times per bar; if **N > 1**, bars show **mean ± sample std** over valid samples |
| `--group-yaxis` | off | One figure with **grouped bars** per category; requires explicit `--yaxis` with **2+** metrics (same Y scale; e.g. `processing_time heuristic_time`) |
| `-o` / `--out` | — | **File**: one metric only. **Directory**: one auto-named PNG per metric. **With `--group-yaxis`**: pass a directory or any path under it — the **filename is always auto-generated** (`…__grouped_<metrics>.png`; extension from path if you pass a file) |

Each metric reuses the same batch of runs (no duplicate work across PNGs). With `--runs 1`, one execution per bar per metric.
