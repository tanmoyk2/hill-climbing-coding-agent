"""Reminder timing."""

from datetime import timezone


def to_utc(event):
    """Return the event's start time as a UTC-aware datetime.

    A timezone-aware start is converted to UTC; a naive start is assumed to
    already be UTC.
    """
    start = event["start"]
    if start.tzinfo is None:
        return start.replace(tzinfo=timezone.utc)
    return start.astimezone(timezone.utc)


def reminder_hour_utc(event):
    """The UTC hour at which to fire the event's reminder."""
    return to_utc(event).hour
