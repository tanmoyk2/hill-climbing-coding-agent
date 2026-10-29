"""Invoice reporting."""


def invoice_total(amounts):
    """Return the rounded total of the line `amounts`."""
    return round(sum(amounts), 2)
