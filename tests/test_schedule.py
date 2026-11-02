import datetime as d
import unittest
from unittest.mock import patch

from src.objects.schedule_table import ScheduleTable


class ScheduleTableTestCase(unittest.TestCase):
    def test_missed_days_are_stored_by_lowercase_name(self):
        with patch("src.objects.schedule_table.SocksDatabase") as database_factory:
            database_factory.return_value.list_employees.return_value = []
            schedule_table = ScheduleTable()
            missed = {d.datetime(2026, 4, 20)}

            schedule_table.add_missed_days("Shawn Evans", missed)

            self.assertEqual(schedule_table.get_missed_days("shawn evans"), missed)


if __name__ == "__main__":
    unittest.main()
