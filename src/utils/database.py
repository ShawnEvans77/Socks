from ..constants import filenames
from contextlib import contextmanager
from dataclasses import dataclass
import datetime as d
import re
import sqlite3


DATE_FORMAT = "%m/%d/%Y"
YEAR_PATTERN = r"(19|20)\d\d"
TIME_PATTERN = r"(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*(AM|PM)"


class DatabaseError(Exception):
    """Base exception for database service failures."""


class ValidationError(DatabaseError):
    """Raised when user-provided data is invalid."""


class DuplicateError(DatabaseError):
    """Raised when a unique database value already exists."""


class NotFoundError(DatabaseError):
    """Raised when a requested row does not exist."""


@dataclass(frozen=True)
class PayPeriod:
    pay_period: str
    start_date: str
    end_date: str
    due_date: str
    pay_date: str


@dataclass(frozen=True)
class Employee:
    name: str
    emplid: str | None
    schedule: tuple[tuple[tuple[str, str], ...], ...]


def default_database_path() -> str:
    return f"{filenames.asset_folder}/{filenames.database_folder}/{filenames.database_name}"


def parse_date(value: str) -> str:
    value = value.strip()
    pattern = r"(0?[1-9]|1[012])/(0?[1-9]|[12][0-9]|3[01])/((19|20)\d\d)"

    if not re.fullmatch(pattern, value):
        raise ValidationError("Date must be in MM/DD/YYYY format.")

    try:
        parsed = d.datetime.strptime(value, DATE_FORMAT)
    except ValueError as exc:
        raise ValidationError("Date is not a real calendar date.") from exc

    return parsed.strftime(DATE_FORMAT)


def parse_existing_date(value: str) -> str:
    value = value.strip()

    for date_format in (DATE_FORMAT, "%Y-%m-%d"):
        try:
            return d.datetime.strptime(value, date_format).strftime(DATE_FORMAT)
        except ValueError:
            pass

    raise ValidationError(f"Existing database date {value!r} is not recognized.")


def parse_year(value: str) -> str:
    value = value.strip()

    if not re.fullmatch(YEAR_PATTERN, value):
        raise ValidationError("Year must be a four-digit year between 1900 and 2099.")

    return value


def parse_emplid(value: str) -> str:
    value = value.strip()
    if not value or not (value.isascii() and value.isdigit()):
        raise ValidationError("EMPLID is required and must contain digits only.")
    return value


def parse_time(value: str) -> str:
    """Normalize a 12-hour time while preserving minute precision."""
    value = value.strip().upper()
    match = re.fullmatch(TIME_PATTERN, value)
    if not match:
        raise ValidationError("Time must look like 9AM, 2:15PM, or 2:15 PM.")

    hour, minute, meridiem = match.groups()
    hour = str(int(hour))
    return f"{hour}:{minute}{meridiem}" if minute else f"{hour}{meridiem}"


def time_minutes(value: str) -> int:
    """Return minutes since midnight for a validated 12-hour time."""
    normalized = parse_time(value)
    match = re.fullmatch(TIME_PATTERN, normalized)
    hour, minute, meridiem = match.groups()
    hour = int(hour) % 12 + (12 if meridiem == "PM" else 0)
    return hour * 60 + int(minute or 0)


def normalize_shift_segments(segments) -> tuple[tuple[str, str], ...]:
    """Accept either one legacy start/end pair or an ordered list of shifts."""
    if isinstance(segments, (tuple, list)) and len(segments) == 2 and all(
        isinstance(value, str) for value in segments
    ):
        raw_segments = [] if not any(str(value).strip() for value in segments) else [segments]
    else:
        raw_segments = list(segments)

    if len(raw_segments) > 2:
        raise ValidationError("A day can have at most two work intervals.")

    normalized = []
    previous_end = None
    for segment in raw_segments:
        if len(segment) != 2:
            raise ValidationError("Each work interval needs a start and end time.")
        start, end = (parse_time(str(value)) for value in segment)
        start_minutes, end_minutes = time_minutes(start), time_minutes(end)
        if end_minutes <= start_minutes:
            raise ValidationError("Each interval's end must be later than its start.")
        if previous_end is not None and start_minutes < previous_end:
            raise ValidationError("Work intervals cannot overlap or be out of order.")
        normalized.append((start, end))
        previous_end = end_minutes

    return tuple(normalized)


def parse_pay_period(value: str, first: int = 1, last: int = 26) -> str:
    value = value.strip()

    if not value.isnumeric() or not first <= int(value) <= last:
        raise ValidationError(f"Pay period must be between {first} and {last}.")

    return value


def add_period_end(start_date: str) -> str:
    start = d.datetime.strptime(parse_date(start_date), DATE_FORMAT)
    return (start + d.timedelta(days=13)).strftime(DATE_FORMAT)


class SocksDatabase:
    """Database service for payroll periods, invalid dates, employees, and shifts."""

    def __init__(self, path: str | None = None):
        self.path = path or default_database_path()

    def connect(self):
        con = sqlite3.connect(self.path)
        con.execute("PRAGMA foreign_keys = ON")
        return con

    @contextmanager
    def connection(self):
        con = self.connect()
        try:
            yield con
            con.commit()
        finally:
            con.close()

    def ensure_schema(self) -> None:
        with self.connection() as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS payroll_schedule(
                    pay_period TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    due_date TEXT,
                    pay_date TEXT
                )
                """
            )
            cur.execute("CREATE TABLE IF NOT EXISTS days_off(invalid_dates TEXT)")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employees(
                    employee_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    emplid TEXT UNIQUE
                )
                """
            )
            legacy_schedule_exists = cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='employee_schedule'"
            ).fetchone()
            segments_existed = cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='employee_schedule_segments'"
            ).fetchone()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employee_schedule_segments(
                    employee_id INTEGER NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
                    weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
                    segment_index INTEGER NOT NULL CHECK(segment_index BETWEEN 0 AND 1),
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    PRIMARY KEY(employee_id, weekday, segment_index)
                )
                """
            )

            if legacy_schedule_exists and not segments_existed:
                legacy_rows = cur.execute(
                    "SELECT employee_id, weekday, start_time, end_time FROM employee_schedule"
                ).fetchall()
                cur.executemany(
                    """INSERT INTO employee_schedule_segments
                       (employee_id, weekday, segment_index, start_time, end_time)
                       VALUES(?,?,0,?,?)""",
                    [row for row in legacy_rows if row[2] and row[3]],
                )
                cur.execute("DROP TABLE employee_schedule")

            columns = {
                row[1] for row in cur.execute("PRAGMA table_info(payroll_schedule)").fetchall()
            }
            due_column = "due_date" if "due_date" in columns else "''"
            pay_column = "pay_date" if "pay_date" in columns else "''"

            pay_rows = cur.execute(
                f"""
                SELECT rowid, pay_period, start_date, end_date,
                       {due_column} AS due_date, {pay_column} AS pay_date
                FROM payroll_schedule
                ORDER BY rowid
                """
            ).fetchall()
            invalid_rows = cur.execute(
                "SELECT rowid, invalid_dates FROM days_off ORDER BY rowid"
            ).fetchall()

            unique_pay = {}
            for _, pay_period, start_date, end_date, due_date, pay_date in pay_rows:
                period = parse_pay_period(str(pay_period))
                if period not in unique_pay:
                    unique_pay[period] = (
                        period,
                        parse_existing_date(str(start_date)),
                        parse_existing_date(str(end_date)),
                        parse_existing_date(str(due_date)) if due_date else "",
                        parse_existing_date(str(pay_date)) if pay_date else "",
                    )

            unique_invalid = []
            seen_dates = set()
            for _, invalid_date in invalid_rows:
                date = parse_existing_date(str(invalid_date))
                if date not in seen_dates:
                    seen_dates.add(date)
                    unique_invalid.append((date,))

            cur.execute("DROP TABLE payroll_schedule")
            cur.execute("DROP TABLE days_off")
            cur.execute(
                """
                CREATE TABLE payroll_schedule(
                    pay_period TEXT NOT NULL UNIQUE,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    due_date TEXT NOT NULL DEFAULT '',
                    pay_date TEXT NOT NULL DEFAULT ''
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE days_off(
                    invalid_dates TEXT NOT NULL UNIQUE
                )
                """
            )
            cur.executemany(
                """
                INSERT INTO payroll_schedule(pay_period,start_date,end_date,due_date,pay_date)
                VALUES(?,?,?,?,?)
                """,
                sorted(unique_pay.values(), key=lambda row: int(row[0])),
            )
            cur.executemany("INSERT INTO days_off(invalid_dates) VALUES(?)", unique_invalid)

    def list_pay_periods(self) -> list[PayPeriod]:
        with self.connection() as con:
            rows = con.execute(
                """
                SELECT pay_period, start_date, end_date, due_date, pay_date
                FROM payroll_schedule
                ORDER BY CAST(pay_period AS INTEGER)
                """
            ).fetchall()

        return [PayPeriod(*row) for row in rows]

    def list_invalid_dates(self) -> list[str]:
        with self.connection() as con:
            rows = con.execute(
                """
                SELECT invalid_dates
                FROM days_off
                ORDER BY substr(invalid_dates, 7, 4), substr(invalid_dates, 1, 2), substr(invalid_dates, 4, 2)
                """
            ).fetchall()

        return [row[0] for row in rows]

    def list_employees(self) -> list[Employee]:
        with self.connection() as con:
            employees = con.execute(
                "SELECT employee_id, name, emplid FROM employees ORDER BY employee_id"
            ).fetchall()
            shifts = con.execute(
                "SELECT employee_id, weekday, start_time, end_time "
                "FROM employee_schedule_segments "
                "ORDER BY employee_id, weekday, segment_index"
            ).fetchall()

        schedules = {row[0]: [[] for _ in range(7)] for row in employees}
        for employee_id, weekday, start_time, end_time in shifts:
            schedules[employee_id][weekday].append((start_time, end_time))

        return [
            Employee(
                name,
                emplid,
                tuple(tuple(day) for day in schedules[employee_id]),
            )
            for employee_id, name, emplid in employees
        ]

    def create_employee(
        self, name: str, schedule, emplid: str | None = None
    ) -> Employee:
        name = name.strip()
        if not name:
            raise ValidationError("Employee name cannot be empty.")
        if len(schedule) != 7:
            raise ValidationError("An employee schedule must contain seven weekdays.")

        normalized_schedule = tuple(normalize_shift_segments(day) for day in schedule)

        normalized_emplid = parse_emplid(emplid) if emplid is not None else None
        with self.connection() as con:
            cur = con.cursor()
            try:
                cur.execute("INSERT INTO employees(name, emplid) VALUES(?,?)", (name, normalized_emplid))
            except sqlite3.IntegrityError as exc:
                raise DuplicateError("Employee name or EMPLID already exists.") from exc
            employee_id = cur.lastrowid
            cur.executemany(
                """
                INSERT INTO employee_schedule_segments
                (employee_id, weekday, segment_index, start_time, end_time)
                VALUES(?,?,?,?,?)
                """,
                [
                    (employee_id, weekday, index, start, end)
                    for weekday, segments in enumerate(normalized_schedule)
                    for index, (start, end) in enumerate(segments)
                ],
            )

        return Employee(name, normalized_emplid, normalized_schedule)

    def set_employee_schedule(self, name: str, weekday: int, segments) -> None:
        """Replace one Sunday-first weekday schedule with up to two intervals."""
        if not isinstance(weekday, int) or not 0 <= weekday <= 6:
            raise ValidationError("Weekday must be an integer from 0 (Sunday) to 6 (Saturday).")
        normalized = normalize_shift_segments(segments)
        with self.connection() as con:
            cur = con.cursor()
            employee = cur.execute(
                "SELECT employee_id FROM employees WHERE name=? COLLATE NOCASE", (name.strip(),)
            ).fetchone()
            if not employee:
                raise NotFoundError(f"Employee {name!r} does not exist.")
            employee_id = employee[0]
            cur.execute(
                "DELETE FROM employee_schedule_segments WHERE employee_id=? AND weekday=?",
                (employee_id, weekday),
            )
            cur.executemany(
                """INSERT INTO employee_schedule_segments
                   (employee_id, weekday, segment_index, start_time, end_time)
                   VALUES(?,?,?,?,?)""",
                [
                    (employee_id, weekday, index, start, end)
                    for index, (start, end) in enumerate(normalized)
                ],
            )

    def set_employee_emplid(self, name: str, emplid: str) -> str:
        name = name.strip()
        emplid = parse_emplid(emplid)
        with self.connection() as con:
            cur = con.cursor()
            if not cur.execute(
                "SELECT employee_id FROM employees WHERE name=? COLLATE NOCASE", (name,)
            ).fetchone():
                raise NotFoundError(f"Employee {name!r} does not exist.")
            try:
                cur.execute("UPDATE employees SET emplid=? WHERE name=? COLLATE NOCASE", (emplid, name))
            except sqlite3.IntegrityError as exc:
                raise DuplicateError(f"EMPLID {emplid} is already assigned to another employee.") from exc

        return emplid

    def delete_employee(self, name: str) -> None:
        name = name.strip()
        with self.connection() as con:
            result = con.execute("DELETE FROM employees WHERE name=? COLLATE NOCASE", (name,))
            if result.rowcount == 0:
                raise NotFoundError(f"Employee {name!r} does not exist.")

    def create_pay_period(
        self, pay_period: str, start_date: str, due_date: str, pay_date: str
    ) -> PayPeriod:
        period = parse_pay_period(pay_period)
        start = parse_date(start_date)
        end = add_period_end(start)
        due = parse_date(due_date)
        pay = parse_date(pay_date)

        with self.connection() as con:
            cur = con.cursor()
            if cur.execute("SELECT 1 FROM payroll_schedule WHERE pay_period=?", (period,)).fetchone():
                raise DuplicateError(f"Pay period {period} already exists.")
            if cur.execute("SELECT pay_period FROM payroll_schedule WHERE start_date=?", (start,)).fetchone():
                raise DuplicateError(f"Start date {start} already exists.")
            cur.execute(
                """
                INSERT INTO payroll_schedule(pay_period,start_date,end_date,due_date,pay_date)
                VALUES(?,?,?,?,?)
                """,
                (period, start, end, due, pay),
            )

        return PayPeriod(period, start, end, due, pay)

    def update_pay_period(
        self, pay_period: str, start_date: str, due_date: str, pay_date: str
    ) -> PayPeriod:
        period = parse_pay_period(pay_period)
        start = parse_date(start_date)
        end = add_period_end(start)
        due = parse_date(due_date)
        pay = parse_date(pay_date)

        with self.connection() as con:
            cur = con.cursor()
            if not cur.execute("SELECT 1 FROM payroll_schedule WHERE pay_period=?", (period,)).fetchone():
                raise NotFoundError(f"Pay period {period} does not exist.")

            conflict = cur.execute(
                "SELECT pay_period FROM payroll_schedule WHERE start_date=? AND pay_period<>?",
                (start, period),
            ).fetchone()
            if conflict:
                raise DuplicateError(f"Start date {start} belongs to pay period {conflict[0]}.")

            cur.execute(
                """
                UPDATE payroll_schedule
                SET start_date=?, end_date=?, due_date=?, pay_date=?
                WHERE pay_period=?
                """,
                (start, end, due, pay, period),
            )

        return PayPeriod(period, start, end, due, pay)

    def delete_pay_period(self, pay_period: str) -> None:
        period = parse_pay_period(pay_period)

        with self.connection() as con:
            cur = con.cursor()
            result = cur.execute("DELETE FROM payroll_schedule WHERE pay_period=?", (period,))
            if result.rowcount == 0:
                raise NotFoundError(f"Pay period {period} does not exist.")

    def count_pay_periods_in_year(self, year: str) -> int:
        year = parse_year(year)

        with self.connection() as con:
            return con.execute(
                "SELECT COUNT(*) FROM payroll_schedule WHERE start_date LIKE ? AND end_date LIKE ?",
                (f"__/__/{year}", f"__/__/{year}"),
            ).fetchone()[0]

    def delete_pay_periods_in_year(self, year: str) -> int:
        year = parse_year(year)

        with self.connection() as con:
            result = con.execute(
                "DELETE FROM payroll_schedule WHERE start_date LIKE ? AND end_date LIKE ?",
                (f"__/__/{year}", f"__/__/{year}"),
            )
            return result.rowcount

    def create_invalid_date(self, invalid_date: str) -> str:
        date = parse_date(invalid_date)

        with self.connection() as con:
            try:
                con.execute("INSERT INTO days_off(invalid_dates) VALUES(?)", (date,))
            except sqlite3.IntegrityError as exc:
                raise DuplicateError(f"Invalid date {date} already exists.") from exc

        return date

    def update_invalid_date(self, old_date: str, new_date: str) -> str:
        old = parse_date(old_date)
        new = parse_date(new_date)

        with self.connection() as con:
            cur = con.cursor()
            if not cur.execute("SELECT 1 FROM days_off WHERE invalid_dates=?", (old,)).fetchone():
                raise NotFoundError(f"Invalid date {old} does not exist.")
            if cur.execute("SELECT 1 FROM days_off WHERE invalid_dates=?", (new,)).fetchone():
                raise DuplicateError(f"Invalid date {new} already exists.")
            cur.execute("UPDATE days_off SET invalid_dates=? WHERE invalid_dates=?", (new, old))

        return new

    def delete_invalid_date(self, invalid_date: str) -> None:
        date = parse_date(invalid_date)

        with self.connection() as con:
            result = con.execute("DELETE FROM days_off WHERE invalid_dates=?", (date,))
            if result.rowcount == 0:
                raise NotFoundError(f"Invalid date {date} does not exist.")

    def count_invalid_dates_in_year(self, year: str) -> int:
        year = parse_year(year)

        with self.connection() as con:
            return con.execute(
                "SELECT COUNT(*) FROM days_off WHERE invalid_dates LIKE ?",
                (f"__/__/{year}",),
            ).fetchone()[0]

    def delete_invalid_dates_in_year(self, year: str) -> int:
        year = parse_year(year)

        with self.connection() as con:
            result = con.execute(
                "DELETE FROM days_off WHERE invalid_dates LIKE ?",
                (f"__/__/{year}",),
            )
            return result.rowcount
