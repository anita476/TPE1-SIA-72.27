# TPE1-SIA-72.27

## Requirements

- Python 3.10+
- Dependencies:

```sh
pip install -r requirements.txt
```
## Optional: Virtual Environment

To use `pipenv` and use virtual environment to run the project run:
```sh
pipenv install
```
And preface all commands with `pipenv run [command] [args..]`


## Quick Start

From the project root:

```bash
python scripts/main.py --level levels/level1.txt --algorithm astar --heuristic deadlock

python scripts/run_all_levels.py --algorithm astar --heuristic emm

python scripts/compare_algorithms.py

python scripts/compare_heuristics.py --heuristics emm mm manhattan

python scripts/plot_level_metrics.py --level levels/level1.txt --out plots/

python scripts/plot_level_metrics.py --all-levels --compare-algorithms-by-heuristic -o plots/microban_by_heuristic/

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

### `scripts/plot_level_metrics.py` — Bar charts for one level or all Microban levels

Pick **exactly one** of `--level PATH` or `--all-levels`. With `--all-levels`, every `microban_levels/level*.txt` is processed; you **must** pass `--out` as a **directory** (non-interactive batch).

**Modes** (do not combine the first two flags):

- **Algorithm mode** (default): X-axis = algorithms. Optional `--algorithm` list; default = all algorithms. For `greedy` / `astar`, fix the heuristic with `--heuristic` (default `emm`). Do not use `--heuristics` in this mode.
- **`--onlyheuristics`**: X-axis = heuristics; pass **exactly one** of `--algorithm greedy` or `--algorithm astar`. Optional `--heuristics` to subset heuristics (default = all).
- **`--compare-algorithms-by-heuristic`**: X-axis = heuristics; grouped bars for `greedy` and/or `astar`. Default algorithms = both; optional `--algorithm greedy`, `--algorithm astar greedy`, etc.

| Argument                             | Default        | Description |
| ------------------------------------ | -------------- | ----------- |
| `--level` *or* `--all-levels`        | (required)     | Single `.txt` path, or batch all `microban_levels/level*.txt` |
| `--onlyheuristics`                   | off            | Heuristic comparison for one of `astar` / `greedy` |
| `--compare-algorithms-by-heuristic`  | off            | `astar` vs `greedy` per heuristic |
| `--algorithm`                        | mode-dependent | Space-separated list (`bfs`, `dfs`, …); constrained as above in heuristic modes |
| `--heuristic`                        | `emm`          | Heuristic for `greedy`/`astar` in algorithm mode (same choices as project heuristics) |
| `--heuristics`                       | all            | Only with `--onlyheuristics` or `--compare-algorithms-by-heuristic` |
| `--yaxis`                            | all            | One or more of: `processing_time`, `heuristic_time`, `memory`, `frontier_nodes`, `expanded_nodes`, `cost`, `boxes_displaced`, `heuristic_time_ratio` |
| `--group-yaxis`                      | off            | Single figure: all `--yaxis` metrics as grouped bars (needs **2+** explicit `--yaxis` values; same Y scale) |
| `--timeout`                          | none           | Per-run time limit (seconds) |
| `--runs`                             | `1`            | Repeat each bar’s search N times; if N>1, mean ± sample std |
| `-o` / `--out`                       | interactive*   | Directory → auto-named files per metric (and per level if `--all-levels`). Single `.png`/`.pdf`/… only if **one** metric in `--yaxis`. Omitting `--out` is allowed only for a **single** level and **one** metric (or default all metrics forces `--out` dir). |

Examples:

```sh
python scripts/plot_level_metrics.py --level levels/level1.txt --yaxis expanded_nodes -o plots/expanded.png

python scripts/plot_level_metrics.py --level levels/level1.txt --runs 5 --out plots/

python scripts/plot_level_metrics.py --level levels/level1.txt --onlyheuristics --algorithm astar --out plots/

python scripts/plot_level_metrics.py --all-levels --compare-algorithms-by-heuristic -o plots/microban_by_heuristic/
```

### `scripts/plot_directory_deadlock_metrics.py` — Deadlock-oriented metrics for every level in a directory

| Argument       | Default    | Description |
| -------------- | ---------- | ----------- |
| `--levels-dir` | (required) | Folder of Sokoban `.txt` levels (path relative to repo root works) |
| `--algorithm`  | (required) | `greedy` or `astar` |
| `--heuristic`  | `deadlock` | `deadlock`, `combination`, or `emm` |
| `--timeout`    | none       | Per-level timeout (seconds) |
| `-o` / `--out` | none       | Omit → `matplotlib` interactive windows. If set: either an image path like `plots/base.png` → writes `plots/base__expanded_nodes.png`, `base__frontier_nodes.png`, … same extension; or a **directory** → creates it if needed and writes `directory_deadlock_metrics__*.png` inside that directory |

Example:

```bash
python scripts/plot_directory_deadlock_metrics.py --levels-dir microban_levels --algorithm astar --heuristic deadlock --out plots/deadlocks_microban

python scripts/plot_directory_deadlock_metrics.py --levels-dir microban_levels --algorithm greedy --heuristic emm -o plots/greedy_emm.png

```

### `scripts/utils/sokoban_to_png.py` — Render a level to PNG

Requires **[Pillow](https://python-pillow.org/)** (`pip install pillow`). Renders ASCII Sokoban levels (including `X` deadlock markers) to an image.

| Argument      | Default             | Description                |
| ------------- | ------------------- | -------------------------- |
| `input`       | —                   | Optional `.txt` level path |
| `--output`    | `sokoban_level.png` | Output PNG path            |
| `--tile-size` | `48`                | Tile size in pixels        |
