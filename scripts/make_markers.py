#!/usr/bin/env python3
"""
Print-ready ArUco markers for the board corners and game pieces.

ID allocation (DICT_4X4_50, IDs 0-49) — must match vision_node:

    0-39    game pieces
    40-45   spare
    46-49   board corners: 46 TL, 47 TR, 48 BR, 49 BL

Usage
    python3 scripts/make_markers.py                    # the 4 corners, 30 mm
    python3 scripts/make_markers.py --size-mm 20       # smaller
    python3 scripts/make_markers.py --ids 0 1 2 3      # piece tags
    python3 scripts/make_markers.py --out /tmp/tags

Print at 100% scale — any "fit to page" will change the physical size, and the
marker must be the size you tell vision_node it is. Measure one after printing.

The white quiet zone around each marker is not decoration: ArUco detection
needs roughly one module of white border, so do not crop it off.
"""

import argparse
import os

import cv2
import numpy as np

DICT = cv2.aruco.DICT_4X4_50
DPI = 300
CORNERS = {46: 'TL', 47: 'TR', 48: 'BR', 49: 'BL'}


def mm_to_px(mm: float) -> int:
    return int(round(mm / 25.4 * DPI))


def render(marker_id: int, size_mm: float) -> np.ndarray:
    """One marker with a quiet zone and a printed label."""
    d = cv2.aruco.getPredefinedDictionary(DICT)
    side = mm_to_px(size_mm)
    img = cv2.aruco.generateImageMarker(d, marker_id, side)

    quiet = max(mm_to_px(size_mm * 0.25), 12)
    label_h = mm_to_px(6)
    canvas = np.full((side + 2 * quiet + label_h, side + 2 * quiet), 255, np.uint8)
    canvas[quiet:quiet + side, quiet:quiet + side] = img

    tag = f'{marker_id}'
    if marker_id in CORNERS:
        tag += f'  {CORNERS[marker_id]}'
    tag += f'   {size_mm:g}mm'
    cv2.putText(canvas, tag, (quiet, side + 2 * quiet + mm_to_px(4)),
                cv2.FONT_HERSHEY_SIMPLEX, size_mm / 40.0, 0, 2)
    return canvas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ids', type=int, nargs='+', default=sorted(CORNERS),
                    help='marker IDs (default: the four board corners)')
    ap.add_argument('--size-mm', type=float, default=30.0)
    ap.add_argument('--out', default='markers')
    args = ap.parse_args()

    bad = [i for i in args.ids if not 0 <= i <= 49]
    if bad:
        raise SystemExit(f'IDs must be 0-49 for DICT_4X4_50; got {bad}')

    os.makedirs(args.out, exist_ok=True)
    tiles = []
    for i in args.ids:
        img = render(i, args.size_mm)
        path = os.path.join(args.out, f'aruco_{i:02d}.png')
        cv2.imwrite(path, img)
        tiles.append(img)
        role = f'  ({CORNERS[i]} corner)' if i in CORNERS else ''
        print(f'  {path}{role}')

    h = max(t.shape[0] for t in tiles)
    pad = [np.pad(t, ((0, h - t.shape[0]), (0, mm_to_px(5))),
                  constant_values=255) for t in tiles]
    sheet_path = os.path.join(args.out, 'sheet.png')
    cv2.imwrite(sheet_path, np.hstack(pad))
    print(f'  {sheet_path}  <- print this at 100% scale, then measure a marker')


if __name__ == '__main__':
    main()
