import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.utils.database import (
    DuplicateError,
    NotFoundError,
    SocksDatabase,
    ValidationError,
    parse_date,
    parse_pay_period,
    parse_year,
)


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "socks.db")
        self.db = SocksDatabase(self.path)
        self.db.ensure_schema()

    def tearDown(self):
        self.tmp.cleanup()

    def test_date_period_and_year_validation(self):
        self.assertEqual(parse_date("1/2/2026"), "01/02/2026")
        self.assertEqual(parse_pay_period("26"), "26")
        self.assertEqual(parse_year("2027"), "2027")

        with self.assertRaises(ValidationError):
            parse_date("02/31/2026")
        with self.assertRaises(ValidationError):
            parse_pay_period("27")
        with self.assertRaises(ValidationError):
            parse_year("1899")

    def test_schema_dedupes_and_adds_unique_constraints(self):
        con = sqlite3.connect(self.path)
        try:
            cur = con.cursor()
            cur.execute("DROP TABLE payroll_schedule")
            cur.execute("DROP TABLE days_off")
            cur.execute("CREATE TABLE payroll_schedule(pay_period TEXT, start_date TEXT, end_date TEXT)")
            cur.execute("CREATE TABLE days_off(invalid_dates TEXT)")
            cur.executemany(
                "INSERT INTO payroll_schedule(pay_period,start_date,end_date) VALUES(?,?,?)",
                [
                    ("1", "2026-01-01", "2026-01-14"),
                    ("1", "01/15/2026", "01/28/2026"),
                ],
            )
            cur.executemany(
                "INSERT INTO days_off(invalid_dates) VALUES(?)",
                [("02/12/2026",), ("02/12/2026",)],
            )
            con.commit()
        finally:
            con.close()

        self.db.ensure_schema()

        self.assertEqual(len(self.db.list_pay_periods()), 1)
        self.assertEqual(self.db.list_invalid_dates(), ["02/12/2026"])

        with self.assertRaises(sqlite3.IntegrityError):
            con = sqlite3.connect(self.path)
            try:
                con.execute(
                    "INSERT INTO days_off(invalid_dates) VALUES(?)",
                    ("02/12/2026",),
                )
            finally:
                con.close()

    def test_pay_period_create_update_delete(self):
        period = self.db.create_pay_period("1", "01/01/2026")

        self.assertEqual(period.start_date, "01/01/2026")
        self.assertEqual(period.end_date, "01/14/2026")

        with self.assertRaises(DuplicateError):
            self.db.create_pay_period("1", "01/15/2026")

        updated = self.db.update_pay_period("1", "01/15/2026")
        self.assertEqual(updated.end_date, "01/28/2026")

        self.db.delete_pay_period("1")
        self.assertEqual(self.db.list_pay_periods(), [])

        with self.assertRaises(NotFoundError):
            self.db.delete_pay_period("1")

    def test_invalid_date_create_update_delete(self):
        self.assertEqual(self.db.create_invalid_date("2/12/2026"), "02/12/2026")

        with self.assertRaises(DuplicateError):
            self.db.create_invalid_date("02/12/2026")

        self.assertEqual(
            self.db.update_invalid_date("02/12/2026", "02/13/2026"),
            "02/13/2026",
        )
        self.db.delete_invalid_date("02/13/2026")
        self.assertEqual(self.db.list_invalid_dates(), [])

    def test_delete_invalid_dates_by_year(self):
        for date in ("01/01/2026", "02/01/2026", "01/01/2027"):
            self.db.create_invalid_date(date)

        self.assertEqual(self.db.count_invalid_dates_in_year("2026"), 2)
        self.assertEqual(self.db.delete_invalid_dates_in_year("2026"), 2)
        self.assertEqual(self.db.list_invalid_dates(), ["01/01/2027"])

    def test_delete_pay_periods_by_year_requires_start_and_end_in_year(self):
        con = sqlite3.connect(self.path)
        try:
            con.executemany(
                "INSERT INTO payroll_schedule(pay_period,start_date,end_date) VALUES(?,?,?)",
                [
                    ("1", "12/20/2025", "01/02/2026"),
                    ("2", "01/03/2026", "01/16/2026"),
                    ("3", "12/20/2026", "01/02/2027"),
                ],
            )
            con.commit()
        finally:
            con.close()

        self.assertEqual(self.db.count_pay_periods_in_year("2026"), 1)
        self.assertEqual(self.db.delete_pay_periods_in_year("2026"), 1)
        self.assertEqual([row.pay_period for row in self.db.list_pay_periods()], ["1", "3"])


if __name__ == "__main__":
    unittest.main()
