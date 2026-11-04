"""Shared closed-segment and rectangle geometry; coordinates are metres."""

import math


def segment_intersects_box(a, b, box, pad=0.0):
    lo, hi = 0.0, 1.0
    for axis in (0, 1):
        low, high = box[axis] - pad, box[axis + 2] + pad
        delta = b[axis] - a[axis]
        if abs(delta) < 1e-12:
            if not low <= a[axis] <= high:
                return False
        else:
            t, u = (low - a[axis]) / delta, (high - a[axis]) / delta
            lo, hi = max(lo, min(t, u)), min(hi, max(t, u))
            if lo > hi:
                return False
    return True


def raster_box(box, cell):
    x0, y0, x1, y1 = box
    return [
        math.floor(x0 / cell) * cell,
        math.floor(y0 / cell) * cell,
        math.ceil(x1 / cell) * cell,
        math.ceil(y1 / cell) * cell,
    ]


def project_point(point, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((point[0] - a[0]) * vx + (point[1] - a[1]) * vy) / (vx * vx + vy * vy)))
    p = [a[0] + t * vx, a[1] + t * vy]
    return t, p, math.dist(point, p)
