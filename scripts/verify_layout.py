#!/usr/bin/env python3
"""Geometry check for the generated SVG cards: overflow, collisions, bounds.

Run after regenerating any SVG. Exits non-zero on a layout fault so a bad
layout can never reach a commit unnoticed.

    python scripts/verify_layout.py
"""

from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# True monospace advance ratio. The portrait grid is sized from this exact
# ratio, so allow 1px of slack at the edges rather than a fudge factor.
MONO_ADVANCE = 0.60
EDGE_SLACK = 1


def load(path: str) -> ET.Element:
    return ET.parse(path).getroot()


def check(path: str) -> list[str]:
    root = load(path)
    width = int(float(root.get("width", "0")))
    height = int(float(root.get("height", "0")))
    problems: list[str] = []

    def fail(message: str) -> None:
        problems.append(f"{os.path.basename(path)}: {message}")

    texts = []
    for node in root.iter(f"{SVG_NS}text"):
        content = "".join(node.itertext())
        if not content.strip():
            continue
        x = float(node.get("x", "0"))
        y = float(node.get("y", "0"))
        size = float(node.get("font-size", "12"))
        anchor = node.get("text-anchor", "start")
        advance = len(content) * size * MONO_ADVANCE

        if anchor == "start":
            left, right = x, x + advance
        elif anchor == "end":
            left, right = x - advance, x
        else:
            left, right = x - advance / 2, x + advance / 2

        if right > width + EDGE_SLACK:
            fail(f"text overflows right edge: {content!r} ends at {right:.0f} of {width}")
        if left < -EDGE_SLACK:
            fail(f"text overflows left edge: {content!r} starts at {left:.0f}")
        if not (2 <= y <= height - 2):
            fail(f"text vertically clipped: {content!r} at y={y} of {height}")
        texts.append((y, left, right, content))

    # Same-baseline horizontal collisions.
    by_baseline: dict[float, list[tuple[float, float, str]]] = {}
    for y, left, right, content in texts:
        by_baseline.setdefault(round(y, 1), []).append((left, right, content))
    for y, items in by_baseline.items():
        items.sort()
        for (l1, r1, c1), (l2, r2, c2) in zip(items, items[1:]):
            if l2 < r1 - 0.5:
                fail(f"text collision at y={y}: {c1!r} and {c2!r} overlap by {r1 - l2:.0f}px")

    for node in root.iter(f"{SVG_NS}rect"):
        if node.get("rx") != "3" and node.get("width") is None:
            continue
    return problems


def main() -> int:
    targets = [
        os.path.join(HERE, "contrib-heatmap.static.svg"),
        os.path.join(HERE, "info-card.static.svg"),
        os.path.join(HERE, "portrait.static.svg"),
    ]

    all_problems: list[str] = []
    checked = 0
    for target in targets:
        if not os.path.exists(target):
            print(f"skip (missing) {os.path.basename(target)}")
            continue
        all_problems.extend(check(target))
        checked += 1

    if all_problems:
        print(f"\n{len(all_problems)} layout problem(s):")
        for problem in all_problems:
            print(f"  FAIL {problem}")
        return 1

    print(f"layout OK across {checked} SVG(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
