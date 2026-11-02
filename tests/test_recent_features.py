import atexit
from contextlib import ExitStack, contextmanager, redirect_stdout
import datetime as dt
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from io import StringIO
from unittest.mock import call, patch

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
    from crud import crud as crud_app
    from src.constants import guide
    from src.objects.schedule_table import ScheduleTable
    from src.objects.sheet_writer import SheetWriter
    from src.utils import wrapper as wrapper_module
finally:
    filenames.asset_folder = _real_asset_folder

_imported_pay_table = guide.Tables.pay_table.value
atexit.register(_test_assets.cleanup)
atexit.register(_imported_pay_table.con.close)


@contextmanager
def use_guide_tables(pay_table=None, schedule_table=None):
    with ExitStack() as stack:
        if pay_table is not None:
            stack.enter_context(patch.object(guide.Tables.pay_table, "_value_", pay_table))
        if schedule_table is not None:
            stack.enter_context(patch.object(guide.Tables.schedule_table, "_value_", schedule_table))
        yield


def weekly_schedule():
    return [[] for _ in range(7)]


class FakePayTable:
    def __init__(self, start=dt.datetime(2026, 4, 5), due="04/20/2026", pay="04/30/2026"):
        self.dates = [start + dt.timedelta(days=offset) for offset in range(14)]
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
    def __init__(self, name="Shawn Evans", schedule=None, emplid="90000001"):
        self.name = name.lower()
        self.schedule = schedule or weekly_schedule()
        self.emplid = emplid
        self.missed = set()
        self.extra = {}

    def has_name(self, name):
        return name.strip().lower() == self.name

    def get_emplid(self, _name):
        return self.emplid

    def set_emplid(self, _name, emplid):
        self.emplid = emplid
        return emplid

    def get(self, _name):
        return self.schedule

    def get_missed_days(self, _name):
        return self.missed

    def add_missed_days(self, _name, missed):
        self.missed = set(missed)

    def get_extra_days(self, _name):
        return self.extra

    def add_extra_days(self, _name, extra):
        self.extra = dict(extra)


class RecentDatabaseFeatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = SocksDatabase(str(Path(self.tmp.name) / "socks.db"))
        self.db.ensure_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_employee_split_schedule_and_emplid_persist_in_sqlite(self):
        schedule = weekly_schedule()
        schedule[4] = [("12pm", "2PM"), ("2:15 pm", "3:15pm")]

        self.db.create_employee("Shawn Evans", schedule, "90000001")
        employee = SocksDatabase(self.db.path).list_employees()[0]

        self.assertEqual(employee.name, "Shawn Evans")
        self.assertEqual(employee.emplid, "90000001")
        self.assertEqual(employee.schedule[4], (("12PM", "2PM"), ("2:15PM", "3:15PM")))

    def test_schedule_table_loads_employee_name_emplid_and_intervals_from_database(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        self.db.create_employee("Shawn Evans", schedule, "90000001")

        with patch("src.objects.schedule_table.SocksDatabase", return_value=self.db):
            table = ScheduleTable()

        self.assertTrue(table.has_name(" Shawn Evans "))
        self.assertEqual(table.get_emplid("shawn evans"), "90000001")
        self.assertEqual(
            table.get("shawn evans")[4],
            [("12PM", "2PM"), ("2:15PM", "3:15PM")],
        )

    def test_invalid_split_intervals_are_rejected_without_changing_saved_schedule(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        self.db.create_employee("Shawn Evans", schedule, "90000001")

        invalid_schedules = (
            [("12PM", "2PM"), ("1:30PM", "3PM")],
            [("2PM", "1PM")],
            [("9AM", "10AM"), ("11AM", "12PM"), ("1PM", "2PM")],
        )
        for segments in invalid_schedules:
            with self.subTest(segments=segments), self.assertRaises(ValidationError):
                self.db.set_employee_schedule("Shawn Evans", 4, segments)

        employee = self.db.list_employees()[0]
        self.assertEqual(employee.schedule[4], (("12PM", "2PM"), ("2:15PM", "3:15PM")))

    def test_emplid_is_numeric_and_unique(self):
        self.db.create_employee("Shawn Evans", weekly_schedule())
        self.db.create_employee("Other Person", weekly_schedule(), "76543210")

        for invalid in ("", "abc", "１２３"):
            with self.subTest(emplid=invalid), self.assertRaises(ValidationError):
                self.db.set_employee_emplid("Shawn Evans", invalid)

        with self.assertRaises(DuplicateError):
            self.db.set_employee_emplid("Shawn Evans", "76543210")
        self.assertEqual(self.db.set_employee_emplid("Shawn Evans", "90000001"), "90000001")

    def test_legacy_weekly_schedule_migrates_to_segment_table(self):
        legacy_path = str(Path(self.tmp.name) / "legacy.db")
        con = sqlite3.connect(legacy_path)
        try:
            con.execute(
                "CREATE TABLE employees(employee_id INTEGER PRIMARY KEY, name TEXT, emplid TEXT)"
            )
            con.execute("INSERT INTO employees VALUES(1, 'Shawn Evans', '90000001')")
            con.execute(
                "CREATE TABLE employee_schedule(employee_id INTEGER, weekday INTEGER, "
                "start_time TEXT, end_time TEXT)"
            )
            con.execute(
                "INSERT INTO employee_schedule VALUES(1, 4, '12PM', '3:15PM')"
            )
            con.commit()
        finally:
            con.close()

        legacy_db = SocksDatabase(legacy_path)
        legacy_db.ensure_schema()

        employee = legacy_db.list_employees()[0]
        self.assertEqual(employee.emplid, "90000001")
        self.assertEqual(employee.schedule[4], (("12PM", "3:15PM"),))
        with legacy_db.connection() as con:
            self.assertIsNone(
                con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='employee_schedule'"
                ).fetchone()
            )


class RecentPromptFeatureTests(unittest.TestCase):
    def test_required_emplid_retries_invalid_and_duplicate_values(self):
        schedule_table = FakeScheduleTable(emplid=None)
        schedule_table.set_emplid = unittest.mock.Mock(
            side_effect=[DuplicateError("already assigned"), "90000001"]
        )
        inputs = ["shawn", "evans", "", "１２３", "letters", "111", "90000001"]

        with use_guide_tables(schedule_table=schedule_table), \
             patch.object(app_main, "_prompt", side_effect=inputs), \
             redirect_stdout(StringIO()):
            result = app_main._step_employee()

        self.assertEqual(result, ("shawn", "evans", "90000001"))
        self.assertEqual(
            schedule_table.set_emplid.call_args_list,
            [call("shawn evans", "111"), call("shawn evans", "90000001")],
        )

    def test_saved_emplid_does_not_prompt_again(self):
        schedule_table = FakeScheduleTable(emplid="90000001")
        with use_guide_tables(schedule_table=schedule_table), \
             patch.object(app_main, "_prompt", side_effect=["shawn", "evans"]), \
             redirect_stdout(StringIO()):
            result = app_main._step_employee()

        self.assertEqual(result, ("shawn", "evans", "90000001"))

    def test_extra_days_validate_dates_duplicates_and_time_order(self):
        schedule_table = FakeScheduleTable()
        schedule_table.missed = {dt.datetime(2026, 4, 8)}
        pay_table = FakePayTable()
        inputs = [
            "04/08",                          # Conflicts with a missed day.
            "04/19",                          # Outside the pay period.
            "04/09 04/09",                   # Duplicate date.
            "04/09 04/10",
            "not a time", "9AM", "8AM",    # Invalid start, then end before start.
            "9:00AM", "10:30AM",
            "2:15PM", "3:15PM",
        ]

        with use_guide_tables(pay_table, schedule_table), \
             patch.object(app_main, "_yn", return_value=True), \
             patch.object(app_main, "_prompt", side_effect=inputs), \
             redirect_stdout(StringIO()):
            app_main._step_extra_days("Shawn", "Evans", 1)

        self.assertEqual(
            schedule_table.extra,
            {
                dt.datetime(2026, 4, 9): ("9:00AM", "10:30AM"),
                dt.datetime(2026, 4, 10): ("2:15PM", "3:15PM"),
            },
        )

    def test_declining_extra_days_clears_current_entries(self):
        schedule_table = FakeScheduleTable()
        schedule_table.extra = {dt.datetime(2026, 4, 9): ("9AM", "10AM")}
        with use_guide_tables(schedule_table=schedule_table), \
             patch.object(app_main, "_yn", return_value=False), \
             redirect_stdout(StringIO()):
            app_main._step_extra_days("Shawn", "Evans", 1)
        self.assertEqual(schedule_table.extra, {})

    def test_main_reports_payroll_due_and_pay_dates(self):
        pay_table = FakePayTable(due="11/16/2026", pay="12/10/2026")
        output = StringIO()
        with use_guide_tables(pay_table=pay_table), \
             patch.object(app_main, "_banner"), \
             patch.object(app_main, "_step_employee", return_value=("shawn", "evans", "90000001")), \
             patch.object(app_main, "_step_pay_period", return_value=19), \
             patch.object(app_main, "_step_work_days"), \
             patch.object(app_main, "_generate", return_value="Evans_Timesheet_19.pdf"), \
             redirect_stdout(output):
            app_main.main()

        plain_output = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        self.assertIn(
            "Timesheet is due on 11/16/2026. You will be paid on 12/10/2026.",
            plain_output,
        )

    def test_global_exit_and_menu_local_q(self):
        with redirect_stdout(StringIO()), patch("builtins.input", return_value="q"):
            self.assertEqual(app_main._prompt("input"), "q")
            self.assertEqual(wrapper_module.Wrapper._prompt("input"), "q")

        with redirect_stdout(StringIO()), patch("builtins.input", return_value="EXIT()"):
            with self.assertRaises(app_main.QuitApp):
                app_main._prompt("input")
            with self.assertRaises(wrapper_module.QuitApp):
                wrapper_module.Wrapper._prompt("input")

        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=["q", "y"]):
            self.assertTrue(app_main._yn("yes or no"))

        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=["maybe", "y"]):
            self.assertTrue(app_main._yn("yes or no"))

        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=["q", "y"]):
            self.assertTrue(wrapper_module.Wrapper._yes_no("yes or no"))

        with redirect_stdout(StringIO()), patch("builtins.input", side_effect=["q", "Wed"]):
            self.assertEqual(wrapper_module.Wrapper.fetch_weekday("weekday"), 3)

    def test_crud_menu_routes_sequential_choices_and_q_quits_menu(self):
        calls = []

        class RecordingWrapper:
            def __getattr__(self, method_name):
                return lambda: calls.append(method_name)

        expected = [
            "create_pay_period",
            "create_invalid_date",
            "read_pay_period_start_end",
            "read_invalid_dates",
            "read_employee_names_and_emplids",
            "read_employee_schedules",
            "update_pay_period",
            "update_invalid_date",
            "update_employee_schedule",
            "delete_pay_period",
            "delete_invalid_date",
        ]
        choices = [str(number) for number in range(1, 12)] + ["q"]

        with redirect_stdout(StringIO()), \
             patch.object(crud_app.wrapper, "Wrapper", return_value=RecordingWrapper()), \
             patch.object(crud_app, "menu"), \
             patch("builtins.input", side_effect=choices):
            crud_app.main()

        self.assertEqual(calls, expected)

    def test_crud_exit_command_quits_from_menu(self):
        class RecordingWrapper:
            called = False

            def __getattr__(self, _method_name):
                self.called = True
                return lambda: None

        wrapper = RecordingWrapper()
        with redirect_stdout(StringIO()), \
             patch.object(crud_app.wrapper, "Wrapper", return_value=wrapper), \
             patch.object(crud_app, "menu"), \
             patch("builtins.input", return_value="exit()"):
            crud_app.main()
        self.assertFalse(wrapper.called)


class RecentScheduleCrudTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = SocksDatabase(str(Path(self.tmp.name) / "socks.db"))
        self.db.ensure_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_schedule_editor_accepts_weekday_and_split_shift_and_retries_overlap(self):
        schedule = weekly_schedule()
        schedule[4] = [("10AM", "1PM")]
        self.db.create_employee("Sample Person", schedule, "12345678")
        wrapper = wrapper_module.Wrapper.__new__(wrapper_module.Wrapper)
        wrapper.db = self.db
        inputs = [
            "sAmPlE pErSoN", "thu", "y",
            "12PM", "2PM", "1:30PM", "3PM",  # Overlapping second interval.
            "12PM", "2PM", "2:15PM", "3:15PM",
        ]

        with use_guide_tables(schedule_table=FakeScheduleTable(name="not in db")), \
             patch("builtins.input", side_effect=inputs), \
             redirect_stdout(StringIO()):
            wrapper.update_employee_schedule()

        employee = self.db.list_employees()[0]
        self.assertEqual(employee.schedule[4], (("12PM", "2PM"), ("2:15PM", "3:15PM")))

    def test_schedule_editor_can_clear_a_weekday(self):
        schedule = weekly_schedule()
        schedule[1] = [("9AM", "12PM")]
        self.db.create_employee("Sample Person", schedule, "12345678")
        wrapper = wrapper_module.Wrapper.__new__(wrapper_module.Wrapper)
        wrapper.db = self.db

        with use_guide_tables(schedule_table=FakeScheduleTable(name="not in db")), \
             patch("builtins.input", side_effect=["Sample Person", "Monday", "n", "OFF"]), \
             redirect_stdout(StringIO()):
            wrapper.update_employee_schedule()

        self.assertEqual(self.db.list_employees()[0].schedule[1], ())

    def test_crud_views_employee_name_emplid_and_split_schedule(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        self.db.create_employee("Shawn Evans", schedule, "90000001")
        wrapper = wrapper_module.Wrapper.__new__(wrapper_module.Wrapper)
        wrapper.db = self.db
        output = StringIO()

        with redirect_stdout(output):
            wrapper.read_employee_names_and_emplids()
            wrapper.read_employee_schedules()

        text = output.getvalue()
        self.assertIn("Shawn Evans", text)
        self.assertIn("90000001", text)
        self.assertIn("Thursday", text)
        self.assertIn("12PM - 2PM, then 2:15PM - 3:15PM", text)


class RecentPdfFeatureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def make_writer(self, emplid="90000001"):
        input_pdf = Path(filenames.asset_folder) / filenames.pdf_input_folder / filenames.starting_pdf
        return SheetWriter(str(input_pdf), "evans", "shawn", 1, emplid)

    def test_emplid_is_required_and_numeric(self):
        for emplid in ("", "abc", "１２３"):
            with self.subTest(emplid=emplid), self.assertRaises(ValueError):
                self.make_writer(emplid)

    def test_ca_checkbox_is_selected_in_form_before_flattening(self):
        with use_guide_tables(pay_table=FakePayTable()):
            sheet = self.make_writer()
            sheet.write_ca_checkbox()
            checkbox = next(
                annotation.get_object()
                for annotation in sheet.page.get("/Annots", [])
                if annotation.get_object().get("/T") == "CheckBox1[0]"
            )
        self.assertEqual(str(checkbox.get("/V")), "/1")

    def test_split_shift_pdf_has_visible_labels_and_is_not_editable(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        pay_table = FakePayTable()
        schedule_table = FakeScheduleTable(schedule=schedule)
        output_path = Path(self.tmp.name) / "Evans_Timesheet_1.pdf"

        with use_guide_tables(pay_table, schedule_table), \
             patch.object(filenames, "output_folder", self.tmp.name):
            sheet = self.make_writer()
            with patch.object(sheet, "update_field", wraps=sheet.update_field) as update_field:
                sheet.write_timesheet()
                sheet.output_timesheet(output_path.name)

        meal_field = SheetWriter.txt_field(guide.Indices.meal_period_indices.value[4])
        self.assertIn(call(meal_field, ""), update_field.call_args_list)
        self.assertEqual(len(sheet.split_shift_cells), 2)

        from pypdf import PdfReader

        reader = PdfReader(str(output_path))
        self.assertIsNone(reader.get_fields())
        self.assertFalse(
            any(
                annotation.get_object().get("/Subtype") == "/Widget"
                for annotation in reader.pages[0].get("/Annots", [])
            )
        )
        text = reader.pages[0].extract_text() or ""
        for expected in (
            "Learning Center",
            "885-54",
            "Prepared by",
            "Shawn Evans",
            "90000001",
            "12PM",
            "2PM",
            "2:15PM",
            "3:15PM",
        ):
            with self.subTest(text=expected):
                self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
