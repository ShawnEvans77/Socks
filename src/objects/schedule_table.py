from typing import List

from ..utils.database import SocksDatabase


class ScheduleTable:
    """Loads employee schedules and EMPLIDs from the Socks database."""

    def __init__(self):
        self.db = SocksDatabase()
        self.schedule_dict = {}
        self.emplid_dict = {}
        self.missed_days_dict = {}
        self.extra_days_dict = {}

        self.db.ensure_schema()
        for employee in self.db.list_employees():
            name = employee.name.lower()
            self.schedule_dict[name] = [list(day) for day in employee.schedule]
            self.emplid_dict[name] = employee.emplid
            self.missed_days_dict[name] = set()
            self.extra_days_dict[name] = {}

    def get(self, name: str) -> List[List[tuple[str, str]]]:
        """Return Sunday-through-Saturday lists of work intervals."""

        return self.schedule_dict[name.lower()]

    def has_name(self, name: str) -> bool:
        """Return whether an employee exists in the database."""

        return name.strip().lower() in self.schedule_dict

    def get_emplid(self, name: str) -> str | None:
        """Return the employee's saved EMPLID, if one has been entered."""

        return self.emplid_dict[name.strip().lower()]

    def set_emplid(self, name: str, emplid: str) -> str:
        """Save an employee's EMPLID in the database and refresh the cache."""

        normalized_name = name.strip().lower()
        saved_emplid = self.db.set_employee_emplid(name, emplid)
        self.emplid_dict[normalized_name] = saved_emplid
        return saved_emplid

    def add_missed_days(self, name: str, missed_days: set):
        """Record an employee's missed dates for the current timesheet."""

        self.missed_days_dict[name.lower()] = missed_days

    def get_missed_days(self, name: str) -> set:
        """Return the employee's missed dates for the current timesheet."""

        return self.missed_days_dict[name.lower()]

    def add_extra_days(self, name: str, extra_days: dict):
        """Store worked hours keyed by date for the current timesheet."""

        self.extra_days_dict[name.lower()] = dict(extra_days)

    def get_extra_days(self, name: str) -> dict:
        """Return manually entered hours keyed by date."""

        return self.extra_days_dict[name.lower()]
