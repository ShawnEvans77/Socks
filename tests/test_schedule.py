import datetime as d
import unittest

from src.objects.schedule_table import ScheduleTable


class ScheduleTableTestCase(unittest.TestCase):
    def test_missed_days_are_stored_by_lowercase_name(self):
        schedule_table = ScheduleTable()
        missed = {d.datetime(2026, 4, 20)}

        schedule_table.add_missed_days("Shawn Evans", missed)

        self.assertEqual(schedule_table.get_missed_days("shawn evans"), missed)


if __name__ == "__main__":
    unittest.main()
