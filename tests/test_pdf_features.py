import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from tests.support import (
    FakePayTable,
    FakeScheduleTable,
    SheetWriter,
    filenames,
    guide,
    use_guide_tables,
    weekly_schedule,
)


class PdfFeatureTests(unittest.TestCase):
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

    def test_output_creates_missing_timesheets_folder(self):
        missing = Path(self.tmp.name) / "not-made-yet"
        with use_guide_tables(FakePayTable(), FakeScheduleTable(schedule=weekly_schedule())), \
             patch.object(filenames, "output_folder", str(missing)):
            sheet = self.make_writer()
            sheet.write_timesheet()
            sheet.output_timesheet("Evans_Timesheet_1.pdf")

        self.assertTrue((missing / "Evans_Timesheet_1.pdf").read_bytes().startswith(b"%PDF"))

    def test_split_shift_pdf_has_visible_labels_and_is_not_editable(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        pay_table = FakePayTable()
        schedule_table = FakeScheduleTable(schedule=schedule, budget=72)
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
            "885-72",
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

    def test_missed_split_interval_displays_remaining_interval_as_single_shift(self):
        schedule = weekly_schedule()
        schedule[4] = [("12PM", "2PM"), ("2:15PM", "3:15PM")]
        schedule_table = FakeScheduleTable(schedule=schedule)
        missed_date = dt.datetime(2026, 4, 9)
        schedule_table.add_missed_split_shifts(
            "Shawn Evans", {missed_date: {("12PM", "2PM")}}
        )

        with use_guide_tables(FakePayTable(), schedule_table):
            sheet = self.make_writer()
            with patch.object(sheet, "update_field", wraps=sheet.update_field) as update_field:
                sheet.write_hours()

        first_thursday_in = SheetWriter.txt_field(
            guide.Indices.time_in_out_indices.value[4][0]
        )
        first_thursday_out = SheetWriter.txt_field(
            guide.Indices.time_in_out_indices.value[4][1]
        )
        self.assertIn(call(first_thursday_in, "2:15PM"), update_field.call_args_list)
        self.assertIn(call(first_thursday_out, "3:15PM"), update_field.call_args_list)
        self.assertEqual(len(sheet.split_shift_cells), 1)
        self.assertEqual(
            schedule_table.schedule[4],
            [("12PM", "2PM"), ("2:15PM", "3:15PM")],
        )

    def test_extra_split_day_is_written_as_split_hours(self):
        schedule_table = FakeScheduleTable()
        date = dt.datetime(2026, 4, 9)
        schedule_table.add_extra_days(
            "Shawn Evans",
            {date: [("12PM", "2PM"), ("2:15PM", "3:15PM")]},
        )

        with use_guide_tables(FakePayTable(), schedule_table):
            sheet = self.make_writer()
            with patch.object(sheet, "update_field", wraps=sheet.update_field) as update_field:
                sheet.write_hours()

        time_in = SheetWriter.txt_field(guide.Indices.time_in_out_indices.value[4][0])
        time_out = SheetWriter.txt_field(guide.Indices.time_in_out_indices.value[4][1])
        hours = SheetWriter.txt_field(guide.Indices.hours_worked_indices.value[4])
        self.assertIn(call(time_in, ""), update_field.call_args_list)
        self.assertIn(call(time_out, ""), update_field.call_args_list)
        self.assertIn(call(hours, "3"), update_field.call_args_list)
        self.assertEqual(
            sheet.split_shift_cells[0][2],
            (("12PM", "2PM"), ("2:15PM", "3:15PM")),
        )

if __name__ == '__main__':
    unittest.main()
