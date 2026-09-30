#!/usr/bin/env python3
"""Prepare a photo for ASCII conversion: isolate the subject, then add contrast.

A flatly-lit face converts to a dark unreadable blob, so this does three things:

1. remove the background (rembg) so the subject is isolated;
2. boost *local* contrast with OpenCV's CLAHE, which is what gives a flat face
   real highlights and shadows;
3. emit the subject as grayscale with a transparent background, so the ASCII
   stage can blank the background to the space glyph instead of guessing.

Run once per photo. Not used by the daily workflow.

    python scripts/prep_photo.py source-photo.jpg
"""

from __future__ import annotations

import os
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_PATH = os.path.join(ROOT, "source-prepped.png")

CLAHE_CLIP = 2.5
CLAHE_GRID = (8, 8)
MIN_SIDE = 640
MARGIN = 0.04  # fraction of the subject's longer side kept as padding


def load_rgba(path: str) -> Image.Image:
    return Image.open(path).convert("RGBA")


def strip_background(image: Image.Image) -> Image.Image:
    session = new_session("u2netp")
    return remove(image, session=session).convert("RGBA")


def enlarge(image: Image.Image) -> Image.Image:
    """u2netp segments best with some resolution to work with."""
    if min(image.size) >= MIN_SIDE:
        return image
    scale = MIN_SIDE / min(image.size)
    new_size = (round(image.width * scale), round(image.height * scale))
    return image.resize(new_size, Image.LANCZOS)


def boost_contrast(gray: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_GRID)
    return clahe.apply(gray)


def crop_to_subject(gray: np.ndarray, alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Trim the empty frame so the ASCII grid is spent entirely on the subject.

    Avatars are usually cropped square, which leaves dead space at the top and
    cuts the shoulders at an edge. Trimming to the matte's bounding box (plus a
    small margin) keeps the head from floating in blank rows.
    """
    ys, xs = np.where(alpha > 0)
    if ys.size == 0:
        return gray, alpha

    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    pad = int(round(max(y1 - y0, x1 - x0) * MARGIN))

    height, width = gray.shape
    y0, x0 = max(0, y0 - pad), max(0, x0 - pad)
    y1, x1 = min(height, y1 + pad), min(width, x1 + pad)

    return gray[y0:y1, x0:x1], alpha[y0:y1, x0:x1]


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {os.path.basename(sys.argv[0])} <photo>", file=sys.stderr)
        return 2

    source = sys.argv[1]
    if not os.path.exists(source):
        print(f"error: no such file: {source}", file=sys.stderr)
        return 1

    image = enlarge(load_rgba(source))
    image = strip_background(image)

    rgba = np.array(image)
    alpha = rgba[:, :, 3]
    gray = boost_contrast(cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY))

    # Kill the background's contribution entirely so CLAHE's tile edges and the
    # matte's soft fringe cannot bleed noise into the subject's edge cells.
    gray = np.where(alpha > 0, gray, 255).astype(np.uint8)

    gray, alpha = crop_to_subject(gray, alpha)

    out = Image.fromarray(np.dstack([gray, gray, gray, alpha]), mode="RGBA")
    out.save(OUT_PATH)

    coverage = float((alpha > 0).mean())
    print(
        f"wrote {os.path.relpath(OUT_PATH, os.getcwd())} "
        f"({out.width}x{out.height}, subject covers {coverage * 100:.1f}% of frame, "
        f"aspect {out.width / out.height:.3f})"
    )
    if coverage < 0.04:
        print("warning: subject barely detected; ASCII output will be near-empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
