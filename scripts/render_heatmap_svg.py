#!/usr/bin/env python3
"""Render data/contributions.json as an animated SVG contribution calendar.

GitHub serves README SVGs through an <img> tag, which renders SMIL and CSS
keyframes but no JavaScript. So the reveal lives entirely in a <style> block:
every cell fades and slides in on a staggered diagonal delay, plays once, and
freezes on the final frame.

Set STATIC=1 to emit a frozen frame (handy for local previews).
"""

from __future__ import annotations

import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(os.path.dirname(HERE), "data", "contributions.json")
OUT_PATH = os.path.join(os.path.dirname(HERE), "contrib-heatmap.svg")

STATIC = os.environ.get("STATIC") == "1"

WEEKS = 53
ROWS = 7
CELL = 12
GAP = 4
PITCH = CELL + GAP

BG = "#0d1117"
EMPTY = "#161b22"
LEVELS = ["#0e4429", "#006d32", "#26a641", "#39d353"]
ACCENT = "#69f0a0"
TEXT = "#7d8590"
TEXT_BRIGHT = "#c9d1d9"
FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

PAD_L = 34
PAD_T = 22
PAD_R = 14
GRID_W = WEEKS * PITCH - GAP
GRID_H = ROWS * PITCH - GAP

STATS_H = 58
LEGEND_H = 26

WIDTH = PAD_L + GRID_W + PAD_R
HEIGHT = PAD_T + GRID_H + LEGEND_H + STATS_H

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Horizontal room a month label needs before the next one would overlap it.
MIN_LABEL_GAP = 34


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x: float, y: float, value: str, *, size: int = 10, fill: str = TEXT,
         anchor: str = "start", weight: str = "400", opacity: str = "1") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" '
        f'opacity="{opacity}">{esc(value)}</text>'
    )


def cell_color(day: dict) -> str:
    level = day["level"]
    if level <= 0:
        return EMPTY
    return LEVELS[min(level, len(LEVELS)) - 1]


def cell(day: dict, col: int, row: int) -> str:
    x = PAD_L + col * PITCH
    y = PAD_T + row * PITCH
    rect = (
        f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
        f'fill="{cell_color(day)}"'
    )
    if STATIC or day["count"] == 0:
        return f"{rect}/>"

    delay = col * 14 + row * 26
    rect = (
        f'{rect} class="cell" style="animation-delay:{delay}ms"/>'
    )
    return rect


def month_labels(days: list[dict]) -> str:
    out = []
    seen: set[int] = set()
    last_x = -MIN_LABEL_GAP
    for col in range(WEEKS):
        chunk = days[col * ROWS:(col + 1) * ROWS]
        if not chunk:
            break
        first = datetime.strptime(chunk[0]["date"], "%Y-%m-%d")
        month = first.month
        if month in seen:
            continue
        # Only label a month if it has room before the next one starts.
        if col + 4 >= WEEKS:
            continue
        x = PAD_L + col * PITCH
        # A window can start mid-month, putting two labels a column apart.
        if x - last_x < MIN_LABEL_GAP:
            continue
        seen.add(month)
        last_x = x
        out.append(text(x, PAD_T - 8, MONTHS[month - 1], size=9, fill=TEXT))
    return "".join(out)


def weekday_labels() -> str:
    out = []
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(
            text(PAD_L - 8, PAD_T + row * PITCH + CELL - 2, label,
                 size=9, fill=TEXT, anchor="end")
        )
    return "".join(out)


def legend() -> str:
    x = PAD_L
    y = PAD_T + GRID_H + 18
    parts = [text(x, y + 8, "Less", size=9, fill=TEXT)]
    x += 30
    swatches = [EMPTY] + LEVELS
    for shade in swatches:
        parts.append(
            f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{shade}"/>'
        )
        x += 15
    parts.append(text(x + 2, y + 9, "More", size=9, fill=TEXT))
    return "".join(parts)


def stat_cells(stats: dict) -> str:
    y = PAD_T + GRID_H + LEGEND_H + 22
    items = [
        (f"{stats['total']:,}", "contributions"),
        (f"{stats['active_days']}", "active days"),
        (f"{stats['longest_streak']}", "day best streak"),
        (f"{stats['busiest_day']}", "busiest day"),
    ]
    parts = []
    span = GRID_W / len(items)
    for index, (value, label) in enumerate(items):
        x = PAD_L + span * index
        parts.append(text(x, y, value, size=17, fill=ACCENT, weight="600"))
        parts.append(text(x, y + 15, label, size=9, fill=TEXT))
        if index:
            parts.append(
                f'<line x1="{x - 16:.1f}" y1="{y - 15}" x2="{x - 16:.1f}" '
                f'y2="{y + 10}" stroke="#21262d" stroke-width="1"/>'
            )
    return "".join(parts)


def build(days: list[dict], stats: dict) -> str:
    cells = []
    for col in range(WEEKS):
        chunk = days[col * ROWS:(col + 1) * ROWS]
        for offset, day in enumerate(chunk):
            observed = datetime.strptime(day["date"], "%Y-%m-%d").weekday()
            row = (observed + 1) % 7
            cells.append(cell(day, col, row))

    style = (
        "<style>"
        "@keyframes cellIn{from{opacity:0;transform:translate(-5px,-5px) scale(.55)}"
        "to{opacity:1;transform:none}}"
        ".cell{transform-box:fill-box;transform-origin:center;"
        "animation:cellIn .42s cubic-bezier(.22,.61,.36,1) both}"
        "</style>"
    ) if not STATIC else ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" \
viewBox="0 0 {WIDTH} {HEIGHT}" role="img" \
aria-label="Contribution calendar: {stats['total']} contributions in the last year">
{style}
<rect width="{WIDTH}" height="{HEIGHT}" rx="10" fill="{BG}"/>
<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="10" fill="none" \
stroke="#21262d"/>
{month_labels(days)}
{weekday_labels()}
{''.join(cells)}
{legend()}
{stat_cells(stats)}
</svg>
"""


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as handle:
        payload = json.load(handle)

    svg = build(payload["days"], payload["stats"])

    target = OUT_PATH
    if STATIC:
        target = os.path.join(HERE, "..", "contrib-heatmap.static.svg")
    with open(os.path.abspath(target), "w", encoding="utf-8") as handle:
        handle.write(svg)

    print(
        f"wrote {os.path.relpath(target, os.getcwd())} "
        f"({WIDTH}x{HEIGHT}, {WEEKS} weeks, {len(payload['days'])} days)"
    )


if __name__ == "__main__":
    main()
