"""Parse raw line amounts."""


def parse_amount(raw):
    """Parse a raw dollar amount into a number."""
    return int(float(raw))
