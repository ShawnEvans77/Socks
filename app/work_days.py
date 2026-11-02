from datetime import datetime

from src.constants import schedule as schedule_rules
from src.objects.clock import Clock
from src.utils.database import DatabaseError, ValidationError, normalize_shift_segments

from . import console


class WorkDaysFlow:
    """Collect one pay period's temporary schedule exceptions."""

    def __init__(self, schedule_table, pay_table):
        self.schedule_table = schedule_table
        self.pay_table = pay_table

    def run(self, first: str, last: str, pay_period: int) -> None:
        console.section(3, 3, "Work Days")
        employee = f"{first} {last}"
        self.schedule_table.add_missed_days(employee, set())
        self.schedule_table.add_missed_split_shifts(employee, {})
        self.schedule_table.add_extra_days(employee, {})

        if not console.yes_no("Any notable changes to account for this week?"):
            console.info("No schedule changes. Using the saved schedule.")
            return

        self.collect_missed_days(employee, pay_period)
        self.collect_missed_split_shifts(employee, pay_period)
        self.collect_extra_days(first, last, pay_period)

    def collect_missed_days(self, employee: str, pay_period: int) -> None:
        if not console.yes_no("Did you miss any days this pay period?"):
            console.info("No missed days. All scheduled days will be included.")
            return

        day_map = self._period_day_map(pay_period)
        self._show_dates("Available days:", day_map)

        while True:
            missed = console.prompt("Missed days (space-separated)").lower().split()
            if not missed:
                console.warn("Enter at least one day, or answer n above to skip.")
                continue

            invalid = set(missed) - day_map.keys()
            if invalid:
                console.warn(
                    f"Unrecognized: {', '.join(sorted(invalid))}. "
                    "Use only the dates listed above."
                )
                continue

            dates = {day_map[date] for date in missed}
            self.schedule_table.add_missed_days(employee, dates)
            dates_text = ", ".join(
                console.color(self.pay_table.date_str(date), console.Color.YELLOW)
                for date in sorted(dates)
            )
            console.success(f"{len(dates)} missed day(s) recorded: {dates_text}")
            return

    def collect_missed_split_shifts(self, employee: str, pay_period: int) -> None:
        schedule = self.schedule_table.get(employee)
        missed_days = self.schedule_table.get_missed_days(employee)
        invalid_dates = set(self.pay_table.get_invalid_dates())
        candidates = []

        for date in self.pay_table.get_period_dates(pay_period):
            shifts = schedule[schedule_rules.weekday_index(date)]
            if len(shifts) > 1 and date not in missed_days and date not in invalid_dates:
                candidates.extend((date, tuple(shift)) for shift in shifts)

        if not candidates:
            return
        if not console.yes_no("Did you miss your split schedule?"):
            console.info("No split shifts missed.")
            return

        console.blank()
        print(console.color("  Split shifts in this pay period:", console.Color.DIM))
        for number, (date, (start, end)) in enumerate(candidates, start=1):
            label = f"{date.strftime('%a %m/%d')}  {start} - {end}"
            number_text = console.color(
                f"{number}.", console.Color.YELLOW, console.Color.BOLD
            )
            print(f"  {number_text} {label}")
        console.blank()

        while True:
            choices = console.prompt("Number(s) of missed shifts (space-separated)").split()
            if not choices or any(
                not choice.isascii() or not choice.isdigit() for choice in choices
            ):
                console.warn("Enter one or more listed numbers.")
                continue
            numbers = [int(choice) for choice in choices]
            if len(numbers) != len(set(numbers)):
                console.warn("Enter each number only once.")
                continue
            if any(number < 1 or number > len(candidates) for number in numbers):
                console.warn(f"Choose numbers from 1 to {len(candidates)}.")
                continue
            break

        missed = {}
        for number in numbers:
            date, shift = candidates[number - 1]
            missed.setdefault(date, set()).add(shift)
        self.schedule_table.add_missed_split_shifts(employee, missed)
        console.success(f"{len(numbers)} missed split shift(s) recorded for this timesheet.")

    def collect_extra_days(self, first: str, last: str, pay_period: int) -> None:
        employee = f"{first} {last}"
        if not console.yes_no("Did you work an extra day or days this pay period?"):
            self.schedule_table.add_extra_days(employee, {})
            console.info("No extra days recorded.")
            return

        day_map = self._period_day_map(pay_period)
        missed_days = self.schedule_table.get_missed_days(employee)
        self._show_dates("Dates in this pay period:", day_map)

        while True:
            dates = console.prompt("Extra work dates (space-separated)").split()
            if not dates:
                console.warn("Enter at least one date, or answer n above to skip.")
                continue

            invalid = set(dates) - day_map.keys()
            if invalid:
                console.warn(
                    f"Unrecognized: {', '.join(sorted(invalid))}. "
                    "Enter dates shown for this pay period."
                )
                continue

            conflicts = [date for date in dates if day_map[date] in missed_days]
            if conflicts:
                console.warn(
                    f"These dates are also marked missed: {', '.join(conflicts)}. "
                    "Remove them or update missed days."
                )
                continue
            if len(set(dates)) != len(dates):
                console.warn("Enter each extra work date only once.")
                continue
            break

        extra_days = {
            day_map[date]: self._collect_extra_day_intervals(date)
            for date in dates
        }
        self.schedule_table.add_extra_days(employee, extra_days)
        console.success(f"Recorded extra work for {len(extra_days)} date(s).")

    def _collect_extra_day_intervals(self, date: str) -> tuple[tuple[str, str], ...]:
        split = console.yes_no(f"Was the extra work on {date} a split schedule?")
        while True:
            shifts = []
            for shift_number in range(1, 3 if split else 2):
                prefix = "" if shift_number == 1 else "Second shift "
                start = self._fetch_work_time(f"{prefix}start time for {date}")
                end = self._fetch_work_time(f"{prefix}end time for {date}")
                shifts.append((start, end))
            try:
                return normalize_shift_segments(shifts)
            except ValidationError as exc:
                console.warn(f"{exc} Enter this day's times again.")

    @staticmethod
    def _fetch_work_time(label: str) -> str:
        while True:
            raw = console.prompt(
                label, hint="12-hour time, such as 9AM, 2:15PM, or 2:15 PM"
            ).upper()
            try:
                return Clock(raw).time_str
            except (ValueError, DatabaseError):
                console.warn("Enter a valid time such as 9AM or 2:15PM.")

    def _period_day_map(self, pay_period: int) -> dict[str, datetime]:
        return {
            self.pay_table.date_str(date): date
            for date in self.pay_table.get_period_dates(pay_period)
        }

    @staticmethod
    def _show_dates(label: str, day_map: dict[str, datetime]) -> None:
        console.blank()
        print(console.color(f"  {label}", console.Color.DIM))
        print(
            "  " + console.color(" | ", console.Color.DIM).join(
                console.color(date, console.Color.YELLOW, console.Color.BOLD)
                for date in day_map
            )
        )
        console.blank()
