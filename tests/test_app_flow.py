import datetime as dt
import re
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import call, patch

from tests.support import (
    DuplicateError,
    FakePayTable,
    FakeScheduleTable,
    WorkDaysFlow,
    app_main,
    crud_app,
    use_guide_tables,
    weekly_schedule,
    wrapper_module,
)
class AppFlowTests(unittest.TestCase):
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
             patch.object(app_main.console, "yes_no", side_effect=[True, False, False]), \
             patch.object(app_main.console, "prompt", side_effect=inputs), \
             redirect_stdout(StringIO()):
            WorkDaysFlow(schedule_table, pay_table).collect_extra_days("Shawn", "Evans", 1)

        self.assertEqual(
            schedule_table.extra,
            {
                dt.datetime(2026, 4, 9): (("9:00AM", "10:30AM"),),
                dt.datetime(2026, 4, 10): (("2:15PM", "3:15PM"),),
            },
        )

    def test_extra_split_day_retries_overlapping_intervals(self):
        schedule_table = FakeScheduleTable()
        inputs = [
            "04/09",
            "12PM", "2PM", "1:45PM", "3PM",
            "12PM", "2PM", "2:15PM", "3:15PM",
        ]

        pay_table = FakePayTable()
        with use_guide_tables(pay_table, schedule_table), \
             patch.object(app_main.console, "yes_no", side_effect=[True, True]), \
             patch.object(app_main.console, "prompt", side_effect=inputs), \
             redirect_stdout(StringIO()):
            WorkDaysFlow(schedule_table, pay_table).collect_extra_days("Shawn", "Evans", 1)

        self.assertEqual(
            schedule_table.extra,
            {
                dt.datetime(2026, 4, 9): (
                    ("12PM", "2PM"), ("2:15PM", "3:15PM")
                )
            },
        )

    def test_declining_extra_days_clears_current_entries(self):
        schedule_table = FakeScheduleTable()
        schedule_table.extra = {dt.datetime(2026, 4, 9): ("9AM", "10AM")}
        with use_guide_tables(schedule_table=schedule_table), \
             patch.object(app_main.console, "yes_no", return_value=False), \
             redirect_stdout(StringIO()):
            WorkDaysFlow(schedule_table, FakePayTable()).collect_extra_days("Shawn", "Evans", 1)
        self.assertEqual(schedule_table.extra, {})

    def test_work_days_gate_skips_all_exception_questions_when_no(self):
        schedule_table = FakeScheduleTable()
        schedule_table.missed = {dt.datetime(2026, 4, 8)}
        schedule_table.missed_split_shifts = {
            dt.datetime(2026, 4, 9): {("12PM", "2PM")}
        }
        schedule_table.extra = {dt.datetime(2026, 4, 10): (("9AM", "10AM"),)}
        pay_table = FakePayTable()
        output = StringIO()

        with use_guide_tables(pay_table, schedule_table), \
             patch.object(app_main.console, "yes_no", return_value=False) as ask_yes_no, \
             patch.object(app_main.console, "prompt") as prompt, \
             redirect_stdout(output):
            app_main._step_work_days("Shawn", "Evans", 1)

        ask_yes_no.assert_called_once_with("Any notable changes to account for this week?")
        prompt.assert_not_called()
        self.assertEqual(schedule_table.missed, set())
        self.assertEqual(schedule_table.missed_split_shifts, {})
        self.assertEqual(schedule_table.extra, {})
        self.assertNotIn("Did you work an extra day", output.getvalue())
        self.assertIn("No schedule changes", output.getvalue())

    def test_work_days_gate_yes_proceeds_to_relevant_exception_questions(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        schedule_table = FakeScheduleTable(schedule=schedule)
        pay_table = FakePayTable()

        with use_guide_tables(pay_table, schedule_table), \
             patch.object(app_main.console, "yes_no", side_effect=[True, False, False, False]) as ask_yes_no, \
             redirect_stdout(StringIO()):
            app_main._step_work_days("Shawn", "Evans", 1)

        self.assertEqual(
            [call.args[0] for call in ask_yes_no.call_args_list],
            [
                "Any notable changes to account for this week?",
                "Did you miss any days this pay period?",
                "Did you miss your split schedule?",
                "Did you work an extra day or days this pay period?",
            ],
        )

    def test_missed_split_prompt_records_only_selected_date_and_interval(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        schedule_table = FakeScheduleTable(schedule=schedule)
        pay_table = FakePayTable()
        output = StringIO()

        with use_guide_tables(pay_table, schedule_table), \
             patch.object(app_main.console, "yes_no", return_value=True), \
             patch.object(app_main.console, "prompt", side_effect=["2"]), \
             redirect_stdout(output):
            WorkDaysFlow(schedule_table, pay_table).collect_missed_split_shifts("Shawn Evans", 1)

        first_thursday = dt.datetime(2026, 4, 9)
        second_thursday = dt.datetime(2026, 4, 16)
        self.assertEqual(
            schedule_table.get_missed_split_shifts("Shawn Evans"),
            {first_thursday: {("2:15PM", "3:15PM")}},
        )
        self.assertEqual(schedule_table.schedule[4], [
            ("12PM", "2PM"), ("2:15PM", "3:15PM")
        ])
        self.assertIn("Thu 04/09  12PM - 2PM", output.getvalue())
        self.assertIn("Thu 04/16  2:15PM - 3:15PM", output.getvalue())

    def test_missed_split_choice_validation_retries(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        schedule_table = FakeScheduleTable(schedule=schedule)

        pay_table = FakePayTable()
        with use_guide_tables(pay_table, schedule_table), \
             patch.object(app_main.console, "yes_no", return_value=True), \
             patch.object(app_main.console, "prompt", side_effect=["0", "1 1", "5", "1"]), \
             redirect_stdout(StringIO()):
            WorkDaysFlow(schedule_table, pay_table).collect_missed_split_shifts("Shawn Evans", 1)

        self.assertEqual(
            schedule_table.get_missed_split_shifts("Shawn Evans"),
            {dt.datetime(2026, 4, 9): {("12PM", "2PM")}},
        )

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
        self.assertIn("Evans_Timesheet_19.pdf", plain_output)
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
            "create_employee",
            "read_pay_period_start_end",
            "read_invalid_dates",
            "read_employee_names_and_emplids",
            "read_employee_schedules",
            "update_pay_period",
            "update_invalid_date",
            "update_employee_schedule",
            "update_employee_budget",
            "delete_pay_period",
            "delete_invalid_date",
        ]
        choices = [str(number) for number in range(1, 14)] + ["q"]

        with redirect_stdout(StringIO()), \
             patch.object(crud_app.wrapper, "Wrapper", return_value=RecordingWrapper()), \
             patch.object(crud_app, "menu"), \
             patch("builtins.input", side_effect=choices):
            crud_app.main()

        self.assertEqual(calls, expected)

    def test_crud_menu_displays_employee_creation_and_contiguous_choices(self):
        output = StringIO()
        with redirect_stdout(output):
            crud_app.menu()

        plain_output = re.sub(r"\x1b\[[0-9;]*m", "", output.getvalue())
        numbers = [
            int(number)
            for number in re.findall(r"(?m)^\s*║\s*(\d+)\s{2}", plain_output)
        ]
        self.assertEqual(numbers, list(range(1, 14)))
        self.assertIn("3  New Employee", plain_output)

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

if __name__ == '__main__':
    unittest.main()
