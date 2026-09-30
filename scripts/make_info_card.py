#!/usr/bin/env python3
"""Hand-author a neofetch-style info card as a self-contained animated SVG.

This is the story panel: role, stack and highlights. Stats that GitHub already
shows (the contribution graph) stay out of here on purpose.

GitHub renders README SVGs through <img>, so no JavaScript and no external CSS:
every entrance animation is a CSS keyframe that plays once and freezes.
Set STATIC=1 for a frozen frame.
"""

from __future__ import annotations

import os

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "info-card.svg")

STATIC = os.environ.get("STATIC") == "1"

WIDTH = 512
PAD = 20
BG = "#0d1117"
BORDER = "#21262d"
ACCENT = "#39d353"
ACCENT_BRIGHT = "#69f0a0"
KEY = "#58a6ff"
TEXT = "#c9d1d9"
DIM = "#7d8590"

FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

NAME = "MUHAMMAD SHAHIR KHAN"
HANDLE = "github.com/shahmirkhan106"

# Key/value rows. The first row of each section starts a new block.
ROWS: list[tuple[str, str, str]] = [
    ("meta", "Location", "Karachi, Sindh", ""),
    ("meta", "Focus", "AI / ML  ·  LLM Agent Security", ""),
    ("meta", "Stack", "Python · TypeScript · C++ · Jupyter", ""),
    ("meta", "Repos", "14 public", ""),
    ("meta", "Site", "shahmirkhan106.github.io", ""),
    ("head", "SELECTED BUILDS", "", ""),
    ("item", "", "Pakistan Flood Intelligence", "Earth Engine · RF+GB · Streamlit"),
    ("item", "", "AI Agent Security Paper", "Prompt-injection detection"),
    ("item", "", "AI YouTube Pipeline", "Automated shot generation"),
]

ROW_H = 21
SECTION_GAP = 22
# Clears the identity block: handle baseline (66) and the rule beneath it (76).
TITLE_H = 96
FOOT_H = 14


def esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x: float, y: float, value: str, *, size: int = 12, fill: str = TEXT,
         anchor: str = "start", weight: str = "400") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" '
        f'xml:space="preserve">{esc(value)}</text>'
    )


def measure(value: str, size: int) -> float:
    """Rough advance width for a monospace face."""
    return len(value) * size * 0.6


def layout() -> tuple[int, int, list[tuple[str, int]]]:
    """Return (height, first_row_y, [(kind, y), ...])."""
    y = TITLE_H
    placed = []
    for kind, *_ in ROWS:
        if kind == "head":
            y += SECTION_GAP
            placed.append((kind, y))
            y += 20
        elif kind == "item":
            placed.append((kind, y))
            y += 18
        else:
            placed.append((kind, y))
            y += ROW_H
    return int(y + FOOT_H), TITLE_H, placed


def build() -> str:
    height, _, placed = layout()

    parts: list[str] = []

    # Terminal title bar with three dots and a dim path.
    parts.append(f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" '
                 f'rx="10" fill="{BG}" stroke="{BORDER}"/>')
    for index, dot in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        parts.append(f'<circle cx="{PAD + index * 15}" cy="24" r="4.5" fill="{dot}"/>')
    parts.append(text(PAD + 60, 28, "shahmirkhan106@github: ~",
                      size=10, fill=DIM))

    # Identity block.
    parts.append(text(PAD, 50, NAME, size=16, fill=ACCENT_BRIGHT, weight="600"))
    parts.append(text(PAD, 66, HANDLE, size=10, fill=DIM))
    parts.append(f'<line x1="{PAD}" y1="76" x2="{WIDTH - PAD}" y2="76" '
                 f'stroke="{BORDER}"/>')

    delay = 0
    key_x = PAD + 76
    for (kind, row_y), (rkind, key, value, note) in zip(placed, ROWS):
        style = "" if STATIC else f' class="row" style="animation-delay:{delay}ms"'
        delay += 85

        if rkind == "head":
            parts.append(f'<g{style}>' + text(PAD, row_y, key, size=9,
                                              fill=ACCENT, weight="600") + "</g>")
            continue

        if rkind == "item":
            parts.append(
                f'<g{style}>'
                + text(PAD, row_y, "\u25b8", size=10, fill=ACCENT)
                + text(PAD + 16, row_y, value, size=12, fill=TEXT)
                + text(PAD + 16, row_y + 13, note, size=9, fill=DIM)
                + "</g>"
            )
            continue

        # key/value meta row
        group = [text(key_x, row_y, key, size=11, fill=KEY, anchor="end")]
        group.append(text(key_x + 12, row_y, value, size=11, fill=TEXT))
        parts.append(f'<g{style}>' + "".join(group) + "</g>")

    style = "" if STATIC else (
        "<style>"
        "@keyframes rowIn{from{opacity:0;transform:translateX(-10px)}"
        "to{opacity:1;transform:none}}"
        "@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}"
        ".row{transform-box:fill-box;transform-origin:left center;"
        "animation:rowIn .38s cubic-bezier(.22,.61,.36,1) both}"
        ".cursor{animation:blink 1.1s steps(1,end) 1.4s 2 both}"
        "</style>"
    )

    cursor = "" if STATIC else (
        f'<rect class="cursor" x="{PAD + 60 + measure("shahmirkhan106@github: ~", 10) + 7}"'
        f' y="19" width="7" height="11" rx="1" fill="{ACCENT}"/>'
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" \
viewBox="0 0 {WIDTH} {height}" role="img" \
aria-label="Profile information card for Muhammad Shahmir Khan">
{style}
<rect width="{WIDTH}" height="{height}" rx="10" fill="{BG}"/>
{''.join(parts)}
{cursor}
</svg>
"""


def main() -> None:
    svg = build()
    target = OUT_PATH
    if STATIC:
        target = os.path.join(os.path.dirname(OUT_PATH), "info-card.static.svg")
    with open(target, "w", encoding="utf-8") as handle:
        handle.write(svg)
    print(f"wrote {os.path.relpath(target, os.getcwd())}")


if __name__ == "__main__":
    main()
