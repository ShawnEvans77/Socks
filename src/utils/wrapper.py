from ..constants import guide
from ..constants import schedule as schedule_rules
from .terminal import Color, color as c, pad
from .database import (
    DatabaseError,
    SocksDatabase,
    ValidationError,
    parse_date,
    parse_budget,
    parse_emplid,
    parse_pay_period,
    parse_time,
    parse_year,
    normalize_shift_segments,
)

WEEKDAYS = schedule_rules.WEEKDAYS


# ─── Control-Flow Exceptions ──────────────────────────────────────────────────

class GoBack(Exception):
    """Raised when the user types 'b' to cancel the current operation."""

class QuitApp(Exception):
    """Raised when the user types 'exit()' to quit from any prompt."""


# ─── Wrapper ──────────────────────────────────────────────────────────────────

class Wrapper:
    """Terminal CRUD wrapper for payroll data and employee schedules."""

    def __init__(self):
        self.db = SocksDatabase()
        self.db.ensure_schema()

    @staticmethod
    def _normalized_name(name: str) -> str:
        return " ".join(name.split()).casefold()

    @classmethod
    def _find_employee(cls, employees, name: str):
        normalized_name = cls._normalized_name(name)
        return next(
            (employee for employee in employees
             if cls._normalized_name(employee.name) == normalized_name),
            None,
        )

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create_pay_period(self):
        self._header("Pay Period Creation", "CREATE")
        try:
            pay_period = Wrapper.fetch_period("Pay period to add")
            start_str = Wrapper.fetch_date("Start date for this pay period")
            due_date = Wrapper.fetch_date("Timesheet due in payroll")
            pay_date = Wrapper.fetch_date("Pay date")
            self.db.create_pay_period(pay_period, start_str, due_date, pay_date)
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

    def create_employee(self):
        self._header("Employee Creation", "CREATE")
        try:
            employees = self.db.list_employees()
            while True:
                first = Wrapper._prompt("First name")
                if first.lower() == "b":
                    raise GoBack
                last = Wrapper._prompt("Last name")
                if last.lower() == "b":
                    raise GoBack
                if not first.strip() or not last.strip():
                    self._warn("Enter both a first and last name.")
                    continue

                name = " ".join(f"{first.strip()} {last.strip()}".split())
                if self._find_employee(employees, name):
                    self._warn(f"An employee named {name} already exists.")
                    continue
                break

            while True:
                raw_emplid = Wrapper._prompt("EMPLID", hint="Required; digits only")
                if raw_emplid.lower() == "b":
                    raise GoBack
                try:
                    emplid = parse_emplid(raw_emplid)
                except ValidationError as exc:
                    self._warn(str(exc))
                    continue
                if any(employee.emplid == emplid for employee in employees):
                    self._warn(f"EMPLID {emplid} is already assigned to another employee.")
                    continue
                break

            budget = Wrapper.fetch_budget("Department budget")

            print("\n    Build the weekly schedule, Sunday through Saturday.")
            schedule = []
            for index, weekday in enumerate(WEEKDAYS, start=1):
                print(f"\n    {weekday} ({index} of 7)")
                schedule.append(Wrapper._prompt_day_schedule(weekday))

            while True:
                Wrapper._print_schedule_summary(name, schedule)
                choice = Wrapper._prompt(
                    "Save employee or revise a weekday",
                    hint="Save, or revise: Sun, Mon, Tue, Wed, Thu, Fri, Sat; b cancels",
                )
                normalized_choice = " ".join(choice.split()).casefold()
                if normalized_choice == "b":
                    raise GoBack
                if normalized_choice == "save":
                    break

                weekdays = schedule_rules.weekday_aliases()
                weekday_index = weekdays.get(normalized_choice)
                if weekday_index is None:
                    self._warn("Enter Save or a weekday name/abbreviation shown above.")
                    continue

                weekday = WEEKDAYS[weekday_index]
                print(f"\n    Revising {weekday}.")
                schedule[weekday_index] = Wrapper._prompt_day_schedule(weekday)

            employee = self.db.create_employee(name, schedule, emplid, budget)
            cache = guide.Tables.schedule_table.value
            cache.add_employee(employee)
            self._success(
                f"Employee {employee.name} added with EMPLID {employee.emplid} "
                f"and budget {employee.budget}."
            )

        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    @staticmethod
    def _prompt_day_schedule(weekday: str) -> list[list[str]]:
        if not Wrapper._yes_no(f"Does this employee work {weekday}?"):
            return []

        while True:
            first_start = Wrapper.fetch_time("First start time")
            first_end = Wrapper.fetch_time("First end time")
            segments = [(first_start, first_end)]
            if Wrapper._yes_no("Add a second interval?"):
                second_start = Wrapper.fetch_time("Second start time")
                second_end = Wrapper.fetch_time("Second end time")
                segments.append((second_start, second_end))

            try:
                return [list(segment) for segment in normalize_shift_segments(segments)]
            except ValidationError as exc:
                Wrapper._warn(str(exc))
                Wrapper._warn(f"Re-enter {weekday}'s intervals.")

    @staticmethod
    def _print_schedule_summary(name: str, schedule) -> None:
        print(f"\n  Weekly schedule for {name}")
        for weekday, segments in zip(WEEKDAYS, schedule):
            shift = ", then ".join(f"{start} - {end}" for start, end in segments) or "Off"
            print(f"    {pad(weekday, 10)} {shift}")

    # ── READ ──────────────────────────────────────────────────────────────────

    def read_pay_period_start_end(self):
        rows = self.db.list_pay_periods()

        h_period = c(" Period ", Color.BOLD)
        h_start  = c(" Start Date ", Color.BOLD)
        h_end    = c(" End Date   ", Color.BOLD)
        h_due    = c(" Due Date    ", Color.BOLD)
        h_pay    = c(" Pay Date    ", Color.BOLD)

        border = c("  ┌──────────┬─────────────┬─────────────┬─────────────┬─────────────┐", Color.DIM)
        mid    = c("  ├──────────┼─────────────┼─────────────┼─────────────┼─────────────┤", Color.DIM)
        foot   = c("  └──────────┴─────────────┴─────────────┴─────────────┴─────────────┘", Color.DIM)
        sep    = c("│", Color.DIM)

        print()
        print(c("  Pay Period Schedule", Color.BOLD + Color.CYAN))
        print(border)
        print(
            f"  {sep}{pad(h_period,10)}{sep}{pad(h_start,13)}{sep}"
            f"{pad(h_end,13)}{sep}{pad(h_due,13)}{sep}{pad(h_pay,13)}{sep}"
        )
        print(mid)

        for row in rows:
            period_s = f" {int(row.pay_period):<8d}"
            start_s  = f" {row.start_date:<11}"
            end_s    = f" {row.end_date:<11}"
            due_s    = f" {row.due_date:<11}"
            pay_s    = f" {row.pay_date:<11}"
            print(f"  {sep}{period_s} {sep}{start_s} {sep}{end_s} {sep}{due_s} {sep}{pay_s} {sep}")

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
        print(f"  {sep}{pad(c(' Date', Color.BOLD), 13)}{sep}")
        print(mid)

        for row in rows:
            print(f"  {sep} {row:<11} {sep}")

        print(foot)
        print()

    def read_employee_names_and_emplids(self):
        employees = self.db.list_employees()
        if not employees:
            print(c("\n  No employee records.\n", Color.DIM))
            return

        name_width = max(len("Employee"), *(len(employee.name) for employee in employees))
        id_width = max(
            len("EMPLID"), *(len(employee.emplid or "NOT SET") for employee in employees)
        )
        budget_width = max(len("Budget"), *(len(str(employee.budget)) for employee in employees))
        border = (
            f"  ┌{'─' * (name_width + 2)}┬{'─' * (id_width + 2)}"
            f"┬{'─' * (budget_width + 2)}┐"
        )
        middle = (
            f"  ├{'─' * (name_width + 2)}┼{'─' * (id_width + 2)}"
            f"┼{'─' * (budget_width + 2)}┤"
        )
        footer = (
            f"  └{'─' * (name_width + 2)}┴{'─' * (id_width + 2)}"
            f"┴{'─' * (budget_width + 2)}┘"
        )

        print()
        print(c("  Employees", Color.BOLD + Color.CYAN))
        print(c(border, Color.DIM))
        print(
            f"  │ {pad(c('Employee', Color.BOLD), name_width)} │ "
            f"{pad(c('EMPLID', Color.BOLD), id_width)} │ "
            f"{pad(c('Budget', Color.BOLD), budget_width)} │"
        )
        print(c(middle, Color.DIM))
        for employee in employees:
            emplid = employee.emplid or "NOT SET"
            print(
                f"  │ {pad(employee.name, name_width)} │ {pad(emplid, id_width)} │ "
                f"{pad(str(employee.budget), budget_width)} │"
            )
        print(c(footer, Color.DIM))
        print()

    def read_employee_schedules(self):
        employees = self.db.list_employees()
        if not employees:
            print(c("\n  No employee schedules.\n", Color.DIM))
            return

        print()
        print(c("  Employee Schedules", Color.BOLD + Color.CYAN))
        for employee in employees:
            emplid = employee.emplid or "NOT SET"
            print(
                f"\n  {c(employee.name, Color.BOLD)}  "
                f"{c(f'EMPLID: {emplid} | Budget: {employee.budget}', Color.DIM)}"
            )
            for weekday, segments in zip(WEEKDAYS, employee.schedule):
                shift = ", then ".join(
                    f"{start} - {end}" for start, end in segments
                ) or "Off"
                print(f"    {pad(weekday, 10)} {shift}")
        print()

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update_pay_period(self):
        self._header("Pay Period Update", "UPDATE")
        try:
            pay_period = Wrapper.fetch_period("Pay period to update")
            start_str = Wrapper.fetch_date(f"New start date for pay period {pay_period}")
            due_date = Wrapper.fetch_date("New timesheet due date")
            pay_date = Wrapper.fetch_date("New pay date")
            self.db.update_pay_period(pay_period, start_str, due_date, pay_date)
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

    def update_employee_schedule(self):
        self._header("Employee Schedule Update", "UPDATE")
        try:
            employees = self.db.list_employees()
            if not employees:
                self._error("No employee records are available.")
                return

            employee = self._select_employee(employees)

            print("\n    Valid weekdays: " + ", ".join(
                f"{day} ({day[:3]})" for day in WEEKDAYS
            ) + ".")
            weekday = Wrapper.fetch_weekday("Weekday to update")
            weekday_name = WEEKDAYS[weekday]
            current = employee.schedule[weekday]
            current_text = ", then ".join(
                f"{start} - {end}" for start, end in current
            ) or "Off"
            print(f"\n    Weekday selected: {weekday_name}.")
            print(f"    Current recurring {weekday_name} schedule: {current_text}")
            print(f"    This change applies to every {weekday_name} for this employee.")

            split = Wrapper._yes_no("Is this a split schedule?")
            while True:
                start = Wrapper.fetch_time(
                    "First start time, or OFF to clear this weekday", allow_off=True
                )
                if start is None:
                    segments = []
                else:
                    end = Wrapper.fetch_time("First end time")
                    segments = [(start, end)]
                    if split:
                        second_start = Wrapper.fetch_time("Second start time")
                        second_end = Wrapper.fetch_time("Second end time")
                        segments.append((second_start, second_end))

                try:
                    self.db.set_employee_schedule(employee.name, weekday, segments)
                    break
                except ValidationError as exc:
                    self._warn(str(exc))
                    self._warn("Please re-enter the intervals for this weekday.")

            cache = guide.Tables.schedule_table.value
            if cache.has_name(employee.name):
                cache.schedule_dict[employee.name.lower()][weekday] = [
                    list(segment) for segment in segments
                ]

            updated = ", then ".join(
                f"{start} - {end}" for start, end in segments
            ) or "Off"
            self._success(f"{weekday_name} schedule updated: {updated}.")

        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    def update_employee_budget(self):
        self._header("Employee Budget Update", "UPDATE")
        try:
            employees = self.db.list_employees()
            if not employees:
                self._error("No employee records are available.")
                return

            employee = self._select_employee(employees)
            budget = Wrapper.fetch_budget("New department budget")
            cache = guide.Tables.schedule_table.value
            if cache.has_name(employee.name):
                budget = cache.set_budget(employee.name, budget)
            else:
                budget = self.db.set_employee_budget(employee.name, budget)
            self._success(
                f"{employee.name}'s department number is now "
                f"{guide.LearningCenter.lc_dept_prefix.value}-{budget}."
            )
        except GoBack:
            self._cancelled()
        except DatabaseError as exc:
            self._error(str(exc))
        finally:
            self._footer()

    def _select_employee(self, employees):
        self.read_employee_names_and_emplids()
        while True:
            raw = Wrapper._prompt(
                "Employee name", hint="First and last name; capitalization does not matter"
            )
            if raw.lower() == "b":
                raise GoBack
            employee = self._find_employee(employees, raw)
            if employee is not None:
                return employee
            self._warn("Enter an employee's first and last name as shown in the table.")

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
        """Prompt for a configured pay period. Raises GoBack or QuitApp on escape."""
        first = guide.PeriodLength.first_period.value
        last  = guide.PeriodLength.last_period.value

        while True:
            raw = Wrapper._prompt(prompt, hint=f"{first}–{last}")
            command = raw.lower()

            if command == "b":
                raise GoBack
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
            try:
                return parse_date(raw)
            except ValidationError as exc:
                Wrapper._warn(str(exc))
                continue

    @staticmethod
    def fetch_weekday(prompt: str) -> int:
        """Prompt for a weekday, accepting full names or 3-letter forms."""
        aliases = schedule_rules.weekday_aliases()
        while True:
            raw = Wrapper._prompt(prompt, hint="Full weekday name or 3-letter abbreviation")
            if raw.lower() == "b":
                raise GoBack
            weekday = aliases.get(raw.casefold())
            if weekday is not None:
                return weekday
            Wrapper._warn("Enter a weekday such as Monday or Mon.")

    @staticmethod
    def fetch_time(prompt: str, allow_off: bool = False) -> str | None:
        """Prompt for a validated 12-hour time, optionally accepting OFF."""
        hint = "12-hour time, such as 9AM or 2:15PM"
        if allow_off:
            hint += "; enter OFF to clear the weekday"
        while True:
            raw = Wrapper._prompt(prompt, hint=hint)
            if raw.lower() == "b":
                raise GoBack
            if allow_off and raw.upper() == "OFF":
                return None
            try:
                return parse_time(raw)
            except ValidationError as exc:
                Wrapper._warn(str(exc))

    @staticmethod
    def fetch_budget(prompt: str) -> int:
        """Prompt for a numeric department budget."""
        while True:
            raw = Wrapper._prompt(
                prompt,
                hint=f"Digits only; final department number is "
                f"{guide.LearningCenter.lc_dept_prefix.value}-<budget>",
            )
            if raw.lower() == "b":
                raise GoBack
            try:
                return parse_budget(raw)
            except ValidationError as exc:
                Wrapper._warn(str(exc))

    @staticmethod
    def _yes_no(prompt: str) -> bool:
        while True:
            raw = Wrapper._prompt(prompt, hint="y / n").lower()
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no"):
                return False
            if raw == "b":
                raise GoBack
            Wrapper._warn("Please enter y or n.")

    @staticmethod
    def fetch_year(prompt: str) -> str:
        """Prompt for a four-digit year. Raises GoBack or QuitApp on escape."""
        while True:
            raw = Wrapper._prompt(prompt, hint="YYYY")

            if raw.lower() == "b":
                raise GoBack
            try:
                return parse_year(raw)
            except ValidationError as exc:
                Wrapper._warn(str(exc))
                continue

    @staticmethod
    def _confirm(message: str) -> bool:
        """Ask the user to confirm a destructive action. Returns True only on 'y'."""
        print(f"    {c('⚠  ' + message, Color.YELLOW)}")
        while True:
            raw = input(c("    Confirm [y/n]: ", Color.DIM)).strip().lower()
            if raw == "exit()":
                raise QuitApp
            if raw in ("y", "yes"):
                return True
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
        raw = input(c(f"  ▶ {label}: ", Color.CYAN)).strip()
        if raw.casefold() == "exit()":
            raise QuitApp
        return raw

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
