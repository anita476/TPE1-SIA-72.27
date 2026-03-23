#!/usr/bin/env python3
"""
Sokoban Level to PNG renderer

Tile legend:
    ' '  empty floor / outside
    '#'  wall
    '@'  player
    '+'  player on goal
    '$'  box
    '*'  box on goal
    '.'  goal
    'X'  deadlock square 
"""

import argparse
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math

# ── Level data ────────────────────────────────────────────────────────────────
LEVEL = """\
#####################
####XXX##############
#### # ##############
#### # X#XXX#XXX#####
#X     X#X$   $ #####
#X## #$X#X X#   #XXX#
#X$  #XX## ## $   $X#
#X## ##### X#XXX#  X#
#X$  X#XX#  ##### ###
### $    @  ...## ###
###XXX#     ...## ###
#######XX###...## ###
#################  X#
################# $X#
#################XXX#
#####################"""

# ── Palette ───────────────────────────────────────────────────────────────────

PALETTE = {
    "bg":          (15,  12,  24),   # deep void outside
    "floor":       (232, 220, 206),  # subtle tile border on #fff5ec
    "floor_inner": (255, 245, 236),  # #fff5ec
    "wall_face":   ( 52,  52,  52),  # #343434
    "wall_top":    ( 75,  75,  75),  # lighter gray top
    "wall_shadow": ( 25,  25,  25),  # dark shadow
    "wall_edge":   ( 90,  90,  90),  # light gray edge
    "box":         (168, 165, 178),  # cool light gray
    "box_dark":    (115, 112, 125),  # darker gray shadow
    "box_light":   (205, 203, 213),  # lighter gray highlight
    "box_goal":    (175, 172, 185),  # same gray on goal
    "box_goal_glow":(210, 208, 218),  # pale gray glow
    "goal":        (160, 103, 174),  # #a067ae purple
    "goal_glow":   (188, 129, 202),  # #bc81ca lighter purple
    "player":      ( 45, 155, 175),  # dark turquoise-blue
    "player_dark": ( 25, 100, 120),  # deeper shadow
    "player_light":( 95, 200, 218),  # lighter highlight
    "player_goal": ( 45, 155, 175),  # same on goal
    "deadlock":    (220,  50,  50),  # red X deadlock
    "deadlock_dark":(140,  20,  20),  # X shadow
    "deadlock_glow":(255, 100, 100),  # X glow
}

# ── Rendering helpers ─────────────────────────────────────────────────────────

def parse_level(text: str) -> list[str]:
    lines = text.splitlines()
    if lines and lines[0] == "":
        lines = lines[1:]
    if lines and lines[-1] == "":
        lines = lines[:-1]
    max_w = max(len(l) for l in lines)
    return [l.ljust(max_w) for l in lines]


def draw_wall(draw: ImageDraw.Draw, x: int, y: int, s: int):
    """Isometric-ish 2.5-D wall tile."""
    top = 4  # height of the 3-D top face
    # main face
    draw.rectangle([x, y + top, x + s - 1, y + s - 1], fill=PALETTE["wall_face"])
    # top face (bevel)
    pts = [x, y + top,  x + top, y,  x + s - 1, y,  x + s - 1, y + top]
    draw.polygon(pts, fill=PALETTE["wall_top"])
    # left shadow strip
    draw.rectangle([x, y + top, x + 1, y + s - 1], fill=PALETTE["wall_shadow"])
    # bright right edge
    draw.line([x + s - 1, y + top, x + s - 1, y + s - 1], fill=PALETTE["wall_edge"], width=1)
    # subtle inner grid line
    draw.rectangle([x + 2, y + top + 2, x + s - 3, y + s - 3],
                   outline=PALETTE["wall_shadow"])


def draw_floor(draw: ImageDraw.Draw, x: int, y: int, s: int):
    draw.rectangle([x, y, x + s - 1, y + s - 1], fill=PALETTE["floor"])
    # subtle inner panel
    draw.rectangle([x + 2, y + 2, x + s - 3, y + s - 3], fill=PALETTE["floor_inner"])


def draw_goal(draw: ImageDraw.Draw, x: int, y: int, s: int):
    draw_floor(draw, x, y, s)
    cx, cy = x + s // 2, y + s // 2
    r = s // 4
    # glow ring
    draw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2],
                 outline=PALETTE["goal_glow"], width=1)
    # goal diamond — fully opaque fill
    pts = [cx, cy - r,  cx + r, cy,  cx, cy + r,  cx - r, cy]
    draw.polygon(pts, outline=PALETTE["goal"], fill=PALETTE["goal"])
    # center dot
    draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=PALETTE["goal_glow"])


def draw_box(draw: ImageDraw.Draw, x: int, y: int, s: int, on_goal: bool = False):
    draw_floor(draw, x, y, s)
    pad = s // 8
    bx, by = x + pad, y + pad
    bw, bh = s - 2 * pad, s - 2 * pad

    face_col  = PALETTE["box_goal"]       if on_goal else PALETTE["box"]
    light_col = PALETTE["box_goal_glow"]  if on_goal else PALETTE["box_light"]
    dark_col  = PALETTE["box_dark"]

    # box body
    draw.rectangle([bx, by, bx + bw - 1, by + bh - 1], fill=face_col)
    # top highlight
    draw.rectangle([bx, by, bx + bw - 1, by + 3], fill=light_col)
    # left highlight
    draw.rectangle([bx, by, bx + 3, by + bh - 1], fill=light_col)
    # bottom shadow
    draw.rectangle([bx, by + bh - 4, bx + bw - 1, by + bh - 1], fill=dark_col)
    # right shadow
    draw.rectangle([bx + bw - 4, by, bx + bw - 1, by + bh - 1], fill=dark_col)
    # cross detail
    cx, cy = bx + bw // 2, by + bh // 2
    draw.line([cx, by + 4, cx, by + bh - 5], fill=dark_col, width=1)
    draw.line([bx + 4, cy, bx + bw - 5, cy], fill=dark_col, width=1)

    if on_goal:
        # mini goal marker (ring + diamond + dot) centered on the tile
        cx, cy = x + s // 2, y + s // 2
        r = s // 5
        draw.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2],
                     outline=PALETTE["goal_glow"], width=1)
        pts = [cx, cy - r,  cx + r, cy,  cx, cy + r,  cx - r, cy]
        draw.polygon(pts, fill=PALETTE["goal"], outline=PALETTE["goal"])
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=PALETTE["goal_glow"])


def draw_player(draw: ImageDraw.Draw, x: int, y: int, s: int, on_goal: bool = False):
    draw_floor(draw, x, y, s)
    cx, cy = x + s // 2, y + s // 2
    pc = PALETTE["player_goal"] if on_goal else PALETTE["player"]

    bpad = s // 5
    draw.ellipse([x + bpad, y + bpad, x + s - bpad - 1, y + s - bpad - 1],
                 fill=PALETTE["player_dark"])
    draw.ellipse([x + bpad, y + bpad, x + s - bpad - 2, y + s - bpad - 2],
                 fill=pc)

    # highlight
    hp = bpad + 2
    draw.ellipse([x + hp, y + hp, x + hp + s // 6, y + hp + s // 6],
                 fill=PALETTE["player_light"])


def draw_deadlock(draw: ImageDraw.Draw, x: int, y: int, s: int):
    """Bold red X to mark a deadlock square."""
    draw_floor(draw, x, y, s)
    pad = s // 6
    thick = max(3, s // 10)

    # Shadow X (offset by 1px for depth)
    shadow = PALETTE["deadlock_dark"]
    draw.line([x + pad + 1, y + pad + 1, x + s - pad + 1, y + s - pad + 1],
              fill=shadow, width=thick + 2)
    draw.line([x + s - pad + 1, y + pad + 1, x + pad + 1, y + s - pad + 1],
              fill=shadow, width=thick + 2)

    # Glow X (slightly wider, dimmer)
    glow = PALETTE["deadlock_glow"]
    draw.line([x + pad, y + pad, x + s - pad, y + s - pad],
              fill=glow, width=thick + 4)
    draw.line([x + s - pad, y + pad, x + pad, y + s - pad],
              fill=glow, width=thick + 4)

    # Main red X
    red = PALETTE["deadlock"]
    draw.line([x + pad, y + pad, x + s - pad, y + s - pad],
              fill=red, width=thick)
    draw.line([x + s - pad, y + pad, x + pad, y + s - pad],
              fill=red, width=thick)

    # Bright end-cap dots for a polished look
    r = thick // 2 + 1
    for cx, cy in [(x + pad, y + pad), (x + s - pad, y + pad),
                   (x + pad, y + s - pad), (x + s - pad, y + s - pad)]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=glow)


def render_level(level_text: str, tile_size: int = 48) -> Image.Image:
    rows = parse_level(level_text)
    grid_h = len(rows)
    grid_w = max(len(r) for r in rows)
    padding = tile_size

    img_w = grid_w * tile_size + 2 * padding
    img_h = grid_h * tile_size + 2 * padding

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for row_i, row in enumerate(rows):
        for col_i, ch in enumerate(row):
            px = padding + col_i * tile_size
            py = padding + row_i * tile_size
            s = tile_size

            if ch == "#":
                draw_wall(draw, px, py, s)
            elif ch == " ":
                pass  # remains transparent
            elif ch == ".":
                draw_goal(draw, px, py, s)
            elif ch == "$":
                draw_box(draw, px, py, s, on_goal=False)
            elif ch == "*":
                draw_box(draw, px, py, s, on_goal=True)
            elif ch == "@":
                draw_player(draw, px, py, s, on_goal=False)
            elif ch == "+":
                draw_player(draw, px, py, s, on_goal=True)
            elif ch == "X":
                draw_deadlock(draw, px, py, s)
            else:
                draw_floor(draw, px, py, s)

    return img


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Render a Sokoban level to PNG.")
    parser.add_argument("input",       nargs="?",             help="Path to a .txt level file (optional, falls back to built-in LEVEL)")
    parser.add_argument("--output",    default="sokoban_level.png", help="Output PNG path")
    parser.add_argument("--tile-size", default=48, type=int,  help="Tile size in pixels (default 48)")
    args = parser.parse_args()

    if args.input:
        with open(args.input) as f:
            level = f.read()
    else:
        level = LEVEL

    print(f"Rendering level ({args.tile_size}px tiles) …")
    img = render_level(level, tile_size=args.tile_size)
    img.save(args.output)
    print(f"Saved → {args.output}")


if __name__ == "__main__":
    main()