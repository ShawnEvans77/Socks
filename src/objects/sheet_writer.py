from ..constants import guide, filenames
from ..constants.schedule import DAYS_PER_WEEK, weekday_index
from ..objects import clock
from ..utils.database import normalize_shift_segments
from io import BytesIO
from pypdf import PdfReader, PdfWriter

class SheetWriter:
    """Populate and flatten the employee timesheet PDF."""

    def __init__(
        self, input_file_name: str, last_name: str, first_name: str,
        pay_period: int, emplid: str
    ):
        self.writer = PdfWriter(input_file_name)
        self.page = self.writer.pages[0]
        self.last_name = last_name
        self.first_name = first_name
        self.name = first_name + " " + last_name
        self.pay_period = pay_period
        self.emplid = emplid.strip()
        self.split_shift_cells = []
        if not self.emplid or not (self.emplid.isascii() and self.emplid.isdigit()):
            raise ValueError("EMPLID is required and must contain digits only.")
        self.dates = guide.Tables.pay_table.value.get_period_dates(self.pay_period)

    def write_timesheet(self):
        '''Writes all needed information on the timesheet.'''

        self.write_last_name()
        self.write_first_name()
        self.write_pay_period()
        self.write_department()
        self.write_pay()
        self.write_department_number()
        self.write_department_extension()
        self.write_dates()
        self.write_hours()
        self.write_ca_checkbox()
        self.flatten_form()
        self.write_split_shift_overlays()
        self.write_emplid()
        self.write_prepared_by()

    def write_ca_checkbox(self):
        """Select the College Assistant checkbox in the template."""
        self.writer.update_page_form_field_values(
            self.page,
            {guide.Indices.ca_checkbox_name.value: "/1"},
            auto_regenerate=False,
        )

    def flatten_form(self):
        """Paint all field appearances into the page and remove editable widgets."""
        import re
        from pypdf.generic import NameObject
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfgen import canvas

        width = float(self.page.mediabox.width)
        height = float(self.page.mediabox.height)
        overlay_buffer = BytesIO()
        overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=(width, height))
        overlay_canvas.setFillColorRGB(0, 0, 0)
        ca_rect = None

        for annotation in self.page.get("/Annots", []):
            widget = annotation.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue

            if widget.get("/T") == "CheckBox1[0]":
                ca_rect = tuple(float(value) for value in widget["/Rect"])
                continue
            if widget.get("/FT") != "/Tx":
                continue

            value = widget.get("/V")
            if not value:
                continue
            text = str(value)
            x0, y0, x1, y1 = (float(number) for number in widget["/Rect"])
            default_appearance = str(widget.get("/DA", ""))
            match = re.search(r"/[^\s]+\s+([\d.]+)\s+Tf", default_appearance)
            font_size = float(match.group(1)) if match else 10
            available_width = x1 - x0 - 4
            while font_size > 5 and pdfmetrics.stringWidth(
                text, "Helvetica", font_size
            ) > available_width:
                font_size -= 0.25
            if pdfmetrics.stringWidth(text, "Helvetica", font_size) > available_width:
                raise ValueError(f"Text does not fit in PDF field {widget.get('/T')}.")

            ascent, descent = pdfmetrics.getAscentDescent("Helvetica", font_size)
            baseline = (y0 + y1) / 2 - (ascent + descent) / 2
            overlay_canvas.setFont("Helvetica", font_size)
            alignment = int(widget.get("/Q", 0))
            if alignment == 1:
                overlay_canvas.drawCentredString((x0 + x1) / 2, baseline, text)
            elif alignment == 2:
                overlay_canvas.drawRightString(x1 - 2, baseline, text)
            else:
                overlay_canvas.drawString(x0 + 2, baseline, text)

        if ca_rect is None:
            raise ValueError("CA checkbox was not found in the PDF template.")
        x0, y0, x1, y1 = ca_rect
        overlay_canvas.setLineWidth(0.8)
        overlay_canvas.line(x0 + 2, y0 + 2, x1 - 2, y1 - 2)
        overlay_canvas.line(x0 + 2, y1 - 2, x1 - 2, y0 + 2)
        overlay_canvas.save()
        overlay_buffer.seek(0)
        self.page.merge_page(PdfReader(overlay_buffer).pages[0])

        self.writer.remove_annotations(subtypes="/Widget")
        self.writer.root_object.pop(NameObject("/AcroForm"), None)

    def write_emplid(self):
        """Draw the required EMPLID over its printed line on the form."""

        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas

        width = float(self.page.mediabox.width)
        height = float(self.page.mediabox.height)
        overlay_buffer = BytesIO()
        overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=(width, height))
        font_name = "Helvetica"
        font_size = 10
        line_left = 172
        line_width = 149
        text_width = stringWidth(self.emplid, font_name, font_size)
        text_x = line_left + max(0, (line_width - text_width) / 2)

        overlay_canvas.setFont(font_name, font_size)
        overlay_canvas.setFillColorRGB(0, 0, 0)
        overlay_canvas.drawString(text_x, 554.5, self.emplid)
        overlay_canvas.save()

        overlay_buffer.seek(0)
        self.page.merge_page(PdfReader(overlay_buffer).pages[0])

    def write_prepared_by(self):
        """Print the employee's full name on the Prepared by line."""
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.pdfgen import canvas

        width = float(self.page.mediabox.width)
        height = float(self.page.mediabox.height)
        name = f"{self.first_name.capitalize()} {self.last_name.capitalize()}"
        line_left, line_width, baseline = 28.8, 155.2, 63.5
        text_width = stringWidth(name, "Helvetica", 10)
        overlay_buffer = BytesIO()
        overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=(width, height))
        overlay_canvas.setFont("Helvetica", 10)
        overlay_canvas.setFillColorRGB(0, 0, 0)
        overlay_canvas.drawString(
            line_left + (line_width - text_width) / 2, baseline, name
        )
        overlay_canvas.save()

        overlay_buffer.seek(0)
        self.page.merge_page(PdfReader(overlay_buffer).pages[0])

    @staticmethod
    def txt_field(index: int) -> str:
        """Build the PDF form field path for a text field index."""
        return f"topmostSubform[0].Page1[0].TextField1[{index}]"

    def update_field(self, field: str, text: str):
        """Write text into a named PDF form field."""

        self.writer.update_page_form_field_values(self.page, {field: text})

    def write_last_name(self):
        '''Writes the person's last name to time the time sheet.'''

        last_name_field = SheetWriter.txt_field(guide.Indices.last_name_index.value)
        self.update_field(last_name_field, self.last_name.capitalize())

    def write_first_name(self):
        '''Write this person's first name to the time sheet.'''

        first_name_field = SheetWriter.txt_field(guide.Indices.first_name_index.value)
        self.update_field(first_name_field, self.first_name.capitalize())

    def write_pay_period(self):
        """Write the pay period and its date range."""
        pay_table = guide.Tables.pay_table.value
        pay_period_field = SheetWriter.txt_field(
            guide.Indices.pay_period_index.value
        )
        pay_period_string = (
            f"{self.pay_period}: {pay_table.start_date_string(self.pay_period)} - "
            f"{pay_table.end_date_string(self.pay_period)}"
        )
        self.update_field(pay_period_field, pay_period_string)

    def write_department(self):
        """Write the employee's department."""
        self._write_guide_field(
            guide.Indices.dept_index.value, guide.LearningCenter.lc_dept_name.value
        )

    def write_pay(self):
        """Write the employee's pay rate."""
        self._write_guide_field(
            guide.Indices.rate_index.value, guide.LearningCenter.lc_ca_rate.value
        )

    def write_department_number(self):
        """Write the department number."""
        budget = guide.Tables.schedule_table.value.get_budget(self.name)
        department_number = f"{guide.LearningCenter.lc_dept_prefix.value}-{budget}"
        self._write_guide_field(
            guide.Indices.dept_num_index.value, department_number
        )

    def write_department_extension(self):
        """Write the department extension."""
        self._write_guide_field(
            guide.Indices.dept_ext_index.value, guide.LearningCenter.lc_dept_ext.value
        )

    def _write_guide_field(self, index: int, value: str) -> None:
        self.update_field(SheetWriter.txt_field(index), value)

    def write_dates(self):
        '''Writes all fourteen days of the current pay period to the timesheet.'''

        for day, day_index in enumerate(guide.Indices.date_indices.value):
            date_field = SheetWriter.txt_field(day_index)
            date_string = guide.Tables.pay_table.value.date_str(self.dates[day])
            self.update_field(date_field, date_string)

    def write_hours(self):
        schedule_table = guide.Tables.schedule_table.value
        schedule = schedule_table.get(self.name)
        invalid_dates = set(guide.Tables.pay_table.value.get_invalid_dates())
        missed_days = schedule_table.get_missed_days(self.name)
        missed_split_shifts = schedule_table.get_missed_split_shifts(self.name)
        extra_days = schedule_table.get_extra_days(self.name)
        week_totals = [0.0] * len(guide.Indices.sub_totals_indices.value)

        for index, date in enumerate(self.dates):
            segments, worked = self._segments_for_date(
                date,
                schedule[weekday_index(date)],
                invalid_dates,
                missed_days,
                missed_split_shifts,
                extra_days,
            )
            if not worked:
                continue

            hours = round(
                sum(clock.Clock(start) - clock.Clock(end) for start, end in segments),
                2,
            )
            week_totals[index // DAYS_PER_WEEK] += hours
            self._write_worked_day(index, segments, hours)

        self._write_totals(week_totals)

    @staticmethod
    def _segments_for_date(
        date, scheduled_segments, invalid_dates, missed_days,
        missed_split_shifts, extra_days,
    ):
        extra_shift = extra_days.get(date)
        if extra_shift:
            return list(normalize_shift_segments(extra_shift)), True

        missed_segments = missed_split_shifts.get(date, set())
        segments = [
            tuple(segment) for segment in scheduled_segments
            if tuple(segment) not in missed_segments
        ]
        worked = bool(segments) and date not in invalid_dates and date not in missed_days
        return segments, worked

    def _write_worked_day(self, index: int, segments, hours: float) -> None:
        time_in_index, time_out_index = guide.Indices.time_in_out_indices.value[index]
        time_in_field = SheetWriter.txt_field(time_in_index)
        time_out_field = SheetWriter.txt_field(time_out_index)

        if len(segments) == 1:
            self.update_field(time_in_field, segments[0][0])
            self.update_field(time_out_field, segments[0][1])
        else:
            self.update_field(time_in_field, "")
            self.update_field(time_out_field, "")
            meal_index = guide.Indices.meal_period_indices.value[index]
            self.update_field(SheetWriter.txt_field(meal_index), "")
            self.split_shift_cells.append(
                (
                    self._field_rect(time_in_index),
                    self._field_rect(time_out_index),
                    tuple(segments),
                )
            )

        hours_text = f"{hours:g}"
        self.update_field(
            SheetWriter.txt_field(guide.Indices.hours_worked_indices.value[index]),
            hours_text,
        )
        self.update_field(
            SheetWriter.txt_field(guide.Indices.total_indices.value[index]),
            hours_text,
        )

    def _write_totals(self, week_totals: list[float]) -> None:
        for total, indices in zip(week_totals, guide.Indices.sub_totals_indices.value):
            for index in indices:
                self.update_field(SheetWriter.txt_field(index), f"{total:g}")

        total_hours = sum(week_totals)
        for index in guide.Indices.total_hours_index.value:
            self.update_field(SheetWriter.txt_field(index), f"{total_hours:g}")

    def write_split_shift_overlays(self):
        """Draw paired times diagonally in the Time In and Time Out cells."""
        if not self.split_shift_cells:
            return

        from reportlab.pdfgen import canvas

        width = float(self.page.mediabox.width)
        height = float(self.page.mediabox.height)
        overlay_buffer = BytesIO()
        overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=(width, height))
        overlay_canvas.setFillColorRGB(0, 0, 0)
        overlay_canvas.setStrokeColorRGB(0, 0, 0)
        overlay_canvas.setLineWidth(0.65)

        for time_in_rect, time_out_rect, segments in self.split_shift_cells:
            starts = [segment[0] for segment in segments]
            ends = [segment[1] for segment in segments]
            self._draw_diagonal_times(
                overlay_canvas, time_in_rect, starts
            )
            self._draw_diagonal_times(
                overlay_canvas, time_out_rect, ends
            )

        overlay_canvas.save()
        overlay_buffer.seek(0)
        self.page.merge_page(PdfReader(overlay_buffer).pages[0])

    def _field_rect(self, index: int) -> tuple[float, float, float, float]:
        target = SheetWriter.txt_field(index)
        leaf_name = target.rsplit(".", 1)[-1]
        for annotation in self.page.get("/Annots", []):
            field = annotation.get_object()
            if field.get("/T") in (target, leaf_name):
                return tuple(float(value) for value in field["/Rect"])
        raise ValueError(f"PDF field {target} was not found.")

    @staticmethod
    def _draw_diagonal_times(overlay_canvas, rect, times):
        from reportlab.pdfbase.pdfmetrics import stringWidth

        x0, y0, x1, y1 = rect
        available_width = x1 - x0 - 5
        labels = list(times)
        font_size = 7.0
        while font_size > 5.0 and max(
            stringWidth(label, "Helvetica-Bold", font_size) for label in labels
        ) > available_width:
            font_size -= 0.25
        if max(
            stringWidth(label, "Helvetica-Bold", font_size) for label in labels
        ) > available_width:
            raise ValueError("A split-shift time label does not fit in its PDF cell.")

        overlay_canvas.line(x0 + 1, y0 + 0.5, x1 - 1, y1 - 2)
        overlay_canvas.setFont("Helvetica-Bold", font_size)
        first_width = stringWidth(labels[0], "Helvetica-Bold", font_size)
        first_x, first_y = x0 + 2, y1 - font_size - 1.5
        second_width = stringWidth(labels[1], "Helvetica-Bold", font_size)
        second_x, second_y = x1 - second_width - 2, y0 + 2.5
        overlay_canvas.setFillColorRGB(1, 1, 1)
        for x, y, text_width in (
            (first_x, first_y, first_width),
            (second_x, second_y, second_width),
        ):
            overlay_canvas.rect(x - 0.5, y - 0.5, text_width + 1, font_size + 1, fill=1, stroke=0)
        overlay_canvas.setFillColorRGB(0, 0, 0)
        overlay_canvas.drawString(first_x, first_y, labels[0])
        overlay_canvas.drawString(second_x, second_y, labels[1])

    def output_timesheet(self, output_file_name: str):
        '''Creates a file with the timesheet stored in PDF form.'''

        self.writer.write(f"{filenames.output_folder}/{output_file_name}")
