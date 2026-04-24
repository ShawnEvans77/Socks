from ..constants import filenames
from contextlib import contextmanager
from dataclasses import dataclass
import datetime as d
import re
import sqlite3


DATE_FORMAT = "%m/%d/%Y"
YEAR_PATTERN = r"(19|20)\d\d"


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


def parse_pay_period(value: str, first: int = 1, last: int = 26) -> str:
    value = value.strip()

    if not value.isnumeric() or not first <= int(value) <= last:
        raise ValidationError(f"Pay period must be between {first} and {last}.")

    return value


def add_period_end(start_date: str) -> str:
    start = d.datetime.strptime(parse_date(start_date), DATE_FORMAT)
    return (start + d.timedelta(days=13)).strftime(DATE_FORMAT)


class SocksDatabase:
    """Database service for Socks pay periods and invalid dates."""

    def __init__(self, path: str | None = None):
        self.path = path or default_database_path()

    def connect(self):
        return sqlite3.connect(self.path)

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
                "CREATE TABLE IF NOT EXISTS payroll_schedule(pay_period TEXT, start_date TEXT, end_date TEXT)"
            )
            cur.execute("CREATE TABLE IF NOT EXISTS days_off(invalid_dates TEXT)")

            pay_rows = cur.execute(
                "SELECT rowid, pay_period, start_date, end_date FROM payroll_schedule ORDER BY rowid"
            ).fetchall()
            invalid_rows = cur.execute(
                "SELECT rowid, invalid_dates FROM days_off ORDER BY rowid"
            ).fetchall()

            unique_pay = {}
            for _, pay_period, start_date, end_date in pay_rows:
                period = parse_pay_period(str(pay_period))
                if period not in unique_pay:
                    unique_pay[period] = (
                        period,
                        parse_existing_date(str(start_date)),
                        parse_existing_date(str(end_date)),
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
                    end_date TEXT NOT NULL
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
                "INSERT INTO payroll_schedule(pay_period,start_date,end_date) VALUES(?,?,?)",
                sorted(unique_pay.values(), key=lambda row: int(row[0])),
            )
            cur.executemany("INSERT INTO days_off(invalid_dates) VALUES(?)", unique_invalid)

    def list_pay_periods(self) -> list[PayPeriod]:
        with self.connection() as con:
            rows = con.execute(
                """
                SELECT pay_period, start_date, end_date
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

    def create_pay_period(self, pay_period: str, start_date: str) -> PayPeriod:
        period = parse_pay_period(pay_period)
        start = parse_date(start_date)
        end = add_period_end(start)

        with self.connection() as con:
            cur = con.cursor()
            if cur.execute("SELECT 1 FROM payroll_schedule WHERE pay_period=?", (period,)).fetchone():
                raise DuplicateError(f"Pay period {period} already exists.")
            if cur.execute("SELECT pay_period FROM payroll_schedule WHERE start_date=?", (start,)).fetchone():
                raise DuplicateError(f"Start date {start} already exists.")
            cur.execute(
                "INSERT INTO payroll_schedule(pay_period,start_date,end_date) VALUES(?,?,?)",
                (period, start, end),
            )

        return PayPeriod(period, start, end)

    def update_pay_period(self, pay_period: str, start_date: str) -> PayPeriod:
        period = parse_pay_period(pay_period)
        start = parse_date(start_date)
        end = add_period_end(start)

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
                "UPDATE payroll_schedule SET start_date=?, end_date=? WHERE pay_period=?",
                (start, end, period),
            )

        return PayPeriod(period, start, end)

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
