from pypdf import PdfReader, PdfWriter # type: ignore
import pay_table as pt
import datetime as d
import schedule_table as st
import os

class SheetWriter:
    last_name_index, first_name_index = 6, 7 # SIX SEVEN!!! :3
    pay_period_index = 5

    week_one_date_indices = (10, 14, 18, 22, 26, 30, 34)
    week_one_time_in_out_indices = ((11, 13), (15,17), (19,21), (23, 25), (27, 29), (31, 33), (35, 37))

    week_two_date_indices = (75, 84, 85, 86, 87, 88, 89)
    week_two_time_in_out_indices = ((76, 78), (90, 102), (91, 103), (92, 104), (93, 105), (94, 106), (95, 107))

    time_in_out_indices = week_one_time_in_out_indices + week_two_time_in_out_indices
    date_indices = week_one_date_indices + week_two_date_indices

    pay_table = pt.PayTable()
    schedule_table = st.ScheduleTable()
    
    def __init__(self, input_file_name: str, last_name: str, first_name: str, pay_period: int):
        self.writer = PdfWriter(input_file_name)
        self.page = self.writer.pages[0]
        self.last_name = last_name
        self.first_name = first_name
        self.name = first_name + " " + last_name
        self.pay_period = pay_period

    def write_last_name(self):
        last_name_field = f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.last_name_index}]"
        self.writer.update_page_form_field_values(self.page,{last_name_field: self.last_name})

    def write_first_name(self):
        first_name_field = f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.first_name_index}]"
        self.writer.update_page_form_field_values(self.page,{first_name_field: self.first_name})

    def write_pay_period(self):
        pay_period_field = f"topmostSubform[0].Page1[0].TextField1[{SheetWriter.pay_period_index}]"
        pay_period_string = f"{self.pay_period}: {SheetWriter.pay_table.start_date_string(self.pay_period)} - {SheetWriter.pay_table.end_date_string(self.pay_period)}"
        self.writer.update_page_form_field_values(self.page, {pay_period_field: pay_period_string})

    def write_dates(self):
        for day, day_index in enumerate(SheetWriter.date_indices):
            date_field = f"topmostSubform[0].Page1[0].TextField1[{day_index}]"
            date_string = SheetWriter.pay_table.date_offset_string(self.pay_period, day)
            self.writer.update_page_form_field_values(self.page, {date_field: date_string})

    def write_hours(self):
        j = 0

        for i in range(len(SheetWriter.time_in_out_indices)):

            time_in_index = SheetWriter.time_in_out_indices[i][0]
            time_out_index = SheetWriter.time_in_out_indices[i][1]
            
            time_in_field = f"topmostSubform[0].Page1[0].TextField1[{time_in_index}]"
            time_out_field = f"topmostSubform[0].Page1[0].TextField1[{time_out_index}]"

            schedule = SheetWriter.schedule_table.get(self.name)

            time_in = schedule[j][0]
            time_out = schedule[j][1]

            self.writer.update_page_form_field_values(self.page, {time_in_field: time_in})
            self.writer.update_page_form_field_values(self.page, {time_out_field: time_out})

            j = 0 if (j == 6) else (j+1)
         
        # for i in range(len(SheetWriter.week_one_time_in_out_indices)):

        #     print(i, end=" ")

        #     time_in_index = SheetWriter.week_one_time_in_out_indices[i][0]
        #     time_out_index = SheetWriter.week_one_time_in_out_indices[i][1]
            
        #     time_in_field = f"topmostSubform[0].Page1[0].TextField1[{time_in_index}]"
        #     time_out_field = f"topmostSubform[0].Page1[0].TextField1[{time_out_index}]"

        #     schedule = SheetWriter.schedule_table.get(self.name)

        #     time_in = schedule[i][0]
        #     time_out = schedule[i][1]

        #     self.writer.update_page_form_field_values(self.page, {time_in_field: time_in})
        #     self.writer.update_page_form_field_values(self.page, {time_out_field: time_out})

        # print("\n")

        # for j in range(len(SheetWriter.week_two_time_in_out_indices)):

        #     print(j, end=" ")

        #     time_in_index = SheetWriter.week_two_time_in_out_indices[j][0]
        #     time_out_index = SheetWriter.week_two_time_in_out_indices[j][1]

        #     time_in_field = f"topmostSubform[0].Page1[0].TextField1[{time_in_index}]"
        #     time_out_field = f"topmostSubform[0].Page1[0].TextField1[{time_out_index}]"

        #     schedule = SheetWriter.schedule_table.get(self.name)

        #     time_in = schedule[j][0]
        #     time_out = schedule[j][1]

        #     self.writer.update_page_form_field_values(self.page, {time_in_field: time_in})
        #     self.writer.update_page_form_field_values(self.page, {time_out_field: time_out})

    def write_timesheet(self):
        self.write_last_name()
        self.write_first_name()
        self.write_pay_period()
        self.write_dates()
        self.write_hours()

    def output_timesheet(self, output_file_name: str):
        self.writer.write(f"timesheets/{output_file_name}")

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