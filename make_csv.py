import csv
from typing import List

def is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

def add_two_below_row(input_path: str, output_path: str, n: int) -> None:
    reader: List[List[str]]
    with open(input_path, 'r', newline='', encoding='utf-8') as infile:
        reader = list(csv.reader(infile))

    for row_idx in range(n, len(reader)):
        for col_idx in range(len(reader[row_idx])):
            val = reader[row_idx][col_idx]
            if is_number(val):
                num = float(val)
                new_val = str(int(num + 2)) if num.is_integer() else str(num + 2)
                reader[row_idx][col_idx] = new_val

    with open(output_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(reader)

# Example usage
add_two_below_row('congress.csv', 'ev.csv', n=1)
