#!/usr/bin/env python3
"""Convert the prepped photo into a self-typing ASCII portrait SVG.

The grid is downsampled to COLS x ROWS characters and each cell's brightness
picks a glyph from a density ramp, sparse for bright areas and dense for dark.

Two choices keep it clean rather than noisy:
  * one light-gray fill for every character (per-character rainbow coloring is
    exactly what makes most ASCII portraits look like static);
  * the matte is honoured, so background cells print nothing at all.

Motion is SMIL inside the SVG: each row sits in a horizontal clip that wipes
left to right with a small block cursor riding the edge, staggered top to
bottom. It prints once and freezes - no looping.

    python scripts/make_ascii_svg.py
"""

from __future__ import annotations

import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IN_PATH = os.path.join(ROOT, "source-prepped.png")
OUT_PATH = os.path.join(ROOT, "portrait.svg")

STATIC = os.environ.get("STATIC") == "1"

# bright (sparse) -> dark (dense). The leading space is what blanks the matte.
RAMP = " .`\\`:-=+*cs#%@"

ROWS = 46
# Monospace characters are ~0.6 as wide as they are tall, so an undistorted
# image comes out 0.6 x (source aspect). STRETCH widens the grid past that to
# buy a landscape-ish panel; 1.0 keeps true proportions (and a tall, narrow
# portrait). 1.45 is the compromise that suits a near-square headshot.
STRETCH = float(os.environ.get("ASCII_STRETCH", "1.45"))

FONT_SIZE = 12
LINE_H = 12.2
ADVANCE = FONT_SIZE * 0.6          # monospace advance width
TOP_PAD = 4
BASELINE = 9.4                    # baseline offset inside a line box

FILL = "#8b949e"                  # GitHub's muted text grey: reads on both themes
CURSOR = "#39d353"

ROW_DUR = "0.55s"
ROW_STAGGER = "0.045"
ALPHA_CUT = 128                   # below this a downsampled cell is background
DARK_PCT, BRIGHT_PCT = 2.0, 98.0  # clip tails so one specular pixel can't flatten it


def esc(value: str) -> str:
    return (value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def load_cells() -> tuple[np.ndarray, np.ndarray]:
    """Downsample to a grid of (luma, is_subject) samples.

    The grid is sized from the image's own aspect ratio so each character cell
    covers a square patch of pixels - that is what keeps the face from being
    stretched. STRETCH is the one deliberate exception.
    """
    rgba = np.array(Image.open(IN_PATH).convert("RGBA"), dtype=np.float32)
    alpha = rgba[:, :, 3]
    gray = rgba[:, :, 0]
    height, width = gray.shape

    cols = max(8, round(ROWS * (width / height) * STRETCH))

    # Composite onto white *before* resizing, so averaging never blends the
    # subject with the transparent (black) matte.
    on_white = np.where(alpha > 0, gray, 255.0)

    luma = np.array(
        Image.fromarray(on_white.astype(np.uint8)).resize((cols, ROWS), Image.LANCZOS),
        dtype=np.float32,
    )
    matte = np.array(
        Image.fromarray(alpha.astype(np.uint8)).resize((cols, ROWS), Image.LANCZOS),
        dtype=np.float32,
    )
    return luma, matte > ALPHA_CUT, cols


def to_ascii(luma: np.ndarray, subject: np.ndarray, cols: int) -> list[str]:
    values = luma[subject]
    if values.size == 0:
        return [""] * ROWS

    dark = float(np.percentile(values, DARK_PCT))
    bright = float(np.percentile(values, BRIGHT_PCT))
    span = max(bright - dark, 1.0)

    normalized = np.clip((luma - dark) / span, 0.0, 1.0)
    # Brightness 1.0 -> sparse (index 0); darkness 0.0 -> dense (last index).
    index = np.round((1.0 - normalized) * (len(RAMP) - 1)).astype(int)

    rows = []
    for row in range(ROWS):
        chars = [
            RAMP[index[row, col]] if subject[row, col] else " " for col in range(cols)
        ]
        rows.append("".join(chars).rstrip())
    return rows


def row_svg(index: int, content: str, width: int) -> str:
    y = TOP_PAD + index * LINE_H
    baseline = y + BASELINE
    begin = f"{index * float(ROW_STAGGER):.3f}s"

    if STATIC:
        return (
            f'<text x="0" y="{baseline:.1f}" font-family="ui-monospace,Menlo,Consolas,'
            f'monospace" font-size="{FONT_SIZE}" fill="{FILL}" '
            f'xml:space="preserve">{esc(content)}</text>'
        )

    return f"""<clipPath id="row{index}"><rect x="0" y="{y:.1f}" width="0" \
height="{LINE_H:.1f}"><animate attributeName="width" from="0" to="{width}" \
dur="{ROW_DUR}" begin="{begin}" fill="freeze"/></rect></clipPath>
<g clip-path="url(#row{index})"><text x="0" y="{baseline:.1f}" \
font-family="ui-monospace,Menlo,Consolas,monospace" font-size="{FONT_SIZE}" \
fill="{FILL}" xml:space="preserve">{esc(content)}</text><rect x="0" \
y="{y:.1f}" width="6" height="{LINE_H:.1f}" fill="{CURSOR}" opacity="0.9">\
<animate attributeName="x" from="0" to="{width}" dur="{ROW_DUR}" begin="{begin}" \
fill="freeze"/></rect></g>"""


def build(rows: list[str], width: int, height: int) -> str:
    body = "".join(
        row_svg(i, content, width) for i, content in enumerate(rows) if content
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" \
height="{height}" viewBox="0 0 {width} {height}" role="img" \
aria-label="ASCII art portrait of Muhammad Shahmir Khan">
{body}
</svg>
"""


def main() -> None:
    luma, subject, cols = load_cells()
    rows = to_ascii(luma, subject, cols)

    width = round(cols * ADVANCE)
    height = round(ROWS * LINE_H + TOP_PAD * 2)

    svg = build(rows, width, height)
    filled = sum(1 for row in rows if row.strip())

    target = OUT_PATH
    if STATIC:
        target = os.path.join(ROOT, "portrait.static.svg")
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(svg)

    print(
        f"wrote {os.path.relpath(target, os.getcwd())} "
        f"({width}x{height}, {cols}x{ROWS} grid, {filled}/{ROWS} rows inked, "
        f"rendered aspect {width / height:.3f})"
    )
    if STATIC:
        for row in rows:
            print(row)


if __name__ == "__main__":
    main()
