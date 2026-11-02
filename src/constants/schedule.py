WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
DAYS_PER_WEEK = len(WEEKDAYS)
DAYS_PER_PAY_PERIOD = DAYS_PER_WEEK * 2


def weekday_index(date) -> int:
    """Return a Sunday-first weekday index for a date-like value."""

    return (date.weekday() + 1) % len(WEEKDAYS)


def weekday_aliases() -> dict[str, int]:
    return {
        alias: index
        for index, day in enumerate(WEEKDAYS)
        for alias in (day.casefold(), day[:3].casefold())
    }
