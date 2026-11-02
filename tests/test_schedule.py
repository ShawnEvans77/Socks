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

    def test_missed_split_shifts_are_stored_by_date_for_current_timesheet(self):
        with patch("src.objects.schedule_table.SocksDatabase") as database_factory:
            database_factory.return_value.list_employees.return_value = []
            schedule_table = ScheduleTable()
            date = d.datetime(2026, 4, 9)
            missed = {date: {("12PM", "2PM")}}

            schedule_table.add_missed_split_shifts("Shawn Evans", missed)

            self.assertEqual(
                schedule_table.get_missed_split_shifts("shawn evans"), missed
            )

    def test_extra_days_store_one_or_two_normalized_intervals(self):
        with patch("src.objects.schedule_table.SocksDatabase") as database_factory:
            database_factory.return_value.list_employees.return_value = []
            schedule_table = ScheduleTable()
            single_date = d.datetime(2026, 4, 9)
            split_date = d.datetime(2026, 4, 10)

            schedule_table.add_extra_days(
                "Shawn Evans",
                {
                    single_date: ("9am", "10:30 am"),
                    split_date: [("12PM", "2PM"), ("2:15PM", "3:15PM")],
                },
            )

            self.assertEqual(
                schedule_table.get_extra_days("shawn evans"),
                {
                    single_date: (("9AM", "10:30AM"),),
                    split_date: (("12PM", "2PM"), ("2:15PM", "3:15PM")),
                },
            )


if __name__ == "__main__":
    unittest.main()
