from ..constants import filenames, guide
import sqlite3, re, datetime as d


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
        self.con = sqlite3.connect(
            f"{filenames.asset_folder}/{filenames.database_folder}/{filenames.database_name}"
        )
        self.cur = self.con.cursor()

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create_pay_period(self):
        self._header("Pay Period Creation", "CREATE")
        try:
            pay_period = Wrapper.fetch_period("Pay period to add")
            self.cur.execute(
                "SELECT pay_period FROM payroll_schedule WHERE pay_period=?", (pay_period,)
            )
            if self.cur.fetchall():
                self._error(f"Pay period {pay_period} already exists.")
                return

            start_str = Wrapper.fetch_date("Start date for this pay period")
            start_date = d.datetime.strptime(start_str, "%m/%d/%Y")

            self.cur.execute(
                "SELECT pay_period, start_date FROM payroll_schedule WHERE start_date=?",
                (start_date.strftime("%Y-%m-%d"),),
            )
            conflict = self.cur.fetchall()
            if conflict:
                self._error(f"{start_str} already belongs to pay period {conflict[0][0]}.")
                return

            end_date = start_date + d.timedelta(days=13)
            self.cur.execute(
                "INSERT INTO payroll_schedule(pay_period,start_date,end_date) VALUES(?,?,?);",
                (pay_period, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
            )
            self.con.commit()
            self._success(f"Pay period {pay_period} added.")

        except GoBack:
            self._cancelled()
        finally:
            self._footer()

    def create_invalid_date(self):
        self._header("Invalid Date Creation", "CREATE")
        try:
            date_str  = Wrapper.fetch_date("Invalid date to add")
            db_str    = d.datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")

            self.cur.execute("SELECT invalid_dates FROM days_off WHERE invalid_dates=?", (db_str,))
            if self.cur.fetchall():
                self._error(f"{date_str} is already in the database.")
                return

            self.cur.execute("INSERT INTO days_off(invalid_dates) VALUES(?);", (db_str,))
            self.con.commit()
            self._success(f"Invalid date {date_str} added.")

        except GoBack:
            self._cancelled()
        finally:
            self._footer()

    # ── READ ──────────────────────────────────────────────────────────────────

    def read_pay_period_start_end(self):
        self.cur.execute("SELECT * FROM payroll_schedule")
        rows = self.cur.fetchall()

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
            period_s = f" {int(row[0]):<8d}"
            start_s  = f" {row[1]:<11}"
            end_s    = f" {row[2]:<11}"
            print(f"  {sep}{period_s} {sep}{start_s} {sep}{end_s} {sep}")

        print(foot)
        print()

    def read_invalid_dates(self):
        self.cur.execute("SELECT * FROM days_off;")
        rows = self.cur.fetchall()

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
            print(f"  {sep} {row[0]:<11} {sep}")

        print(foot)
        print()

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update_pay_period(self):
        self._header("Pay Period Update", "UPDATE")
        try:
            pay_period = Wrapper.fetch_period("Pay period to update")
            self.cur.execute(
                "SELECT pay_period, start_date FROM payroll_schedule WHERE pay_period=?",
                (pay_period,),
            )
            row = self.cur.fetchall()
            if not row:
                self._error(f"Pay period {pay_period} does not exist.")
                return

            old = d.datetime.strptime(row[0][1], "%Y-%m-%d").strftime("%m/%d/%Y")
            print(f"    {c('Current start date:', Color.DIM)} {c(old, Color.YELLOW)}")

            start_str = Wrapper.fetch_date(f"New start date for pay period {pay_period}")
            start_date = d.datetime.strptime(start_str, "%m/%d/%Y")

            self.cur.execute(
                "SELECT pay_period FROM payroll_schedule WHERE start_date=?",
                (start_date.strftime("%Y-%m-%d"),),
            )
            conflict = self.cur.fetchall()
            if conflict:
                self._error(f"{start_str} already belongs to pay period {conflict[0][0]}.")
                return

            end_date = start_date + d.timedelta(days=13)
            self.cur.execute(
                "UPDATE payroll_schedule SET start_date=?, end_date=? WHERE pay_period=?",
                (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), pay_period),
            )
            self.con.commit()
            self._success(f"Pay period {pay_period}: {old} {c('→', Color.DIM)} {start_str}")

        except GoBack:
            self._cancelled()
        finally:
            self._footer()

    def update_invalid_date(self):
        self._header("Invalid Date Update", "UPDATE")
        try:
            date_str   = Wrapper.fetch_date("Date to change")
            db_str     = d.datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")

            self.cur.execute("SELECT invalid_dates FROM days_off WHERE invalid_dates=?", (db_str,))
            if not self.cur.fetchall():
                self._error(f"{date_str} does not exist in the database.")
                return

            new_str_in = Wrapper.fetch_date(f"Replacement for {c(date_str, Color.YELLOW)}")
            new_db_str = d.datetime.strptime(new_str_in, "%m/%d/%Y").strftime("%Y-%m-%d")

            self.cur.execute("SELECT invalid_dates FROM days_off WHERE invalid_dates=?", (new_db_str,))
            if self.cur.fetchall():
                self._error(f"{new_str_in} already exists in the database.")
                return

            self.cur.execute(
                "UPDATE days_off SET invalid_dates=? WHERE invalid_dates=?", (new_db_str, db_str)
            )
            self.con.commit()
            self._success(f"Updated: {date_str} {c('→', Color.DIM)} {new_str_in}")

        except GoBack:
            self._cancelled()
        finally:
            self._footer()

    # ── DELETE ────────────────────────────────────────────────────────────────

    def delete_pay_period(self):
        self._header("Pay Period Deletion", "DELETE")
        try:
            pay_period = Wrapper.fetch_period("Pay period to delete")
            self.cur.execute(
                "SELECT pay_period FROM payroll_schedule WHERE pay_period=?", (pay_period,)
            )
            if not self.cur.fetchall():
                self._error(f"Pay period {pay_period} does not exist.")
                return

            if Wrapper._confirm(f"Permanently delete pay period {c(pay_period, Color.YELLOW)}?"):
                self.con.execute("DELETE FROM payroll_schedule WHERE pay_period=?", (pay_period,))
                self.con.commit()
                self._success(f"Pay period {pay_period} deleted.")
            else:
                self._cancelled()

        except GoBack:
            self._cancelled()
        finally:
            self._footer()

    def delete_invalid_date(self):
        self._header("Invalid Date Deletion", "DELETE")
        try:
            date_str = Wrapper.fetch_date("Invalid date to delete")
            db_str   = d.datetime.strptime(date_str, "%m/%d/%Y").strftime("%Y-%m-%d")

            self.cur.execute("SELECT invalid_dates FROM days_off WHERE invalid_dates=?", (db_str,))
            if not self.cur.fetchall():
                self._error(f"{date_str} does not exist in the database.")
                return

            if Wrapper._confirm(f"Permanently delete invalid date {c(date_str, Color.YELLOW)}?"):
                self.con.execute("DELETE FROM days_off WHERE invalid_dates=?", (db_str,))
                self.con.commit()
                self._success(f"Invalid date {date_str} deleted.")
            else:
                self._cancelled()

        except GoBack:
            self._cancelled()
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
            if not raw.isnumeric():
                Wrapper._warn("Pay period must be a number.")
                continue
            if not first <= int(raw) <= last:
                Wrapper._warn(f"Pay period must be between {first} and {last}.")
                continue

            return raw

    @staticmethod
    def fetch_date(prompt: str) -> str:
        """Prompt for a date in MM/DD/YYYY format. Raises GoBack or QuitApp on escape."""
        pattern = r"(0?[1-9]|1[012])\/(0?[1-9]|[12][0-9]|3[01])\/((19|20)\d\d)"

        while True:
            raw = Wrapper._prompt(prompt, hint="MM/DD/YYYY")

            if raw.lower() == "b":
                raise GoBack
            if raw.lower() == "q":
                raise QuitApp
            if re.search(pattern, raw):
                return raw

            Wrapper._warn(f"'{raw}' is not a valid MM/DD/YYYY date.")

    @staticmethod
    def insertable_period(pay_period: str) -> bool:
        return pay_period.isnumeric() and 1 <= int(pay_period) <= 26

    @staticmethod
    def _confirm(message: str) -> bool:
        """Ask the user to confirm a destructive action. Returns True only on 'y'."""
        print(f"\n    {c('⚠  ' + message, Color.YELLOW)}")
        while True:
            raw = input(c("    Confirm [y/n]: ", Color.DIM)).strip().lower()
            if raw in ("y", "yes"):
                return True
            if raw in ("n", "no", "b", "q", ""):
                return False
            Wrapper._warn("Please enter y or n.")

    @staticmethod
    def _prompt(label: str, hint: str = "") -> str:
        """Render a styled input prompt with navigation hints."""
        nav = c(f"  ({hint})  ", Color.DIM) + c("[b]", Color.YELLOW) + c(" back  ", Color.DIM) + c("[q]", Color.RED) + c(" quit", Color.DIM)
        print(nav)
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