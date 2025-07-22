import csv
from typing import cast

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


def apportionment_to_dicts(
    state_abbrs: list[str],
    data: list[list[int | None]]
) -> list[dict[str, int]]:
    return [
        {state: val for state, val in zip(state_abbrs, row) if val is not None}
        for row in data
    ]

def create_ev_dict(nth_app: int):
    data = csv_to_typed_list('ev.csv')

    states_title = cast(list[str], data[0])
    table = cast(Table[int | None], data[1:])

    apportionment_dictionary = apportionment_to_dicts(states_title, table)

    id_to_ev: dict[str, int] = apportionment_dictionary[nth_app]   
    return id_to_ev
