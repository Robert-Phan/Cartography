from collections import namedtuple
from typing import Tuple, Optional, List, NamedTuple, cast
import math
from centroid_and_area import centroid_of_path
from svgpathtools import svg2paths2, parse_path, Path, path_encloses_pt
import copy


type Coord = tuple[float, float]

class Rect(NamedTuple):
    xmin: float
    xmax: float
    ymin: float
    ymax: float

# def movement_to_touch(A: Rect, B: Rect) -> tuple[float, float]:
#     # Centers
#     cxA = (A.xmin + A.xmax) / 2
#     cyA = (A.ymin + A.ymax) / 2
#     cxB = (B.xmin + B.xmax) / 2
#     cyB = (B.ymin + B.ymax) / 2

#     dx = cxB - cxA
#     dy = cyB - cyA
#     dist = math.hypot(dx, dy)
#     if dist == 0:
#         return (0.0, 0.0)  # Already overlapping or same center

#     # Unit vector
#     ux = dx / dist
#     uy = dy / dist

#     # Half-extents
#     hwA = (A.xmax - A.xmin) / 2
#     hhA = (A.ymax - A.ymin) / 2
#     hwB = (B.xmax - B.xmin) / 2
#     hhB = (B.ymax - B.ymin) / 2

#     # Projected overlap threshold
#     proj_extent = abs(ux) * (hwA + hwB) + abs(uy) * (hhA + hhB)

#     # Translation needed
#     move_dist = dist - proj_extent
#     if move_dist < 0:
#         move_dist = 0  # Already overlapping

#     return (ux * move_dist, uy * move_dist)

def move_to_target(rect: Rect, target: Coord):
    cx, cy = (rect.xmin + rect.xmax) / 2, (rect.ymin + rect.ymax) / 2
    tx, ty = target
    return tx - cx, ty - cy

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

def combine_path(paths: list[Path]):

    combined_d = ""

    for path in paths:
        d: str = path.d() #type:ignore
        combined_d += d
    
    combined_path = parse_path(combined_d)

    return combined_path

def move_with_obstacles2(path: Path, centroid: complex, target: complex, obstacles: list[Path], epsilon: int = 10):    

    dir_vector = target - centroid
    dist = math.hypot(dir_vector.real, dir_vector.imag)
    step_vector = dir_vector / dist

    moving = copy.deepcopy(path)

    relevant_obstacles = []
    for obs in obstacles:
        A = Rect(*path.bbox())
        B = Rect(*obs.bbox())

        t = swept_aabb(A, B, dir_vector.real, dir_vector.imag)
        if t is not None:
            relevant_obstacles.append(obs)
    
    combined_obstacles = combine_path(relevant_obstacles)

    low = 0
    high = dist

    while high - low > epsilon:
        mid = (high + low) / 2
        
        new_moving = cast(Path, moving.translated(step_vector * mid))
        if new_moving is None:
            break
        
        intersects = combined_obstacles.intersect(new_moving)

        if intersects:
            high = mid
        else:
            low = mid

    return low * step_vector

def move_with_obstacles(moving: Rect, target: Coord, obstacles: list[Rect]):
    dx, dy = move_to_target(moving, target)

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