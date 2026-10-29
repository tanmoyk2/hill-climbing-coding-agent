Reminders fire at the wrong time for events with a timezone offset.

An event starting at "2026-03-10T09:00:00-05:00" should be 14:00 UTC, but `reminder_hour_utc` (in `src/scheduling/core.py`) reports 9. Events that are already in UTC are fine. Please fix it so reminders use the correct UTC time for any offset.
