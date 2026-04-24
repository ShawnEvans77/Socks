from ..constants import guide
from .database import (
    DatabaseError,
    SocksDatabase,
    ValidationError,
    parse_date,
    parse_pay_period,
    parse_year,
)
import re


# ─── ANSI Colors ──────────────────────────────────────────────────────────────

class Color:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    CYAN    = "\033[96m"

def c(text: str, *codes: str) -> str:
    """Wrap text in one or more ANSI color codes."""
    return "".join(codes) + text + Color.RESET

def _visible_len(s: str) -> int:
    """Return the printable length of a string, ignoring ANSI escape codes."""
    return len(re.sub(r"\033\[[0-9;]*m", "", s))

def _pad(s: str, width: int) -> str:
    """Pad a (possibly ANSI-colored) string to a visible width."""
    return s + " " * max(0, width - _visible_len(s))


# ─── Control-Flow Exceptions ──────────────────────────────────────────────────

class GoBack(Exception):
    """Raised when the user types 'b' to cancel the current operation."""

class QuitApp(Exception):
    """Raised when the user types 'q' to exit the application."""


# ─── Wrapper ──────────────────────────────────────────────────────────────────

class Wrapper:
    """SQLite3 wrapper supporting CRUD for payroll_schedule and days_off."""

    def __init__(self):
        self.db = SocksDatabase()

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create_pay_period(self):
        self._header("Pay Period Creation", "CREATE")
        try:
            pay_period = Wrapper.fetch_period("Pay period to add")
            start_str = Wrapper.fetch_date("Start date for this pay period")
            self.db.create_pay_period(pay_period, start_str)
            self._success(f"Pay period {pay_period} added.")

        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    def create_invalid_date(self):
        self._header("Invalid Date Creation", "CREATE")
        try:
            date_str = Wrapper.fetch_date("Invalid date to add")
            self.db.create_invalid_date(date_str)
            self._success(f"Invalid date {date_str} added.")

        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    # ── READ ──────────────────────────────────────────────────────────────────

    def read_pay_period_start_end(self):
        rows = self.db.list_pay_periods()

        h_period = c(" Period ", Color.BOLD)
        h_start  = c(" Start Date ", Color.BOLD)
        h_end    = c(" End Date   ", Color.BOLD)

        border = c("  ┌──────────┬─────────────┬─────────────┐", Color.DIM)
        mid    = c("  ├──────────┼─────────────┼─────────────┤", Color.DIM)
        foot   = c("  └──────────┴─────────────┴─────────────┘", Color.DIM)
        sep    = c("│", Color.DIM)

        print()
        print(c("  Pay Period Schedule", Color.BOLD + Color.CYAN))
        print(border)
        print(f"  {sep}{_pad(h_period,10)}{sep}{_pad(h_start,13)}{sep}{_pad(h_end,13)}{sep}")
        print(mid)

        for row in rows:
            period_s = f" {int(row.pay_period):<8d}"
            start_s  = f" {row.start_date:<11}"
            end_s    = f" {row.end_date:<11}"
            print(f"  {sep}{period_s} {sep}{start_s} {sep}{end_s} {sep}")

        print(foot)
        print()

    def read_invalid_dates(self):
        rows = self.db.list_invalid_dates()

        border = c("  ┌─────────────┐", Color.DIM)
        mid    = c("  ├─────────────┤", Color.DIM)
        foot   = c("  └─────────────┘", Color.DIM)
        sep    = c("│", Color.DIM)

        print()
        print(c("  Invalid Dates", Color.BOLD + Color.CYAN))
        print(border)
        print(f"  {sep}{_pad(c(' Date', Color.BOLD), 13)}{sep}")
        print(mid)

        for row in rows:
            print(f"  {sep} {row:<11} {sep}")

        print(foot)
        print()

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update_pay_period(self):
        self._header("Pay Period Update", "UPDATE")
        try:
            pay_period = Wrapper.fetch_period("Pay period to update")
            start_str = Wrapper.fetch_date(f"New start date for pay period {pay_period}")
            self.db.update_pay_period(pay_period, start_str)
            self._success(f"Pay period {pay_period} updated.")

        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    def update_invalid_date(self):
        self._header("Invalid Date Update", "UPDATE")
        try:
            date_str = Wrapper.fetch_date("Date to change")
            new_str_in = Wrapper.fetch_date(f"Replacement for {c(date_str, Color.YELLOW)}")
            self.db.update_invalid_date(date_str, new_str_in)
            self._success(f"Updated: {date_str} {c('→', Color.DIM)} {new_str_in}")

        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    # ── DELETE ────────────────────────────────────────────────────────────────

    def delete_pay_period(self):
        self._header("Pay Period Deletion", "DELETE")
        try:
            if Wrapper._confirm("Remove all pay periods fully inside a specific year?"):
                year = Wrapper.fetch_year("Year to delete")
                count = self.db.count_pay_periods_in_year(year)

                if count == 0:
                    self._error(f"No pay periods found fully inside {year}.")
                    return

                if Wrapper._confirm(
                    f"Permanently delete {count} pay period(s) fully inside {c(year, Color.YELLOW)}?"
                ):
                    self.db.delete_pay_periods_in_year(year)
                    self._success(f"Deleted {count} pay period(s) fully inside {year}.")
                else:
                    self._cancelled()
                return

            pay_period = Wrapper.fetch_period("Pay period to delete")

            if Wrapper._confirm(f"Permanently delete pay period {c(pay_period, Color.YELLOW)}?"):
                self.db.delete_pay_period(pay_period)
                self._success(f"Pay period {pay_period} deleted.")
            else:
                self._cancelled()

        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    def delete_invalid_date(self):
        self._header("Invalid Date Deletion", "DELETE")
        try:
            if Wrapper._confirm("Remove all invalid dates for a specific year?"):
                year = Wrapper.fetch_year("Year to delete")
                count = self.db.count_invalid_dates_in_year(year)

                if count == 0:
                    self._error(f"No invalid dates found for {year}.")
                    return

                if Wrapper._confirm(
                    f"Permanently delete {count} invalid date(s) from {c(year, Color.YELLOW)}?"
                ):
                    self.db.delete_invalid_dates_in_year(year)
                    self._success(f"Deleted {count} invalid date(s) from {year}.")
                else:
                    self._cancelled()
                return

            date_str = Wrapper.fetch_date("Invalid date to delete")

            if Wrapper._confirm(f"Permanently delete invalid date {c(date_str, Color.YELLOW)}?"):
                self.db.delete_invalid_date(date_str)
                self._success(f"Invalid date {date_str} deleted.")
            else:
                self._cancelled()

        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    # ─── Static Input Helpers ─────────────────────────────────────────────────

    @staticmethod
    def fetch_period(prompt: str) -> str:
        """Prompt for a pay period (1–26). Raises GoBack or QuitApp on escape."""
        first = guide.PeriodLength.first_period.value
        last  = guide.PeriodLength.last_period.value

        while True:
            raw = Wrapper._prompt(prompt, hint=f"{first}–{last}")

            if raw == "b":
                raise GoBack
            if raw == "q":
                raise QuitApp
            try:
                return parse_pay_period(raw, first, last)
            except ValidationError as exc:
                Wrapper._warn(str(exc))
                continue

    @staticmethod
    def fetch_date(prompt: str) -> str:
        """Prompt for a date in MM/DD/YYYY format. Raises GoBack or QuitApp on escape."""
        while True:
            raw = Wrapper._prompt(prompt, hint="MM/DD/YYYY")

            if raw.lower() == "b":
                raise GoBack
            if raw.lower() == "q":
                raise QuitApp
            try:
                return parse_date(raw)
            except ValidationError as exc:
                Wrapper._warn(str(exc))
                continue

    @staticmethod
    def fetch_year(prompt: str) -> str:
        """Prompt for a four-digit year. Raises GoBack or QuitApp on escape."""
        while True:
            raw = Wrapper._prompt(prompt, hint="YYYY")

            if raw.lower() == "b":
                raise GoBack
            if raw.lower() == "q":
                raise QuitApp
            try:
                return parse_year(raw)
            except ValidationError as exc:
                Wrapper._warn(str(exc))
                continue

    @staticmethod
    def insertable_period(pay_period: str) -> bool:
        try:
            parse_pay_period(pay_period)
        except ValidationError:
            return False
        return True

    @staticmethod
    def _confirm(message: str) -> bool:
        """Ask the user to confirm a destructive action. Returns True only on 'y'."""
        print(f"    {c('⚠  ' + message, Color.YELLOW)}")
        while True:
            raw = input(c("    Confirm [y/n]: ", Color.DIM)).strip().lower()
            if raw in ("y", "yes"):
                return True
            if raw == "q":
                raise QuitApp
            if raw == "b":
                raise GoBack
            if raw in ("n", "no", ""):
                return False
            Wrapper._warn("Please enter y or n.")

    @staticmethod
    def _prompt(label: str, hint: str = "") -> str:
        """Render a styled input prompt with an optional format hint."""
        if hint:
            print(c(f"  ({hint})", Color.DIM))
        return input(c(f"  ▶ {label}: ", Color.CYAN)).strip()

    # ─── Display Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _header(title: str, tag: str):
        tag_color = {
            "CREATE": Color.GREEN,
            "UPDATE": Color.YELLOW,
            "DELETE": Color.RED,
        }.get(tag, Color.CYAN)
        print()
        print(f"  {c(f'[{tag}]', tag_color + Color.BOLD)} {c(title, Color.BOLD)}")
        print(c("  " + "─" * 42, Color.DIM))

    @staticmethod
    def _footer():
        print(c("  " + "─" * 42, Color.DIM))
        print()

    @staticmethod
    def _success(msg: str):
        print(f"\n    {c('✔  ' + msg, Color.GREEN)}")

    @staticmethod
    def _error(msg: str):
        print(f"\n    {c('✘  ' + msg, Color.RED)}")

    @staticmethod
    def _warn(msg: str):
        print(f"    {c('⚠  ' + msg, Color.YELLOW)}")

    @staticmethod
    def _cancelled():
        print(c("\n    Operation cancelled.", Color.DIM))
