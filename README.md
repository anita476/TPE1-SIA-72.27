# TPE1-SIA-72.27

## Requirements

- Python 3.10+
- Dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

From the project root:

```bash
python scripts/main.py --level levels/level1.txt --algorithm astar --heuristic deadlock
python scripts/run_all_levels.py --algorithm astar --heuristic emm
python scripts/compare_algorithms.py
python scripts/compare_heuristics.py --heuristics emm mm manhattan
python scripts/plot_level_metrics.py --level levels/level1.txt --out plots/
python scripts/plot_directory_deadlock_metrics.py --levels-dir microban_levels --algorithm astar --heuristic deadlock --out plots/deadlocks_microban
python scripts/utils/sokoban_to_png.py levels/level1.txt --output level1.png
```

## Available Algorithms and Heuristics

- Algorithms: `bfs`, `dfs`, `iddfs`, `greedy`, `astar`
- Heuristics:
  - `manhattan`
  - `manhattan_greedy`
  - `basic_hungarian_plus_player_distance`
  - `improved_hungarian_plus_player_distance`
  - `mm`
  - `emm`
  - `deadlock`
  - `combination`
  - `push_distance`

## Main Scripts

### `scripts/main.py` — Solve one level

| Argument      | Default             | Description                       |
| ------------- | ------------------- | --------------------------------- |
| `--level`     | `levels/level1.txt` | Level file path                   |
| `--algorithm` | `dfs`               | Algorithm to use                  |
| `--heuristic` | `emm`               | Used only by `greedy` and `astar` |

### `scripts/run_all_levels.py` — Run all levels in `microban_levels` with one algorithm

| Argument      | Default | Description                        |
| ------------- | ------- | ---------------------------------- |
| `--algorithm` | `bfs`   | Algorithm to use                   |
| `--heuristic` | `emm`   | Used only by `greedy` and `astar`  |
| `--timeout`   | `120`   | Per-level timeout (seconds)        |
| `--verbose`   | —       | Show level state and solution path |

### `scripts/compare_algorithms.py` — Compare algorithms on `levels`

| Argument       | Default | Description                          |
| -------------- | ------- | ------------------------------------ |
| `--algorithms` | all     | Space-separated algorithm list       |
| `--heuristic`  | `emm`   | Fixed heuristic for `greedy`/`astar` |
| `--timeout`    | `60`    | Per-level timeout per algorithm      |

### `scripts/compare_heuristics.py` — Compare heuristics with A\* on `levels`

| Argument       | Default | Description                     |
| -------------- | ------- | ------------------------------- |
| `--heuristics` | all     | Space-separated heuristic list  |
| `--timeout`    | `60`    | Per-level timeout per heuristic |

### `scripts/plot_level_metrics.py` — Bar charts for one Sokoban level

Generates metric charts by algorithm or by heuristic.

| Argument           | Default              | Description                                                    |
| ------------------ | -------------------- | -------------------------------------------------------------- |
| `--level`          | required             | `.txt` level path                                              |
| `--onlyheuristics` | off                  | X-axis = heuristics (requires `--algorithm astar` or `greedy`) |
| `--algorithm`      | all / mode-dependent | Algorithms to compare, or one in heuristics mode               |
| `--heuristic`      | `emm`                | Fixed heuristic in algorithm mode                              |
| `--heuristics`     | all                  | Heuristic subset in `--onlyheuristics` mode                    |
| `--yaxis`          | all                  | Metrics to plot                                                |
| `--timeout`        | none                 | Per-run timeout                                                |
| `--runs`           | `1`                  | Repeats per bar (`>1` uses mean ± sample std)                  |
| `--group-yaxis`    | off                  | Grouped chart with 2+ metrics on the same Y scale              |
| `-o` / `--out`     | —                    | Single file (1 metric) or directory (multiple auto-named PNGs) |

### `scripts/plot_directory_deadlock_metrics.py` — Bar charts for every level in a directory

Runs `greedy` or `astar` with heuristic `deadlock` or `combination` on all `.txt` files in a folder and writes **five** figures: expanded nodes, frontier nodes, deadlock cell count, expanded/deadlock ratio, and frontier/(expanded+frontier).

| Argument       | Default    | Description                                              |
| -------------- | ---------- | -------------------------------------------------------- |
| `--levels-dir` | (required) | Directory of Sokoban `.txt` levels                       |
| `--algorithm`  | (required) | `greedy` or `astar`                                      |
| `--heuristic`  | `deadlock` | `deadlock` or `combination`                              |
| `--timeout`    | none       | Per-level timeout (seconds)                              |
| `-o` / `--out` | none       | Base path or directory; omit to show interactive windows |

Example:

```bash
python scripts/plot_directory_deadlock_metrics.py --levels-dir microban_levels --algorithm astar --heuristic deadlock --out plots/deadlocks_microban
```

### `scripts/utils/sokoban_to_png.py` — Render a level to PNG

Requires **[Pillow](https://python-pillow.org/)** (`pip install pillow`). Renders ASCII Sokoban levels (including `X` deadlock markers) to an image.

| Argument      | Default             | Description                |
| ------------- | ------------------- | -------------------------- |
| `input`       | —                   | Optional `.txt` level path |
| `--output`    | `sokoban_level.png` | Output PNG path            |
| `--tile-size` | `48`                | Tile size in pixels        |

If `input` is omitted, a built-in demo level is rendered.
