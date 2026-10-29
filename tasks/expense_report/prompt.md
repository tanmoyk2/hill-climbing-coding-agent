# ledger — an expense-report CLI

Build a command-line program at **`src/ledger.py`**. It reads expense records from
**stdin** and answers a query given as command-line arguments.

    python src/ledger.py <command> [args]

## Input

One record per line: `date,category,amount` where `date` is `YYYY-MM-DD`,
`category` is text, and `amount` is a decimal number (it may be negative and may
have more than two decimal places). Ignore blank lines.

If any non-blank line is malformed — not exactly three comma-separated fields, or
an `amount` that is not a number — print an error to **stderr** and exit `2`
(whatever the command).

## Money formatting

Every money amount you print uses **exactly two decimals, rounded half-up**
(so `5.005` prints as `5.01`, not `5.00`).

## Commands

- `total` — sum of all amounts.
- `count` — number of records (an integer).
- `average` — mean of all amounts; with no records, print `0.00`.
- `categories` — one line `name: amount` per category (amounts summed), ordered by
  amount **descending**, ties broken by category **name ascending**.
- `top N` — like `categories` but only the first `N` lines (`N` is an argument).
- `category NAME` — the summed total for `NAME`. If there is no such category,
  print an error to **stderr** and exit `1`.

Any other command, or no command at all, is a usage error: print an error to
**stderr** and exit `2`.

## Examples

For the records:

    2026-01-05,food,10.00
    2026-02-03,food,5.005
    2026-01-20,rent,800

- `total` prints `815.01` (10.00 + 5.005 + 800, the 5.005 rounding half-up).
- `categories` prints:

      rent: 800.00
      food: 15.01

- `category food` prints `15.01`; `category travel` prints nothing and exits `1`.
- with no records, `total` prints `0.00` and `average` prints `0.00`.
