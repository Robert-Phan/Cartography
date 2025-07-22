import csv
from typing import cast, Sequence
import xml.etree.ElementTree as ET
from svgpathtools import svg2paths2, parse_path, Path
import numpy as np
import math
from pprint import pp, pprint
import copy

type Table[T] = list[list[T]]

def convert_value(cell: str) -> int | str | None:
    cell = cell.strip()
    if cell == '':
        return None
    try:
        return int(cell)
    except ValueError:
        return cell

def csv_to_typed_list(path: str) -> Table[int | str | None]:
    with open(path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        return [[convert_value(cell) for cell in row] for row in reader]

data = csv_to_typed_list('ev.csv')

states_title = cast(list[str], data[0])
table = cast(Table[int | None], data[1:])

def apportionment_to_dicts(
    state_abbrs: list[str],
    data: list[list[int | None]]
) -> list[dict[str, int]]:
    return [
        {state: val for state, val in zip(state_abbrs, row) if val is not None}
        for row in data
    ]

apportionment_dictionary = apportionment_to_dicts(states_title, table)

INPUT = "1968.svg"
NTH_APP = 23
print(len(apportionment_dictionary))

id_to_ev: dict[str, int] = apportionment_dictionary[NTH_APP]   

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
            xmin, xmax, ymin, ymax = path.bbox()
            cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

            t = f"translate({cx},{cy}) scale({s}) translate({-cx},{-cy})"
            existing = path_el.get('transform', '')
            path_el.set('transform', f"{existing} {t}".strip())

    # 2. Standalone <path> scaling: if a <path> itself has an ID in id_to_scale
    for path_el in root.findall('.//svg:path', ns):
        path_id = path_el.get('id')
        if path_id not in id_to_scale:
            continue
        
        s = id_to_scale[path_id]
        d = path_el.get('d')
        if not d:
            continue

        path_el_copy = copy.deepcopy(path_el)
        path_el_copy.set('stroke-width', '0.5')
        path_el_copy.set('stroke', 'grey')
        path_el_copy.set('fill', 'none')
        path_el_copy.set('id', path_id + 'c')

        outline_el = root.find(".//svg:*[@id='outlines']", namespaces=ns)
        if outline_el is not None:
            outline_el.insert(0, path_el_copy)

        path = parse_path(d)
        xmin, xmax, ymin, ymax = path.bbox()
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

        t = f"translate({cx},{cy}) scale({s}) translate({-cx},{-cy})"
        existing = path_el.get('transform', '')
        path_el.set('transform', f"{existing} {t}".strip())

    # 4. Move states
    # for path_el in root.findall('.//svg:path', ns):
    #     path_id = path_el.get('id')
    #     if path_id not in id_to_scale:
    #         continue
        
    #     s = id_to_scale[path_id]
    #     d = path_el.get('d')
    #     if not d:
    #         continue

    #     path = parse_path(d)
    #     xmin, xmax, ymin, ymax = path.bbox()
    #     cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

    #     movement_proportion = 0.25
    #     print(path_id, movement_proportion)

    #     dx = ((centerpiece_x - cx) * movement_proportion) 
    #     dy = ((centerpiece_y - cy) * movement_proportion)
    #     print(dx, dy)

    #     t = f"translate({dx},{dy})"
    #     existing = path_el.get('transform', '')
    #     path_el.set('transform', f"{t} {existing}".strip())

        #3. Adjust text
        text_id = f"{path_id}n"
        xpath = f".//svg:text[@id='{text_id}']"
        text_el = root.find(xpath, ns)

        if text_el is None:
            continue

        new_size = 20 * math.sqrt(id_to_norm_ev[path_id])

        text_el.set('font-size', str(new_size))
        text_el.set('x', str(cx - new_size / 2))
        text_el.set('y', str(cy + new_size / 2))

        inner_text = text_el.text
        inner_text = id_to_ev[path_id]
        text_el.text = str(inner_text)

    # write out the modified SVG
    tree.write(output_svg, encoding='utf-8', xml_declaration=True)

scale_svg(INPUT, f'output.svg', id_to_scale)
