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
    "floor":       (38,  32,  55),   # dark purple floor
    "floor_inner": (44,  38,  62),   # slightly lighter inner floor
    "wall_face":   (80,  60, 110),   # purple-toned wall face
    "wall_top":    (110, 85, 150),   # lighter wall top highlight
    "wall_shadow": (30,  22,  44),   # wall shadow
    "wall_edge":   (130, 100, 175),  # wall bright edge
    "box":         (210, 140,  50),  # warm amber box
    "box_dark":    (150,  90,  20),  # box shadow side
    "box_light":   (255, 200, 100),  # box highlight
    "box_goal":    (255, 220,  80),  # box-on-goal (golden)
    "box_goal_glow":(255,240,140),
    "goal":        (80, 180, 220),   # cyan goal marker
    "goal_glow":   (120, 220, 255),
    "player":      (100, 220, 160),  # mint-green player
    "player_dark": ( 40, 140,  90),
    "player_light":(180, 255, 200),
    "player_goal": (120, 255, 180),  # player on goal
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
    # goal diamond
    pts = [cx, cy - r,  cx + r, cy,  cx, cy + r,  cx - r, cy]
    draw.polygon(pts, outline=PALETTE["goal"], fill=None)
    draw.polygon(pts, outline=PALETTE["goal"], fill=(*PALETTE["goal"], 80))
    # center dot
    draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=PALETTE["goal"])


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
        # star glow overlay
        draw.ellipse([bx + bw // 4, by + bh // 4,
                      bx + 3 * bw // 4, by + 3 * bh // 4],
                     outline=PALETTE["box_goal_glow"], width=1)


def draw_player(draw: ImageDraw.Draw, x: int, y: int, s: int, on_goal: bool = False):
    draw_floor(draw, x, y, s)
    if on_goal:
        # draw goal underneath
        cx, cy = x + s // 2, y + s // 2
        r = s // 4
        pts = [cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy]
        draw.polygon(pts, outline=PALETTE["goal"])

    cx, cy = x + s // 2, y + s // 2
    pc = PALETTE["player_goal"] if on_goal else PALETTE["player"]

    # body (rounded rect)
    bpad = s // 5
    draw.ellipse([x + bpad, y + bpad, x + s - bpad - 1, y + s - bpad - 1],
                 fill=PALETTE["player_dark"])
    draw.ellipse([x + bpad, y + bpad, x + s - bpad - 2, y + s - bpad - 2],
                 fill=pc)

    # highlight
    hp = bpad + 2
    draw.ellipse([x + hp, y + hp, x + hp + s // 6, y + hp + s // 6],
                 fill=PALETTE["player_light"])

    # direction indicator (small triangle pointing right)
    tr = s // 8
    pts = [cx + tr, cy, cx - tr // 2, cy - tr, cx - tr // 2, cy + tr]
    draw.polygon(pts, fill=PALETTE["player_dark"])


def draw_deadlock(draw: ImageDraw.Draw, x: int, y: int, s: int):
    """Floor tile with a bold red X to mark a deadlock square."""
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

    img = Image.new("RGB", (img_w, img_h), PALETTE["bg"])
    draw = ImageDraw.Draw(img)

    for row_i, row in enumerate(rows):
        for col_i, ch in enumerate(row):
            px = padding + col_i * tile_size
            py = padding + row_i * tile_size
            s = tile_size

            if ch == "#":
                draw_wall(draw, px, py, s)
            elif ch == " ":
                pass  # remains bg
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

    # slight overall vignette
    vignette = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(min(padding, 30)):
        alpha = int(180 * (1 - i / min(padding, 30)))
        vd.rectangle([i, i, img_w - i - 1, img_h - i - 1],
                     outline=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")

    return img


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Render a Sokoban level to PNG.")
    parser.add_argument("--output",    default="sokoban_level.png", help="Output PNG path")
    parser.add_argument("--tile-size", default=48, type=int, help="Tile size in pixels (default 48)")
    args = parser.parse_args()

    print(f"Rendering level ({args.tile_size}px tiles) …")
    img = render_level(LEVEL, tile_size=args.tile_size)
    img.save(args.output)
    print(f"Saved → {args.output}")


if __name__ == "__main__":
    main()