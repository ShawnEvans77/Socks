import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.support import (
    FakeScheduleTable,
    ScheduleTable,
    SocksDatabase,
    use_guide_tables,
    weekly_schedule,
    wrapper_module,
)


class EmployeeScheduleCrudTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = SocksDatabase(str(Path(self.tmp.name) / "socks.db"))
        self.db.ensure_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_employee_wizard_collects_validated_week_and_allows_revision(self):
        existing_schedule = weekly_schedule()
        self.db.create_employee("Jamie Rivera", existing_schedule, "11111111")
        wrapper = wrapper_module.Wrapper.__new__(wrapper_module.Wrapper)
        wrapper.db = self.db
        cache = FakeScheduleTable(name="not yet saved")
        inputs = [
            "JAMIE", "RIVERA",              # Case-insensitive duplicate name.
            "Taylor", "Ng", "11111111",    # Duplicate EMPLID.
            "90000001", "54",
            "n",                              # Sunday off.
            "y", "9AM", "12PM", "n",       # Monday single interval.
            "n",                              # Tuesday off.
            "y", "12PM", "2PM", "y",       # Wednesday split, first try overlaps.
            "1:30PM", "3PM",
            "12PM", "2PM", "y", "2:15PM", "3:15PM",
            "n", "n", "n",                  # Thursday through Saturday off.
            "wed",                            # Revise Wednesday from the summary.
            "y", "12PM", "2PM", "y", "2:30PM", "3:30PM",
            "save",
        ]

        with use_guide_tables(schedule_table=cache), \
             patch("builtins.input", side_effect=inputs), \
             redirect_stdout(StringIO()):
            wrapper.create_employee()

        employees = self.db.list_employees()
        created = next(employee for employee in employees if employee.name == "Taylor Ng")
        self.assertEqual(created.emplid, "90000001")
        self.assertEqual(created.budget, 54)
        self.assertEqual(created.schedule[1], (("9AM", "12PM"),))
        self.assertEqual(created.schedule[2], ())
        self.assertEqual(created.schedule[3], (("12PM", "2PM"), ("2:30PM", "3:30PM")))
        self.assertEqual(created.schedule[6], ())
        self.assertEqual(cache.emplid_dict["taylor ng"], "90000001")
        self.assertEqual(cache.budget_dict["taylor ng"], 54)
        self.assertEqual(cache.schedule_dict["taylor ng"][3], [["12PM", "2PM"], ["2:30PM", "3:30PM"]])

    def test_new_employee_cancel_before_save_leaves_no_partial_record(self):
        wrapper = wrapper_module.Wrapper.__new__(wrapper_module.Wrapper)
        wrapper.db = self.db
        cache = FakeScheduleTable(name="not yet saved")
        inputs = ["Taylor", "Ng", "90000001", "54", "n", "n", "n", "n", "n", "n", "n", "b"]

        with use_guide_tables(schedule_table=cache), \
             patch("builtins.input", side_effect=inputs), \
             redirect_stdout(StringIO()):
            wrapper.create_employee()

        self.assertEqual(self.db.list_employees(), [])

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
        self.assertIn("Budget", text)
        self.assertIn("54", text)
        self.assertIn("Thursday", text)
        self.assertIn("12PM - 2PM, then 2:15PM - 3:15PM", text)

    def test_employee_budget_can_be_updated_from_crud(self):
        self.db.create_employee("Shawn Evans", weekly_schedule(), "90000001", 54)
        wrapper = wrapper_module.Wrapper.__new__(wrapper_module.Wrapper)
        wrapper.db = self.db
        with patch("src.objects.schedule_table.SocksDatabase", return_value=self.db):
            cache = ScheduleTable()

        with use_guide_tables(schedule_table=cache), \
             patch("builtins.input", side_effect=["shawn evans", "72"]), \
             redirect_stdout(StringIO()):
            wrapper.update_employee_budget()

        self.assertEqual(self.db.list_employees()[0].budget, 72)
        self.assertEqual(cache.get_budget("Shawn Evans"), 72)

if __name__ == '__main__':
    unittest.main()
