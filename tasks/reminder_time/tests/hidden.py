import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from scheduling import parse_event, to_utc, reminder_hour_utc
import scheduling as _m

def h(raw):
    return reminder_hour_utc(parse_event(raw))

assert h({"title": "A", "start": "2026-03-10T09:00:00-05:00"}) == 14
assert h({"title": "B", "start": "2026-03-10T08:00:00+02:00"}) == 6
assert h({"title": "C", "start": "2026-03-10T12:00:00+00:00"}) == 12
assert h({"title": "D", "start": "2026-03-10T23:30:00-05:00"}) == 4
print("ALL TESTS PASSED")
