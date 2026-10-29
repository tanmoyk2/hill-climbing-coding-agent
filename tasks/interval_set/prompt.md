# intervals — interval-set operations

Build a command-line program at **`src/intervals.py`**. It reads intervals from
**stdin**, one per line as `start end` (two **decimal** numbers with
`start <= end`); the query is the first command-line argument. Ignore blank lines.

    python src/intervals.py <command> [args]

Intervals are **inclusive**. Intervals that overlap **or merely touch** are merged
(so `1 3` and `3 5` merge into `1 5`).

## Commands

- `merge` — the merged intervals, one per line as `start end`, sorted by start.
  Print each coordinate as a plain decimal with **trailing zeros trimmed** (so
  `4.0` prints as `4`, `1.50` as `1.5`).
- `count` — the number of merged intervals.
- `length` — the total length covered (the sum of `end - start` over the merged
  intervals), printed with **exactly two decimals, rounded half-up** (so a total
  of `3.675` prints as `3.68`).
- `covers X` — print `yes` if the decimal `X` lies inside any interval (inclusive),
  otherwise `no`.

A malformed line (not two numbers, or `start > end`) is an input error: print to
**stderr** and exit `2`. Any other command, or no command, is also a usage error:
print to **stderr** and exit `2`.

## Example

For the intervals `0 2.675` and `5 6`:

- `merge` prints `0 2.675` then `5 6`.
- `count` prints `2`.
- `length` prints `3.68` (2.675 + 1 = 3.675, rounded half-up).
- `covers 2` prints `yes`; `covers 4` prints `no`.

(For `1.5 3.5` and `3.5 4.0`, `merge` prints `1.5 4` — they touch, and `4.0` is
trimmed to `4`.)
