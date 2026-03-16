# TPE1-SIA-72.27

## Build

No compilation required. Python 3.10+ with standard library only.

## Run

From the project root:

```bash
python scripts/main.py --level levels/level1.txt --algorithm bfs
python scripts/run_all_levels.py --algorithm bfs
python scripts/compare_algorithms.py
```

### main.py — Solve a single level

| Argument     | Default              | Description        |
|-------------|----------------------|--------------------|
| `--level`   | `levels/level1.txt`  | Path to level file |
| `--algorithm` | `dfs`              | `bfs`, `dfs`, `iddfs` |

### run_all_levels.py — Run all levels with one algorithm

| Argument     | Default | Description                    |
|-------------|---------|--------------------------------|
| `--algorithm` | `bfs` | `bfs`, `dfs`, `iddfs`          |
| `--timeout` | `60`    | Seconds per level              |
| `--verbose` | —       | Show level state and solution  |

### compare_algorithms.py — Compare algorithms on all levels

| Argument      | Default           | Description                    |
|--------------|-------------------|--------------------------------|
| `--timeout`  | `60`              | Seconds per level per algorithm |
| `--algorithms` | `bfs dfs iddfs` | Space-separated algorithm list  |
