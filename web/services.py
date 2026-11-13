"""Prompt-free timesheet logic shared by the web front end.

Everything here takes plain values and returns plain values (or raises
``ValidationError``), so no request can leak state into another one.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from src.constants.schedule import DAYS_PER_WEEK, WEEKDAYS, weekday_index
from src.objects.clock import Clock
from src.objects.sheet_writer import SheetWriter
from src.utils.database import (
    DATE_FORMAT,
    ValidationError,
    normalize_shift_segments,
    parse_date,
    parse_time,
    time_minutes,
)

MODES = ("normal", "missed", "custom")
_INPUT_TIME = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?")
_INPUT_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


# ─── Time and date conversion ────────────────────────────────────────────────

def time_from_input(value: str | None) -> str:
    """Turn a browser time ("14:15") or typed time ("2:15PM") into Socks format."""

    value = (value or "").strip()
    match = _INPUT_TIME.fullmatch(value)
    if not match:
        return parse_time(value)

    hour, minute = int(match.group(1)), match.group(2)
    meridiem = "AM" if hour < 12 else "PM"
    hour = hour % 12 or 12
    return parse_time(f"{hour}{meridiem}" if minute == "00" else f"{hour}:{minute}{meridiem}")


def time_to_input(value: str | None) -> str:
    """Turn a stored time ("2:15PM") into a browser time value ("14:15")."""

    try:
        minutes = time_minutes(value or "")
    except ValidationError:
        return ""
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def date_from_input(value: str | None, label: str = "Date") -> str:
    """Turn a browser date ("2026-11-13") or typed MM/DD/YYYY into MM/DD/YYYY."""

    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{label} is required.")
    if _INPUT_DATE.fullmatch(value):
        try:
            value = dt.datetime.strptime(value, "%Y-%m-%d").strftime(DATE_FORMAT)
        except ValueError as exc:
            raise ValidationError(f"{label} is not a real calendar date.") from exc
    try:
        return parse_date(value)
    except ValidationError as exc:
        raise ValidationError(f"{label}: {exc}") from exc


def date_to_input(value: str | None) -> str:
    """Turn a stored MM/DD/YYYY date into a browser date value."""

    try:
        return dt.datetime.strptime((value or "").strip(), DATE_FORMAT).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def parse_intervals(start1, end1, start2, end2) -> tuple[tuple[str, str], ...]:
    """Validate up to two start/end pairs. All blank means no work."""

    raw = [(value or "").strip() for value in (start1, end1, start2, end2)]
    first, second = raw[:2], raw[2:]

    if any(first) != all(first) or any(second) != all(second):
        raise ValidationError("Each shift needs both a start time and an end time.")
    if any(second) and not any(first):
        raise ValidationError("Fill in the first shift before adding a second one.")

    segments = [
        (time_from_input(start), time_from_input(end))
        for start, end in (first, second)
        if start
    ]
    return normalize_shift_segments(segments)


def format_shifts(segments) -> str:
    return ", then ".join(f"{start} – {end}" for start, end in segments)


def format_hours(hours: float) -> str:
    return f"{hours:g}"


# ─── Names ───────────────────────────────────────────────────────────────────

def normalized_name(name: str) -> str:
    return " ".join((name or "").split()).casefold()


def find_employee(employees, name: str):
    target = normalized_name(name)
    if not target:
        return None
    return next(
        (employee for employee in employees if normalized_name(employee.name) == target),
        None,
    )


def split_name(name: str) -> tuple[str, str]:
    """Return (first, last); everything before the final word is the first name."""

    parts = name.split()
    if len(parts) < 2:
        return "", "".join(parts)
    return " ".join(parts[:-1]), parts[-1]


def timesheet_file_name(name: str, pay_period: int) -> str:
    _, last = split_name(name)
    safe_last = re.sub(r"[^\w-]", "", last) or "Employee"
    return f"{safe_last.capitalize()}_Timesheet_{int(pay_period)}.pdf"


# ─── Pay periods ─────────────────────────────────────────────────────────────

def current_pay_period(pay_table, today: dt.date | None = None) -> int | None:
    """Return the pay period containing today, including its final day."""

    today = today or dt.date.today()
    for pay_period, (start, end) in sorted(pay_table.get_pay_dict().items()):
        if start.date() <= today <= end.date():
            return int(pay_period)
    return None


# ─── The fourteen days of a timesheet ────────────────────────────────────────

@dataclass
class Day:
    index: int
    date: dt.datetime
    scheduled: tuple[tuple[str, str], ...]
    is_holiday: bool
    mode: str = "normal"
    skipped: set[int] = field(default_factory=set)
    custom: list[str] = field(default_factory=lambda: ["", "", "", ""])
    error: str = ""
    worked: tuple[tuple[str, str], ...] = ()
    hours: float = 0

    @property
    def weekday(self) -> str:
        return WEEKDAYS[weekday_index(self.date)]

    @property
    def date_text(self) -> str:
        return self.date.strftime("%m/%d")

    @property
    def is_split(self) -> bool:
        return len(self.scheduled) > 1

    @property
    def works_by_default(self) -> bool:
        return bool(self.scheduled) and not self.is_holiday

    @property
    def scheduled_text(self) -> str:
        return format_shifts(self.scheduled)

    @property
    def worked_text(self) -> str:
        return format_shifts(self.worked)

    @property
    def hours_text(self) -> str:
        return format_hours(self.hours)


@dataclass
class Changes:
    """One timesheet's exceptions to the saved weekly schedule."""

    missed_days: set = field(default_factory=set)
    missed_split_shifts: dict = field(default_factory=dict)
    extra_days: dict = field(default_factory=dict)


@dataclass
class Summary:
    week_totals: list[float]
    total: float

    @property
    def week_texts(self) -> list[str]:
        return [format_hours(total) for total in self.week_totals]

    @property
    def total_text(self) -> str:
        return format_hours(self.total)


def build_days(pay_table, schedule, pay_period: int) -> list[Day]:
    invalid_dates = set(pay_table.get_invalid_dates())
    return [
        Day(
            index=index,
            date=date,
            scheduled=tuple(tuple(segment) for segment in schedule[weekday_index(date)]),
            is_holiday=date in invalid_dates,
        )
        for index, date in enumerate(pay_table.get_period_dates(pay_period))
    ]


def apply_form(days: list[Day], form) -> tuple[Changes, bool]:
    """Read each day's choice from a submitted form. Returns (changes, ok)."""

    changes = Changes()
    ok = True

    for day in days:
        i = day.index
        mode = form.get(f"mode_{i}", "normal")
        day.mode = mode if mode in MODES else "normal"
        if day.mode == "missed" and not day.works_by_default:
            day.mode = "normal"  # nothing was scheduled, so there is nothing to miss
        day.custom = [
            (form.get(f"{key}_{i}") or "").strip()
            for key in ("start1", "end1", "start2", "end2")
        ]
        day.skipped = {
            number for number in range(len(day.scheduled))
            if form.get(f"skip_{i}_{number}")
        }

        if day.mode == "missed":
            changes.missed_days.add(day.date)
        elif day.mode == "custom":
            try:
                segments = parse_intervals(*day.custom)
                if not segments:
                    raise ValidationError("Enter the hours you worked on this day.")
            except ValidationError as exc:
                day.error = str(exc)
                ok = False
            else:
                changes.extra_days[day.date] = segments
        elif day.is_split and day.works_by_default and day.skipped:
            changes.missed_split_shifts[day.date] = {
                day.scheduled[number] for number in day.skipped
            }

    return changes, ok


def summarize(days: list[Day], changes: Changes) -> Summary:
    """Work out each day's hours exactly the way the PDF writer does."""

    invalid_dates = {day.date for day in days if day.is_holiday}
    week_totals = [0.0] * max(1, -(-len(days) // DAYS_PER_WEEK))

    for day in days:
        segments, worked = SheetWriter._segments_for_date(
            day.date,
            day.scheduled,
            invalid_dates,
            changes.missed_days,
            changes.missed_split_shifts,
            changes.extra_days,
        )
        if not worked:
            day.worked, day.hours = (), 0
            continue
        day.worked = tuple(segments)
        day.hours = round(
            sum(Clock(start) - Clock(end) for start, end in segments), 2
        )
        week_totals[day.index // DAYS_PER_WEEK] += day.hours

    return Summary(week_totals, sum(week_totals))


def generate_timesheet(
    template_pdf, employee, pay_period: int, pay_table, schedule_table, changes: Changes
) -> bytes:
    """Fill in the PDF template and return the finished timesheet."""

    schedule_table.add_missed_days(employee.name, set(changes.missed_days))
    schedule_table.add_missed_split_shifts(employee.name, changes.missed_split_shifts)
    schedule_table.add_extra_days(employee.name, changes.extra_days)

    first, last = split_name(employee.name)
    sheet = SheetWriter(
        str(template_pdf), last, first, int(pay_period), employee.emplid or "",
        pay_table=pay_table, schedule_table=schedule_table,
    )
    sheet.name = employee.name
    sheet.write_timesheet()
    return sheet.to_bytes()
