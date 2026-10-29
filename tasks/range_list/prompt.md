# expand — expand a compact range list

Build a command-line program at **`src/expand.py`**. It reads one line from
**stdin**: a comma-separated list of items, where each item is either a single
integer or a range `a-b`. Print all the integers, space-separated, on one line, in
the order the items appear.

    python src/expand.py

A range `a-b` expands to every integer **from a to b inclusive**. With empty input,
print nothing.

## Examples

- `1-3,5,7-9` → `1 2 3 5 7 8 9`
- `5` → `5`
- `1-1` → `1`
