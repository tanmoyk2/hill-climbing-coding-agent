"""Parse raw events into typed events."""

from datetime import datetime


def parse_event(raw):
    """Parse a raw event (string fields) into a typed event.

    `raw["start"]` is an ISO-8601 timestamp such as "2026-03-10T09:00:00-05:00".
    """
    return {
        "title": raw["title"],
        "start": datetime.fromisoformat(raw["start"]).replace(tzinfo=None),
    }
