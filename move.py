from collections import namedtuple
from typing import Tuple, Optional, List, NamedTuple
import math

# Rect = namedtuple("Rect", ["xmin", "xmax", "ymin", "ymax"])

class Rect(NamedTuple):
    xmin: float
    xmax: float
    ymin: float
    ymax: float

"""
def center(rect: Rect) -> Tuple[float, float]:
    return ((rect.xmin + rect.xmax) / 2, (rect.ymin + rect.ymax) / 2)

def size(rect: Rect) -> Tuple[float, float]:
    return (rect.xmax - rect.xmin, rect.ymax - rect.ymin)

def normalize(dx: float, dy: float) -> Tuple[float, float]:
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, 0.0
    return dx / length, dy / length

def move_rect(rect: Rect, dx: float, dy: float, dist: float) -> Rect:
    return Rect(
        rect.xmin + dx * dist,
        rect.xmax + dx * dist,
        rect.ymin + dy * dist,
        rect.ymax + dy * dist
    )

def swept_collision_distance(
    moving: Rect, obstacle: Rect, dx: float, dy: float
) -> Optional[float]:
    invdx = 1 / dx if dx != 0 else float('inf')
    invdy = 1 / dy if dy != 0 else float('inf')

    mw, mh = size(moving)

    exmin = obstacle.xmin - mw
    exmax = obstacle.xmax
    eymin = obstacle.ymin - mh
    eymax = obstacle.ymax

    tx1 = (exmin - moving.xmin) * invdx
    tx2 = (exmax - moving.xmin) * invdx
    ty1 = (eymin - moving.ymin) * invdy
    ty2 = (eymax - moving.ymin) * invdy

    tmin = max(min(tx1, tx2), min(ty1, ty2))
    tmax = min(max(tx1, tx2), max(ty1, ty2))

    if tmax < 0 or tmin > tmax:
        return None
    return max(tmin, 0)

def compute_max_translation(
    moving: Rect, target: Rect, obstacles: List[Rect]
) -> tuple[float, float]:
    cxA, cyA = center(moving)
    cxB, cyB = center(target)
    dx, dy = normalize(cxB - cxA, cyB - cyA)
    if dx == dy == 0:
        return (0.0, 0.0)

    hwA, hhA = size(moving)[0] / 2, size(moving)[1] / 2
    hwB, hhB = size(target)[0] / 2, size(target)[1] / 2

    center_dist = math.hypot(cxB - cxA, cyB - cyA)
    proj_extent = abs(dx) * (hwA + hwB) + abs(dy) * (hhA + hhB)
    max_target_dist = max(0.0, center_dist - proj_extent)

    min_dist = max_target_dist
    for obs in obstacles:
        dist = swept_collision_distance(moving, obs, dx, dy)
        if dist is not None and dist < min_dist:
            min_dist = dist

    return (dx * min_dist, dy * min_dist)
"""

def movement_to_touch(A: Rect, B: Rect) -> tuple[float, float]:
    # Centers
    cxA = (A.xmin + A.xmax) / 2
    cyA = (A.ymin + A.ymax) / 2
    cxB = (B.xmin + B.xmax) / 2
    cyB = (B.ymin + B.ymax) / 2

    dx = cxB - cxA
    dy = cyB - cyA
    dist = math.hypot(dx, dy)
    if dist == 0:
        return (0.0, 0.0)  # Already overlapping or same center

    # Unit vector
    ux = dx / dist
    uy = dy / dist

    # Half-extents
    hwA = (A.xmax - A.xmin) / 2
    hhA = (A.ymax - A.ymin) / 2
    hwB = (B.xmax - B.xmin) / 2
    hhB = (B.ymax - B.ymin) / 2

    # Projected overlap threshold
    proj_extent = abs(ux) * (hwA + hwB) + abs(uy) * (hhA + hhB)

    # Translation needed
    move_dist = dist - proj_extent
    if move_dist < 0:
        move_dist = 0  # Already overlapping

    return (ux * move_dist, uy * move_dist)

def swept_aabb(A: Rect, B: Rect, dx: float, dy: float) -> float | None:
    # Compute entry and exit times along x and y axes
    def axis_sweep(a_min, a_max, b_min, b_max, d):
        if d > 0:
            entry = (b_min - a_max) / d
            exit_ = (b_max - a_min) / d
        elif d < 0:
            entry = (b_max - a_min) / d
            exit_ = (b_min - a_max) / d
        else:
            # No movement along this axis
            if a_max <= b_min or a_min >= b_max:
                return float('inf'), -float('inf')  # no overlap possible
            else:
                return -float('inf'), float('inf')  # always overlapping

        return entry, exit_

    tx_entry, tx_exit = axis_sweep(A.xmin, A.xmax, B.xmin, B.xmax, dx)
    ty_entry, ty_exit = axis_sweep(A.ymin, A.ymax, B.ymin, B.ymax, dy)

    entry_time = max(tx_entry, ty_entry)
    exit_time = min(tx_exit, ty_exit)

    if entry_time > exit_time or entry_time > 1 or entry_time < 0:
        return None  # no collision in [0, 1]
    return entry_time

def move_with_obstacles(moving: Rect, target: Rect, obstacles: list[Rect]):
    dx, dy = movement_to_touch(moving, target)

    lowest_t = 1
    for obs in obstacles:
        t = swept_aabb(moving, obs, dx, dy)
        if t is not None and t < lowest_t:
            lowest_t = t
    
    return (dx * lowest_t, dy * lowest_t)
    ...

def merge_rects(*rects: Rect) -> Rect:
    if not rects:
        raise ValueError("No rectangles to merge")

    xmin = min(r.xmin for r in rects)
    xmax = max(r.xmax for r in rects)
    ymin = min(r.ymin for r in rects)
    ymax = max(r.ymax for r in rects)

    return Rect(xmin, xmax, ymin, ymax)