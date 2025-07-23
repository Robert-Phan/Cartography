import csv
from typing import cast
import xml.etree.ElementTree as ET
from svgpathtools import parse_path, Path
import svgpathtools.path as pathtools 
import math
from move import Rect, movement_to_touch, move_with_obstacles
from ev_dict import create_ev_dict
from centroid_and_area import compute_svg_areas, centroid_of_path_element
import re
from pprint import pprint

INPUT = "1968.svg"
NTH_APP = 23

id_to_ev = create_ev_dict(NTH_APP)

def get_scales(id_to_area: dict[str, float], ev_dict: dict[str, int]):
    max_scale = 0
    id_to_scale = {}

    for (id, area) in id_to_area.items():
        if id not in ev_dict:
            continue
        
        ev = ev_dict[id]

        scale = math.sqrt((ev / area))
        id_to_scale[id] = scale

        if scale > max_scale:
            max_scale = scale
    
    for id in id_to_scale:
        id_to_scale[id] = id_to_scale[id] / max_scale

    return id_to_scale

id_to_area = compute_svg_areas(INPUT)
max_ev = max(id_to_ev.values())
id_to_norm_ev = {k: v / max_ev for k, v in id_to_ev.items()}
id_to_scale = get_scales(id_to_area, id_to_ev) 

def scale_svg(input_svg: str,
              output_svg: str,
              id_to_scale: dict[str, float]) -> None:
    # ensure the SVG namespace is preserved
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    tree = ET.parse(input_svg)
    root = tree.getroot()
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    # 1. Group-level scaling: if a <g> has an ID in id_to_scale,
    #    scale all descendant <path> by that factor (each about its own centre)
    for g in root.findall('.//svg:g', ns):
        group_id = g.get('id')
        if group_id not in id_to_scale:
            continue
            
        s = id_to_scale[group_id]
        for path_el in g.findall('.//svg:path', ns):
            d = path_el.get('d')
            if not d:
                continue

            path = parse_path(d)
            # xmin, xmax, ymin, ymax = path.bbox()
            # cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
            # centroid = path_centroid(path)
            centroid = centroid_of_path_element(path)
            if not centroid:
                continue
            cx, cy = centroid.real, centroid.imag

            t = f"translate({cx},{cy}) scale({s}) translate({-cx},{-cy})"
            existing = path_el.get('transform', '')
            path_el.set('transform', f"{existing} {t}".strip())
    
    id_to_rect: dict[str, Rect] = {}
    id_to_centroid: dict[str, tuple[float, float]] = {}

    target_x: float = 0
    target_y: float = 0

    outline_el = root.find(".//svg:*[@id='outlines']", namespaces=ns)
    if outline_el is None:
        return

    # 2. Standalone <path> scaling: if a <path> itself has an ID in id_to_scale
    for path_el in root.findall('.//svg:path', ns):
        path_id = path_el.get('id')
        if path_id not in id_to_scale:
            continue
        
        s = id_to_scale[path_id]
        d = path_el.get('d')
        if not d:
            continue

        # path_el_copy = copy.deepcopy(path_el)
        # path_el_copy.set('stroke-width', '0.5')
        # path_el_copy.set('stroke', '#4772b8')
        # path_el_copy.set('fill', '#edf1f8')
        # path_el_copy.set('id', path_id + 'c')

        path = parse_path(d)
        centroid = centroid_of_path_element(path)
        if not centroid:
            continue
        cx, cy = centroid.real, centroid.imag

        cc = complex(cx, cy)
        new_path = cast(Path, path.scaled(s, origin=cc))
        d = new_path.d()
        path_el.set('d', d)

        rect = Rect(*new_path.bbox())
        id_to_rect[path_id] = rect
        id_to_centroid[path_id] = cx, cy
        if path_id == 'RI':
            target_x, target_y = cx, cy

        # t = f"translate({cx},{cy}) scale({s}) translate({-cx},{-cy})"
        # existing = path_el.get('transform', '')
        # path_el.set('transform', f"{existing} {t}".strip())

        path_el.set('fill', '#4772b8')
        path_el.set('stroke-width', '0.5')
        path_el.set('stroke', '#325081')
        path_el.set('vector-effect', 'non-scaling-stroke')

    target = id_to_rect['RI']
    id_to_distance = {k: math.hypot(target_x - x, target_y - y) for k, (x, y) in id_to_centroid.items()}
    nearest_to_farthest = sorted(id_to_distance, key=lambda k: id_to_distance[k])

    for i, path_id in enumerate(nearest_to_farthest):
        print(path_id)

        xpath = f".//svg:path[@id='{path_id}']"
        path_el = root.find(xpath, ns)

        if path_el is None:
            continue
        
        moving = id_to_rect[path_id]
        obstacles = [id_to_rect[id] for j, id in enumerate(nearest_to_farthest) if j < i]
        # print(obstacles[-1] if len(obstacles) > 0 else None)

        # dx, dy = movement_to_touch(moving, target)
        dx, dy = move_with_obstacles(moving, target, obstacles)
        
        d = path_el.get('d')
        if not d:
            continue
        path = parse_path(d)
        
        new_path = cast(Path, path.translated(complex(dx, dy)))
        rect = Rect(*new_path.bbox())
        id_to_rect[path_id] = rect
        # print(rect)

        d = new_path.d()
        path_el.set('d', d)

        cx, cy = id_to_centroid[path_id]
        cx, cy = cx + dx, cy + dy

        #3. Adjust text
        text_id = f"{path_id}n"
        xpath = f".//svg:text[@id='{text_id}']"
        text_el = root.find(xpath, ns)

        if text_el is None:
            continue

        inner_text = text_el.text
        if inner_text is None:
            continue

        new_england = re.match(r'^[A-Za-z]{2}', inner_text)
        if new_england:
            inner_text = inner_text[:3]
        else:
            inner_text = ""

        inner_text += str(id_to_ev[path_id])
        text_el.text = str(inner_text)

        text_scale = math.sqrt(id_to_norm_ev[path_id])
        BASE_SIZE = 20
        new_size = BASE_SIZE * text_scale
        digit_len = len(str(id_to_ev[path_id]))
        new_width = (new_size / 2) * digit_len

        text_el.set('font-size', str(new_size))
        text_el.set('stroke', '#325081')
        text_el.set('fill', '#edf1f8')

        if not new_england:
            text_el.set('x', str(cx - new_width / 2))
            text_el.set('y', str(cy + new_size / 2.5))
            text_el.set('stroke-width', f'{0.5 * text_scale}')
        else:
            text_el.set('font-size', str(BASE_SIZE * 0.8))
            text_el.set('stroke-width', f'{0.5}')

    # write out the modified SVG
    tree.write(output_svg, encoding='utf-8', xml_declaration=True)

scale_svg(INPUT, f'output.svg', id_to_scale)
