from pypdf import PdfReader, PdfWriter # type: ignore
import pay_table as pt
import datetime as d
import os

class SheetWriter:    
    last_pos, first_pos = 6, 7 # SIX SEVEN!!! :3
    pay_pos = 5

    def __init__(self, input_file_name: str):
        self.writer = PdfWriter(input_file_name)
        self.page = self.writer.pages[0]

    def write_last(self, last_name: str):
        self.writer.update_page_form_field_values(self.page,{f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.last_pos}]": last_name})

    def write_first(self, first_name: str):
        self.writer.update_page_form_field_values(self.page,{f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.first_pos}]": first_name})

    def write_pay_period(self, pay_period: int):
        pay_table = pt.PayTable()
        self.writer.update_page_form_field_values(self.page, {f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.pay_pos}]":  f"{pay_period}: {pay_table.start_date_string(pay_period)} - {pay_table.end_date_string(pay_period)}"})

        days = (10, 14, 18, 22, 26, 30, 34, 75, 84, 85, 86, 87, 88, 89)

        for day, day_index in enumerate(days):
            self.writer.update_page_form_field_values(self.page, {f"topmostSubform[0].Page1[0].TextField1[{day_index}]":  pay_table.date_offset_string(pay_period, day)} )

    def output(self, output_file_name: str):
        self.writer.write(output_file_name)

    def output_timesheet(self, output_file_name: str):
        self.output(f"timesheets/{output_file_name}")

    def generate_fields(self):
        fields = self.writer.get_fields()

        with open("resources/fields.txt", "w") as field_file:
            for key in fields.keys():
                field_file.write(key + "\n")

    def view_fields_index(self):
        start = 0
        end = 151

        for i in range(start, end):
            self.writer.update_page_form_field_values(self.page, {f"topmostSubform[0].Page1[0].TextField1[{i}]":  i} )