# TPE1-SIA-72.27

## Build

No compilation required. Python 3.10+ with standard library only.

## Run

From the project root:

```bash
python scripts/main.py --level levels/level1.txt --algorithm bfs
python scripts/run_all_levels.py --algorithm astar --heuristic emm
python scripts/compare_algorithms.py
python scripts/compare_heuristics.py --heuristics emm mm manhattan
```

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
