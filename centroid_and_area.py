from svgpathtools import svg2paths2, parse_path, Path
from xml.etree import ElementTree as ET
from typing import Iterator
import os

def path_centroid(path: Path, num_samples: int = 1000) -> complex:
    points = [path.point(i / num_samples) for i in range(num_samples)]
    area = 0
    cx = 0
    cy = 0
    for i in range(len(points)):
        x0, y0 = points[i].real, points[i].imag
        x1, y1 = points[(i + 1) % len(points)].real, points[(i + 1) % len(points)].imag
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area *= 0.5
    if area == 0:
        raise ValueError("Degenerate path with zero area")
    cx /= (6 * area)
    cy /= (6 * area)
    return complex(cx, cy)

def centroid_of_path_element(full_path: Path, epsilon: float = 0) -> complex | None:
    """
    Returns the area-weighted centroid of all closed continuous subpaths
    in the given <path> element. Returns None if no closed subpaths exist.
    """
    # d_attr = path_elem.get('d')
    # if not d_attr:
    #     return None
    
    entries: list[tuple[complex, float]] = []

    for subpath in full_path.continuous_subpaths():
        if not subpath.isclosed():
            continue

        # n_subpaths += 1
        points = [subpath.point(i / 1000) for i in range(1000)]
        area = 0
        cx = 0
        cy = 0

        for i in range(len(points)):
            x0, y0 = points[i].real, points[i].imag
            x1, y1 = points[(i + 1) % len(points)].real, points[(i + 1) % len(points)].imag
            cross = x0 * y1 - x1 * y0
            area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross
        
        area *= 0.5
        if area == 0:
            continue

        cx /= (6 * area)
        cy /= (6 * area)

        entries.append((complex(cx, cy), abs(area)))

    if not entries:
        return None

    max_area = max(a for _, a in entries)
    total_weight = 0.0
    weighted_cx = 0.0
    weighted_cy = 0.0

    for c, a in entries:
        weight = a + epsilon * max_area
        weighted_cx += c.real * weight
        weighted_cy += c.imag * weight
        total_weight += weight

    return complex(weighted_cx / total_weight, weighted_cy / total_weight)

def compute_svg_areas(input_svg: str) -> dict[str, float]:
    """
    Parse `input_svg` and return a mapping from each element ID
    (<path> or <g>) to the sum of its path‐areas.
    """
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree = ET.parse(input_svg)
    root = tree.getroot()
    ns   = {'svg': 'http://www.w3.org/2000/svg'}

    # Preserve the SVG namespace
    def area_of_path_d(d: str) -> float:
        full = parse_path(d)
        total = 0.0
        for sub in full.continuous_subpaths():
            # only count subpaths that close on themselves
            if abs(sub.start - sub.end) < 1e-6:
                total += abs(sub.area())
        return total

    id_to_area: dict[str, float] = {}

    # standalone <path>
    for el in root.findall('.//svg:path', ns):
        pid = el.get('id')
        d   = el.get('d')
        if pid and d:
            id_to_area[pid] = area_of_path_d(d)

    # <g> groups
    for g in root.findall('.//svg:g', ns):
        gid = g.get('id')
        if not gid:
            continue
        total = 0.0
        for el in g.findall('.//svg:path', ns):
            d = el.get('d')
            if d:
                total += area_of_path_d(d)
        id_to_area[gid] = total

    return id_to_area
