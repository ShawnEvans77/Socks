import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.support import (
    DuplicateError,
    ScheduleTable,
    SocksDatabase,
    ValidationError,
    weekly_schedule,
)


class DatabaseFeatureTests(unittest.TestCase):
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
        self.assertEqual(employee.budget, 54)
        self.assertEqual(employee.schedule[4], (("12PM", "2PM"), ("2:15PM", "3:15PM")))

    def test_employee_budget_is_persisted_and_validated(self):
        self.db.create_employee("Shawn Evans", weekly_schedule(), "90000001", "72")
        self.assertEqual(self.db.list_employees()[0].budget, 72)
        self.assertEqual(self.db.set_employee_budget("shawn evans", 81), 81)
        self.assertEqual(self.db.list_employees()[0].budget, 81)

        for invalid in ("", "abc", "１２３", "54-1"):
            with self.subTest(budget=invalid), self.assertRaises(ValidationError):
                self.db.set_employee_budget("Shawn Evans", invalid)

    def test_legacy_employee_table_gets_default_budget(self):
        legacy_path = str(Path(self.tmp.name) / "legacy_budget.db")
        con = sqlite3.connect(legacy_path)
        try:
            con.execute(
                "CREATE TABLE employees(employee_id INTEGER PRIMARY KEY, name TEXT, emplid TEXT)"
            )
            con.execute("INSERT INTO employees VALUES(1, 'Shawn Evans', '90000001')")
            con.commit()
        finally:
            con.close()

        legacy_db = SocksDatabase(legacy_path)
        legacy_db.ensure_schema()
        self.assertEqual(legacy_db.list_employees()[0].budget, 54)

    def test_schedule_table_loads_employee_name_emplid_and_intervals_from_database(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        self.db.create_employee("Shawn Evans", schedule, "90000001")

        with patch("src.objects.schedule_table.SocksDatabase", return_value=self.db):
            table = ScheduleTable()

        self.assertTrue(table.has_name(" Shawn Evans "))
        self.assertEqual(table.get_emplid("shawn evans"), "90000001")
        self.assertEqual(table.get_budget("shawn evans"), 54)
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
        self.assertEqual(employee.budget, 54)
        self.assertEqual(employee.schedule[4], (("12PM", "3:15PM"),))
        with legacy_db.connection() as con:
            self.assertIsNone(
                con.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='employee_schedule'"
                ).fetchone()
            )

if __name__ == '__main__':
    unittest.main()
