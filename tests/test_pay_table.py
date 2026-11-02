import datetime as dt
import tempfile
import unittest
from pathlib import Path

from src.objects.pay_table import PayTable
from src.utils.database import SocksDatabase, ValidationError


class PayTableDateTests(unittest.TestCase):
    def test_str_to_datetime_parses_month_day_year(self):
        self.assertEqual(
            PayTable.str_to_datetime("11/02/2026"),
            dt.datetime(2026, 11, 2),
        )

    def test_str_to_datetime_rejects_invalid_dates(self):
        with self.assertRaises(ValidationError):
            PayTable.str_to_datetime("02/30/2026")

    def test_pay_table_reads_payroll_data_through_database_service(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = SocksDatabase(str(Path(temp_dir) / "socks.db"))
            database.ensure_schema()
            database.create_pay_period("1", "04/05/2026", "04/20/2026", "04/30/2026")
            database.create_invalid_date("04/08/2026")

            pay_table = PayTable(database)

        self.assertEqual(pay_table.start_date_string(1), "04/05")
        self.assertEqual(pay_table.end_date_string(1), "04/18")
        self.assertEqual(pay_table.due_date_string(1), "04/20/2026")
        self.assertEqual(pay_table.get_invalid_dates(), [dt.datetime(2026, 4, 8)])


if __name__ == "__main__":
    unittest.main()
