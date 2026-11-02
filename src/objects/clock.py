from ..utils.database import parse_time, time_minutes


class Clock:
    """Parse 12-hour times and calculate durations with minute precision."""

    def __init__(self, time_str: str):
        self.time_str = parse_time(time_str)
        self.minutes = time_minutes(self.time_str)

    def __sub__(self, other) -> int | float:
        """Return elapsed hours from this clock time to the other."""
        duration = other.minutes - self.minutes
        hours = round(duration / 60, 2)
        return int(hours) if hours.is_integer() else hours
    
    def __str__(self) -> str:
        return self.time_str
