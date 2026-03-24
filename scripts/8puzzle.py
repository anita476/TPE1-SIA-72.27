import heapq
import random
import time
import tkinter as tk
from tkinter import ttk
from itertools import permutations

BOARD_SIDE = 3
BOARD_SIZE = BOARD_SIDE * BOARD_SIDE
GOAL_STATE = (1, 2, 3, 4, 5, 6, 7, 8, 0)
DEFAULT_SHUFFLE_MOVES = 40
ANIM_DELAY_MS = 300
REQUIRED_ADJACENCIES = (
    (1, 2),
    (2, 3),
    (4, 5),
    (5, 6),
    (7, 8),
    (1, 4),
    (2, 5),
    (3, 6),
    (4, 7),
    (5, 8),
)

HEURISTIC_HAMMING = "hamming"
HEURISTIC_MANHATTAN = "manhattan"
HEURISTIC_LINEAR_CONFLICT = "manhattan_linear_conflict"
HEURISTIC_MAX = "max_combo"

HEURISTIC_LABELS = {
    HEURISTIC_HAMMING: "Hamming",
    HEURISTIC_MANHATTAN: "Manhattan",
    HEURISTIC_LINEAR_CONFLICT: "Manhattan + Linear Conflict",
    HEURISTIC_MAX: "Max(Hamming, Manhattan, M+LC)",
}

# Paleta inspirada en la referencia (crema + rosa + lila + carbón).
COLOR_BG_MAIN = "#FFF5EC"
COLOR_BG_PANEL = "#E8DCD4"
COLOR_BG_CARD = "#F3EAE3"
COLOR_TEXT_DARK = "#343434"
COLOR_TEXT_SOFT = "#4A454D"
COLOR_ACCENT_PINK = "#FABDBD"
COLOR_ACCENT_PINK_DARK = "#BF8788"
COLOR_ACCENT_PURPLE = "#A97BC2"
COLOR_ACCENT_PURPLE_DARK = "#8E5EAB"
COLOR_ACCENT_LILAC = "#C8A1D9"
COLOR_EMPTY_TILE = "#38383D"
COLOR_EMPTY_TILE_ACTIVE = "#434349"
COLOR_CONFLICT = "#8E5EAB"
COLOR_CONFLICT_SOFT = "#6D5A78"

MOVES = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}

OPPOSITE_MOVE = {
    "UP": "DOWN",
    "DOWN": "UP",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT",
}


def index_to_row_col(index: int) -> tuple[int, int]:
    return divmod(index, BOARD_SIDE)


def row_col_to_index(row: int, col: int) -> int:
    return row * BOARD_SIDE + col


def build_all_goal_states() -> tuple[tuple[int, ...], ...]:
    goals: list[tuple[int, ...]] = []
    for candidate in permutations(range(9)):
        if all(
            tiles_are_adjacent(candidate, tile_a, tile_b)
            for tile_a, tile_b in REQUIRED_ADJACENCIES
        ):
            goals.append(candidate)
    return tuple(goals)


def tiles_are_adjacent(state: tuple[int, ...], tile_a: int, tile_b: int) -> bool:
    index_a = state.index(tile_a)
    index_b = state.index(tile_b)
    row_a, col_a = index_to_row_col(index_a)
    row_b, col_b = index_to_row_col(index_b)
    return abs(row_a - row_b) + abs(col_a - col_b) == 1


def is_goal_state(state: tuple[int, ...]) -> bool:
    return all(tiles_are_adjacent(state, tile_a, tile_b) for tile_a, tile_b in REQUIRED_ADJACENCIES)


ALL_GOAL_STATES = build_all_goal_states()
GOAL_POSITIONS = tuple(
    {
        tile: index_to_row_col(goal_state.index(tile))
        for tile in range(1, 9)
    }
    for goal_state in ALL_GOAL_STATES
)
CANONICAL_GOAL_POSITIONS = {
    tile: index_to_row_col(GOAL_STATE.index(tile))
    for tile in range(1, 9)
}


def inversion_parity(state: tuple[int, ...]) -> int:
    values = [tile for tile in state if tile != 0]
    inversions = 0
    for i, value in enumerate(values):
        for next_value in values[i + 1:]:
            if value > next_value:
                inversions += 1
    return inversions % 2


GOAL_PARITIES = frozenset(inversion_parity(goal_state) for goal_state in ALL_GOAL_STATES)


def is_solvable(state: tuple[int, ...]) -> bool:
    # Con múltiples metas, un estado es resoluble si su paridad coincide con
    # al menos una meta alcanzable.
    return inversion_parity(state) in GOAL_PARITIES


def hamming_distance(state: tuple[int, ...], goal_positions: dict[int, tuple[int, int]]) -> int:
    mismatches = 0
    for index, tile in enumerate(state):
        if tile == 0:
            continue
        row, col = index_to_row_col(index)
        goal_row, goal_col = goal_positions[tile]
        if row != goal_row or col != goal_col:
            mismatches += 1
    return mismatches


def manhattan_distance(state: tuple[int, ...], goal_positions: dict[int, tuple[int, int]]) -> int:
    distance = 0
    for index, tile in enumerate(state):
        if tile == 0:
            continue
        row, col = index_to_row_col(index)
        goal_row, goal_col = goal_positions[tile]
        distance += abs(row - goal_row) + abs(col - goal_col)
    return distance


def linear_conflict_penalty(state: tuple[int, ...], goal_positions: dict[int, tuple[int, int]]) -> int:
    penalty = 0

    for row in range(BOARD_SIDE):
        row_tiles: list[int] = []
        for col in range(BOARD_SIDE):
            tile = state[row_col_to_index(row, col)]
            if tile == 0:
                continue
            goal_row, goal_col = goal_positions[tile]
            if goal_row == row:
                row_tiles.append(goal_col)
        for i in range(len(row_tiles)):
            for j in range(i + 1, len(row_tiles)):
                if row_tiles[i] > row_tiles[j]:
                    penalty += 2

    for col in range(BOARD_SIDE):
        col_tiles: list[int] = []
        for row in range(BOARD_SIDE):
            tile = state[row_col_to_index(row, col)]
            if tile == 0:
                continue
            goal_row, goal_col = goal_positions[tile]
            if goal_col == col:
                col_tiles.append(goal_row)
        for i in range(len(col_tiles)):
            for j in range(i + 1, len(col_tiles)):
                if col_tiles[i] > col_tiles[j]:
                    penalty += 2

    return penalty


def linear_conflict_pairs(
    state: tuple[int, ...],
    goal_positions: dict[int, tuple[int, int]],
) -> list[tuple[int, int, str]]:
    conflicts: list[tuple[int, int, str]] = []

    for row in range(BOARD_SIDE):
        row_data: list[tuple[int, int]] = []
        for col in range(BOARD_SIDE):
            tile = state[row_col_to_index(row, col)]
            if tile == 0:
                continue
            goal_row, goal_col = goal_positions[tile]
            if goal_row == row:
                row_data.append((tile, goal_col))
        for i in range(len(row_data)):
            for j in range(i + 1, len(row_data)):
                tile_i, goal_col_i = row_data[i]
                tile_j, goal_col_j = row_data[j]
                if goal_col_i > goal_col_j:
                    a, b = sorted((tile_i, tile_j))
                    conflicts.append((a, b, "fila"))

    for col in range(BOARD_SIDE):
        col_data: list[tuple[int, int]] = []
        for row in range(BOARD_SIDE):
            tile = state[row_col_to_index(row, col)]
            if tile == 0:
                continue
            goal_row, goal_col = goal_positions[tile]
            if goal_col == col:
                col_data.append((tile, goal_row))
        for i in range(len(col_data)):
            for j in range(i + 1, len(col_data)):
                tile_i, goal_row_i = col_data[i]
                tile_j, goal_row_j = col_data[j]
                if goal_row_i > goal_row_j:
                    a, b = sorted((tile_i, tile_j))
                    conflicts.append((a, b, "columna"))

    # Evita duplicados exactos de pares con mismo tipo.
    return sorted(set(conflicts), key=lambda x: (x[2], x[0], x[1]))


def linear_conflict_count(state: tuple[int, ...], goal_positions: dict[int, tuple[int, int]]) -> int:
    return linear_conflict_penalty(state, goal_positions) // 2


def heuristic_value(state: tuple[int, ...], heuristic_name: str) -> int:
    best = float("inf")
    for goal_positions in GOAL_POSITIONS:
        h_hamming = hamming_distance(state, goal_positions)
        h_manhattan = manhattan_distance(state, goal_positions)
        h_linear = h_manhattan + linear_conflict_penalty(state, goal_positions)

        if heuristic_name == HEURISTIC_HAMMING:
            current = h_hamming
        elif heuristic_name == HEURISTIC_MANHATTAN:
            current = h_manhattan
        elif heuristic_name == HEURISTIC_LINEAR_CONFLICT:
            current = h_linear
        elif heuristic_name == HEURISTIC_MAX:
            current = max(h_hamming, h_manhattan, h_linear)
        else:
            raise ValueError(f"Heurística desconocida: {heuristic_name}")

        if current < best:
            best = current
    return int(best)


def best_linear_conflict_stats(state: tuple[int, ...]) -> tuple[int, int, list[tuple[int, int, str]]]:
    # Debe estar alineado con la heurística Manhattan + Linear Conflict:
    # elegimos la meta que minimiza (manhattan + penalty), no la que minimiza
    # solo el penalty.
    best_linear_value = float("inf")
    best_penalty = float("inf")
    best_count = 0
    best_pairs: list[tuple[int, int, str]] = []
    for goal_positions in GOAL_POSITIONS:
        manhattan = manhattan_distance(state, goal_positions)
        penalty = linear_conflict_penalty(state, goal_positions)
        linear_value = manhattan + penalty
        if (
            linear_value < best_linear_value
            or (linear_value == best_linear_value and penalty < best_penalty)
        ):
            best_linear_value = linear_value
            best_penalty = penalty
            best_count = linear_conflict_count(state, goal_positions)
            best_pairs = linear_conflict_pairs(state, goal_positions)
    return best_count, int(best_penalty), best_pairs


def best_linear_conflict_breakdown(
    state: tuple[int, ...],
) -> tuple[int, int, int, list[tuple[int, int, str]]]:
    """
    Devuelve (manhattan_base, linear_conflict_value, penalty, pairs) para la
    misma meta que minimiza Manhattan+LinearConflict.
    """
    best_linear_value = float("inf")
    best_manhattan = 0
    best_penalty = 0
    best_pairs: list[tuple[int, int, str]] = []

    for goal_positions in GOAL_POSITIONS:
        manhattan = manhattan_distance(state, goal_positions)
        penalty = linear_conflict_penalty(state, goal_positions)
        linear_value = manhattan + penalty
        if (
            linear_value < best_linear_value
            or (linear_value == best_linear_value and penalty < best_penalty)
        ):
            best_linear_value = linear_value
            best_manhattan = manhattan
            best_penalty = penalty
            best_pairs = linear_conflict_pairs(state, goal_positions)

    return best_manhattan, int(best_linear_value), best_penalty, best_pairs


def best_manhattan_breakdown(
    state: tuple[int, ...],
) -> tuple[int, int, int, list[tuple[int, int, str]]]:
    """
    Devuelve (manhattan_value, manhattan_plus_lc_same_goal, penalty, pairs)
    para la meta que minimiza Manhattan.
    """
    best_manhattan = float("inf")
    best_penalty = float("inf")
    best_pairs: list[tuple[int, int, str]] = []

    for goal_positions in GOAL_POSITIONS:
        manhattan = manhattan_distance(state, goal_positions)
        penalty = linear_conflict_penalty(state, goal_positions)
        if (
            manhattan < best_manhattan
            or (manhattan == best_manhattan and penalty < best_penalty)
        ):
            best_manhattan = manhattan
            best_penalty = penalty
            best_pairs = linear_conflict_pairs(state, goal_positions)

    return int(best_manhattan), int(best_manhattan + best_penalty), int(best_penalty), best_pairs


def apply_move(state: tuple[int, ...], move_name: str) -> tuple[int, ...] | None:
    empty_index = state.index(0)
    row, col = index_to_row_col(empty_index)
    delta_row, delta_col = MOVES[move_name]
    next_row = row + delta_row
    next_col = col + delta_col

    if not (0 <= next_row < BOARD_SIDE and 0 <= next_col < BOARD_SIDE):
        return None

    next_index = row_col_to_index(next_row, next_col)
    as_list = list(state)
    as_list[empty_index], as_list[next_index] = as_list[next_index], as_list[empty_index]
    return tuple(as_list)


def get_neighbors(state: tuple[int, ...]) -> list[tuple[str, tuple[int, ...]]]:
    neighbors: list[tuple[str, tuple[int, ...]]] = []
    for move_name in MOVES:
        next_state = apply_move(state, move_name)
        if next_state is not None:
            neighbors.append((move_name, next_state))
    return neighbors


def random_solvable_state(steps: int = DEFAULT_SHUFFLE_MOVES) -> tuple[int, ...]:
    state = GOAL_STATE
    last_move = None
    for _ in range(steps):
        candidates = []
        for move_name, next_state in get_neighbors(state):
            if last_move is not None and move_name == OPPOSITE_MOVE[last_move]:
                continue
            candidates.append((move_name, next_state))
        move_name, state = random.choice(candidates)
        last_move = move_name
    return state


def reconstruct_path(
    parent_by_state: dict[tuple[int, ...], tuple[int, ...] | None],
    move_by_state: dict[tuple[int, ...], str | None],
    goal_state: tuple[int, ...],
) -> list[str]:
    path: list[str] = []
    current = goal_state
    while parent_by_state[current] is not None:
        path.append(move_by_state[current])
        current = parent_by_state[current]
    path.reverse()
    return path


def solve_with_astar(
    start_state: tuple[int, ...],
    heuristic_name: str,
) -> tuple[list[str], int, float] | None:
    if not is_solvable(start_state):
        return None

    start_time = time.perf_counter()
    frontier: list[tuple[int, int, tuple[int, ...]]] = []
    start_h = heuristic_value(start_state, heuristic_name)
    heapq.heappush(frontier, (start_h, 0, start_state))

    parent_by_state: dict[tuple[int, ...], tuple[int, ...] | None] = {start_state: None}
    move_by_state: dict[tuple[int, ...], str | None] = {start_state: None}
    best_cost: dict[tuple[int, ...], int] = {start_state: 0}

    expanded_nodes = 0

    while frontier:
        _, current_cost, state = heapq.heappop(frontier)
        if current_cost != best_cost.get(state):
            continue

        expanded_nodes += 1
        if is_goal_state(state):
            elapsed = time.perf_counter() - start_time
            return reconstruct_path(parent_by_state, move_by_state, state), expanded_nodes, elapsed

        for move_name, next_state in get_neighbors(state):
            next_cost = current_cost + 1
            previous_best = best_cost.get(next_state)
            if previous_best is None or next_cost < previous_best:
                best_cost[next_state] = next_cost
                parent_by_state[next_state] = state
                move_by_state[next_state] = move_name
                priority = next_cost + heuristic_value(next_state, heuristic_name)
                heapq.heappush(frontier, (priority, next_cost, next_state))

    return None


class EightPuzzleVisualizer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("8-Puzzle Visualizador")
        self.root.configure(bg=COLOR_BG_MAIN)
        self.root.geometry("760x840")
        self.root.resizable(False, False)

        self.initial_state = random_solvable_state()
        self.state = self.initial_state
        self.solution_path: list[str] = []
        self.current_step = 0

        self.playing = False
        self.anim_job = None
        self.speed_ms = ANIM_DELAY_MS
        self.selected_heuristic = tk.StringVar(value=HEURISTIC_LINEAR_CONFLICT)

        self.tile_buttons: list[tk.Button] = []
        self.heuristic_vars: dict[str, tk.StringVar] = {}
        self.linear_conflicts_var = tk.StringVar(value="")
        self.linear_conflict_detail_var = tk.StringVar(value="")

        self._build_ui()
        self._draw_board()
        self._update_step_label()
        self._update_heuristics_panel()
        self._set_info("Listo. Podés mezclar o resolver.")

    def _build_ui(self):
        top_bar = tk.Frame(self.root, bg=COLOR_BG_PANEL, padx=12, pady=10)
        top_bar.pack(fill=tk.X)

        tk.Button(
            top_bar,
            text="Mezclar",
            command=self._shuffle_board,
            bg=COLOR_ACCENT_PINK,
            fg=COLOR_TEXT_DARK,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=4,
        ).pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(
            top_bar,
            text="Resolver (A*)",
            command=self._solve,
            bg=COLOR_ACCENT_PURPLE,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=4,
        ).pack(side=tk.LEFT)

        tk.Label(
            top_bar,
            text="Heurística:",
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG_PANEL,
            font=("Segoe UI", 10),
        ).pack(side=tk.LEFT, padx=(14, 4))

        heur_combo = ttk.Combobox(
            top_bar,
            textvariable=self.selected_heuristic,
            values=list(HEURISTIC_LABELS.keys()),
            state="readonly",
            width=24,
        )
        heur_combo.pack(side=tk.LEFT)
        heur_combo.bind("<<ComboboxSelected>>", lambda _: self._update_heuristics_panel())

        board_frame = tk.Frame(self.root, bg=COLOR_BG_MAIN, padx=12, pady=14)
        board_frame.pack()

        for index in range(BOARD_SIZE):
            button = tk.Button(
                board_frame,
                text="",
                width=5,
                height=2,
                font=("Segoe UI", 22, "bold"),
                relief=tk.RAISED,
                command=lambda idx=index: self._handle_tile_click(idx),
            )
            row, col = index_to_row_col(index)
            button.grid(row=row, column=col, padx=4, pady=4, ipadx=4, ipady=4)
            self.tile_buttons.append(button)

        metrics_frame = tk.Frame(self.root, bg=COLOR_BG_CARD, padx=12, pady=8)
        metrics_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        tk.Label(
            metrics_frame,
            text="Heurísticas (estado actual):",
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG_CARD,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")

        for key in (
            HEURISTIC_HAMMING,
            HEURISTIC_MANHATTAN,
            HEURISTIC_LINEAR_CONFLICT,
            HEURISTIC_MAX,
        ):
            var = tk.StringVar(value="")
            self.heuristic_vars[key] = var
            tk.Label(
                metrics_frame,
                textvariable=var,
                fg=COLOR_TEXT_SOFT,
                bg=COLOR_BG_CARD,
                font=("Consolas", 10),
                anchor="w",
                justify=tk.LEFT,
            ).pack(fill=tk.X)

        tk.Label(
            metrics_frame,
            textvariable=self.linear_conflicts_var,
            fg=COLOR_CONFLICT,
            bg=COLOR_BG_CARD,
            font=("Consolas", 10, "bold"),
            anchor="w",
            justify=tk.LEFT,
            pady=4,
        ).pack(fill=tk.X)
        tk.Label(
            metrics_frame,
            textvariable=self.linear_conflict_detail_var,
            fg=COLOR_CONFLICT_SOFT,
            bg=COLOR_BG_CARD,
            font=("Consolas", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=700,
        ).pack(fill=tk.X)

        controls = tk.Frame(self.root, bg=COLOR_BG_PANEL, padx=12, pady=10)
        controls.pack(fill=tk.X, side=tk.BOTTOM)

        button_style = {
            "bg": COLOR_ACCENT_LILAC,
            "fg": "white",
            "font": ("Segoe UI", 10),
            "relief": tk.FLAT,
            "padx": 10,
            "pady": 3,
        }

        self.btn_reset = tk.Button(controls, text="Reset", command=self._reset, **button_style)
        self.btn_reset.pack(side=tk.LEFT, padx=2)

        self.btn_prev = tk.Button(controls, text="Prev", command=self._step_back, **button_style)
        self.btn_prev.pack(side=tk.LEFT, padx=2)

        self.btn_play = tk.Button(
            controls,
            text="Play",
            command=self._toggle_play,
            bg=COLOR_ACCENT_PURPLE,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=3,
        )
        self.btn_play.pack(side=tk.LEFT, padx=2)

        self.btn_next = tk.Button(controls, text="Next", command=self._step_forward, **button_style)
        self.btn_next.pack(side=tk.LEFT, padx=2)

        tk.Label(
            controls,
            text="Velocidad:",
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG_PANEL,
            font=("Segoe UI", 9),
        ).pack(side=tk.LEFT, padx=(20, 4))

        self.speed_var = tk.IntVar(value=ANIM_DELAY_MS)
        tk.Scale(
            controls,
            from_=60,
            to=900,
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            command=self._on_speed_change,
            bg=COLOR_BG_PANEL,
            fg=COLOR_TEXT_DARK,
            highlightthickness=0,
            troughcolor=COLOR_ACCENT_PINK_DARK,
            length=130,
            showvalue=False,
        ).pack(side=tk.LEFT)

        self.speed_label = tk.Label(
            controls,
            text=f"{ANIM_DELAY_MS} ms",
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG_PANEL,
            font=("Segoe UI", 9),
        )
        self.speed_label.pack(side=tk.LEFT, padx=(4, 0))

        self.step_label = tk.Label(
            controls,
            text="",
            fg=COLOR_TEXT_DARK,
            bg=COLOR_BG_PANEL,
            font=("Segoe UI", 10),
        )
        self.step_label.pack(side=tk.RIGHT, padx=6)

        self.info_var = tk.StringVar(value="")
        info_bar = tk.Label(
            self.root,
            textvariable=self.info_var,
            bg=COLOR_BG_MAIN,
            fg=COLOR_TEXT_SOFT,
            font=("Consolas", 9),
            anchor="w",
            padx=12,
            pady=8,
        )
        info_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _set_info(self, text: str):
        self.info_var.set(text)

    def _update_heuristics_panel(self):
        selected = self.selected_heuristic.get()
        values = {
            HEURISTIC_HAMMING: heuristic_value(self.state, HEURISTIC_HAMMING),
            HEURISTIC_MANHATTAN: heuristic_value(self.state, HEURISTIC_MANHATTAN),
            HEURISTIC_LINEAR_CONFLICT: heuristic_value(self.state, HEURISTIC_LINEAR_CONFLICT),
            HEURISTIC_MAX: heuristic_value(self.state, HEURISTIC_MAX),
        }
        for key in (HEURISTIC_HAMMING, HEURISTIC_MANHATTAN, HEURISTIC_LINEAR_CONFLICT, HEURISTIC_MAX):
            marker = " *" if key == selected else ""
            self.heuristic_vars[key].set(f"- {HEURISTIC_LABELS[key]}{marker}: {values[key]}")
        linear_manhattan_base, linear_value, conflict_penalty, conflict_pairs = (
            best_linear_conflict_breakdown(self.state)
        )
        conflict_count = conflict_penalty // 2
        self.linear_conflicts_var.set(
            f"- Conflictos lineales (para M+LC): {conflict_count} "
            f"(penalización total: +{conflict_penalty}) | "
            f"M+LC = {linear_manhattan_base} + {conflict_penalty} = {linear_value}"
        )
        if conflict_pairs:
            lines = [f"    - ({a},{b}) [{kind}]" for a, b, kind in conflict_pairs]
            details_best = "  Piezas en conflicto (meta usada por M+LC):\n" + "\n".join(lines)
        else:
            details_best = "  Piezas en conflicto (meta usada por M+LC): ninguna"

        canonical_penalty = linear_conflict_penalty(self.state, CANONICAL_GOAL_POSITIONS)
        canonical_pairs = linear_conflict_pairs(self.state, CANONICAL_GOAL_POSITIONS)
        canonical_count = canonical_penalty // 2
        if canonical_pairs:
            canonical_pairs_text = ", ".join(
                f"({a},{b})[{kind}]"
                for a, b, kind in canonical_pairs
            )
        else:
            canonical_pairs_text = "ninguna"

        details_canonical = (
            f"  Conflictos en meta canónica (1-2-3/4-5-6/7-8-_): "
            f"{canonical_count} (+{canonical_penalty}) | {canonical_pairs_text}"
        )
        manh_value, manh_plus_lc_same_goal, manh_penalty, manh_pairs = best_manhattan_breakdown(self.state)
        if manh_pairs:
            manh_pairs_text = ", ".join(f"({a},{b})[{kind}]" for a, b, kind in manh_pairs)
        else:
            manh_pairs_text = "ninguna"
        details_manhattan_goal = (
            f"  Conflictos en meta de Manhattan (h={manh_value}): "
            f"{manh_penalty // 2} (+{manh_penalty}) | M+LC en esa meta={manh_plus_lc_same_goal} | "
            f"{manh_pairs_text}"
        )
        self.linear_conflict_detail_var.set(f"{details_best}\n{details_manhattan_goal}\n{details_canonical}")

    def _draw_board(self):
        for index, tile in enumerate(self.state):
            button = self.tile_buttons[index]
            if tile == 0:
                button.config(
                    text="",
                    bg=COLOR_EMPTY_TILE,
                    activebackground=COLOR_EMPTY_TILE_ACTIVE,
                    state=tk.DISABLED,
                )
            else:
                button.config(
                    text=str(tile),
                    bg=COLOR_ACCENT_PINK,
                    activebackground=COLOR_ACCENT_PINK_DARK,
                    fg=COLOR_TEXT_DARK,
                    state=tk.NORMAL,
                )

    def _handle_tile_click(self, tile_index: int):
        if self.playing:
            return
        empty_index = self.state.index(0)
        empty_row, empty_col = index_to_row_col(empty_index)
        tile_row, tile_col = index_to_row_col(tile_index)

        if abs(empty_row - tile_row) + abs(empty_col - tile_col) != 1:
            return

        as_list = list(self.state)
        as_list[empty_index], as_list[tile_index] = as_list[tile_index], as_list[empty_index]
        self.state = tuple(as_list)
        self.initial_state = self.state
        self.solution_path = []
        self.current_step = 0
        self._draw_board()
        self._update_step_label()
        self._update_heuristics_panel()

        if is_goal_state(self.state):
            self._set_info("¡Resuelto manualmente!")
        else:
            self._set_info("Movimiento manual aplicado.")

    def _shuffle_board(self):
        self._stop_play()
        self.initial_state = random_solvable_state()
        self.state = self.initial_state
        self.solution_path = []
        self.current_step = 0
        self._draw_board()
        self._update_step_label()
        self._update_heuristics_panel()
        self._set_info("Tablero mezclado.")

    def _solve(self):
        self._stop_play()
        self.state = self.initial_state
        self.current_step = 0
        self._set_info("Resolviendo con A*...")
        self.root.update()

        heuristic_name = self.selected_heuristic.get()
        result = solve_with_astar(self.initial_state, heuristic_name)
        if result is None:
            self.solution_path = []
            self._set_info("Sin solución para el estado actual.")
            self._draw_board()
            self._update_step_label()
            self._update_heuristics_panel()
            return

        path, expanded_nodes, elapsed = result
        self.solution_path = path
        self._draw_board()
        self._update_step_label()
        self._update_heuristics_panel()
        self._set_info(
            f"Resuelto | h={HEURISTIC_LABELS[heuristic_name]} | "
            f"Pasos: {len(path)} | Nodos expandidos: {expanded_nodes} | Tiempo: {elapsed:.4f}s"
        )

    def _step_forward(self):
        if self.current_step >= len(self.solution_path):
            return
        move_name = self.solution_path[self.current_step]
        next_state = apply_move(self.state, move_name)
        if next_state is None:
            return
        self.state = next_state
        self.current_step += 1
        self._draw_board()
        self._update_step_label()
        self._update_heuristics_panel()

    def _step_back(self):
        if self.current_step <= 0:
            return
        self.current_step -= 1
        self.state = self.initial_state
        for i in range(self.current_step):
            self.state = apply_move(self.state, self.solution_path[i])
        self._draw_board()
        self._update_step_label()
        self._update_heuristics_panel()

    def _reset(self):
        self._stop_play()
        self.state = self.initial_state
        self.current_step = 0
        self._draw_board()
        self._update_step_label()
        self._update_heuristics_panel()
        self._set_info("Estado reiniciado.")

    def _toggle_play(self):
        if self.playing:
            self._stop_play()
        else:
            self._start_play()

    def _start_play(self):
        if not self.solution_path:
            return
        self.playing = True
        self.btn_play.config(text="Pause", bg=COLOR_ACCENT_PINK_DARK, fg="white")
        self._play_tick()

    def _stop_play(self):
        self.playing = False
        self.btn_play.config(text="Play", bg=COLOR_ACCENT_PURPLE, fg="white")
        if self.anim_job is not None:
            self.root.after_cancel(self.anim_job)
            self.anim_job = None

    def _play_tick(self):
        if not self.playing:
            return
        if self.current_step < len(self.solution_path):
            self._step_forward()
            self.anim_job = self.root.after(self.speed_ms, self._play_tick)
        else:
            self._stop_play()

    def _on_speed_change(self, value: str):
        self.speed_ms = int(value)
        self.speed_label.config(text=f"{self.speed_ms} ms")

    def _update_step_label(self):
        total_steps = len(self.solution_path)
        if total_steps > 0:
            self.step_label.config(text=f"Paso {self.current_step}/{total_steps}")
        else:
            self.step_label.config(text="Sin ruta")


def main():
    root = tk.Tk()
    EightPuzzleVisualizer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
