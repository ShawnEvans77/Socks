from contextlib import ExitStack, contextmanager
import datetime as dt
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.constants.schedule import DAYS_PER_PAY_PERIOD, WEEKDAYS
from src.constants import filenames
from src.utils.database import (
    DuplicateError,
    SocksDatabase,
    ValidationError,
)


# The application constructs its tables during import. Keep that eager setup
# inside a temporary asset directory so tests never touch the user's database.
_test_assets = tempfile.TemporaryDirectory(prefix="socks-feature-tests-")
(Path(_test_assets.name) / filenames.database_folder).mkdir(parents=True)
_real_asset_folder = filenames.asset_folder
filenames.asset_folder = _test_assets.name
try:
    from app import main as app_main
    from app.work_days import WorkDaysFlow
    from crud import crud as crud_app
    from src.constants import guide
    from src.objects.schedule_table import ScheduleTable
    from src.objects.sheet_writer import SheetWriter
    from src.utils import wrapper as wrapper_module
finally:
    filenames.asset_folder = _real_asset_folder


@contextmanager
def use_guide_tables(pay_table=None, schedule_table=None):
    with ExitStack() as stack:
        if pay_table is not None:
            stack.enter_context(patch.object(guide.Tables.pay_table, "_value_", pay_table))
        if schedule_table is not None:
            stack.enter_context(patch.object(guide.Tables.schedule_table, "_value_", schedule_table))
        yield


def weekly_schedule():
    return [[] for _ in WEEKDAYS]


class FakePayTable:
    def __init__(self, start=dt.datetime(2026, 4, 5), due="04/20/2026", pay="04/30/2026"):
        self.dates = [
            start + dt.timedelta(days=offset)
            for offset in range(DAYS_PER_PAY_PERIOD)
        ]
        self.invalid_dates = []
        self.due = due
        self.pay = pay

    def get_period_dates(self, _pay_period):
        return self.dates

    def get_invalid_dates(self):
        return self.invalid_dates

    @staticmethod
    def date_str(date):
        return date.strftime("%m/%d")

    def start_date_string(self, _pay_period):
        return self.date_str(self.dates[0])

    def end_date_string(self, _pay_period):
        return self.date_str(self.dates[-1])

    def due_date_string(self, _pay_period):
        return self.due

    def pay_date_string(self, _pay_period):
        return self.pay


class FakeScheduleTable:
    def __init__(self, name="Shawn Evans", schedule=None, emplid="23862075", budget=54):
        self.name = name.lower()
        self.schedule = schedule or weekly_schedule()
        self.emplid = emplid
        self.budget = budget
        self.missed = set()
        self.missed_split_shifts = {}
        self.missed_split_shifts_dict = {self.name: self.missed_split_shifts}
        self.extra = {}
        self.schedule_dict = {self.name: self.schedule}
        self.emplid_dict = {self.name: self.emplid}
        self.budget_dict = {self.name: self.budget}
        self.missed_days_dict = {self.name: self.missed}
        self.extra_days_dict = {self.name: self.extra}

    def has_name(self, name):
        return name.strip().lower() == self.name

    def get_emplid(self, _name):
        return self.emplid

    def set_emplid(self, _name, emplid):
        self.emplid = emplid
        return emplid

    def get_budget(self, _name):
        return self.budget

    def set_budget(self, _name, budget):
        self.budget = int(budget)
        return self.budget

    def get(self, _name):
        return self.schedule

    def add_employee(self, employee):
        name = employee.name.lower()
        self.schedule_dict[name] = [
            [list(segment) for segment in day] for day in employee.schedule
        ]
        self.emplid_dict[name] = employee.emplid
        self.budget_dict[name] = employee.budget
        self.missed_days_dict[name] = set()
        self.missed_split_shifts_dict[name] = {}
        self.extra_days_dict[name] = {}

    def get_missed_days(self, _name):
        return self.missed

    def add_missed_days(self, _name, missed):
        self.missed = set(missed)

    def get_missed_split_shifts(self, _name):
        return self.missed_split_shifts_dict[_name.strip().lower()]

    def add_missed_split_shifts(self, _name, missed_shifts):
        self.missed_split_shifts = {
            date: {tuple(segment) for segment in segments}
            for date, segments in missed_shifts.items()
        }
        self.missed_split_shifts_dict[_name.strip().lower()] = self.missed_split_shifts

    def get_extra_days(self, _name):
        return self.extra

    def add_extra_days(self, _name, extra):
        self.extra = dict(extra)
