from pypdf import PdfWriter
import pay_table as pt
import datetime as d
import schedule_table as st
import clock as c

class SheetWriter:
    """The SheetWriter class is the main way Socks creates your timesheet. It has various static constants
    that represent indices in the PDF. It uses methods like write_last_name() to write and create your sheet."""

    pay_table = pt.PayTable()
    schedule_table = st.ScheduleTable()

    last_name_index, first_name_index = 6, 7 # SIX SEVEN!!! :3
    pay_period_index = 5

    sub_totals_indices = ((74, 73), (132,137))
    total_hours_index = (138, 141)

    week_one_date_indices = (10, 14, 18, 22, 26, 30, 34)
    week_two_date_indices = (75, 84, 85, 86, 87, 88, 89)
    date_indices = week_one_date_indices + week_two_date_indices

    week_one_time_in_out_indices = ((11, 13), (15,  17), (19,21),   (23, 25),  (27, 29),  (31, 33), (35, 37))
    week_two_time_in_out_indices = ((76, 78), (90, 102), (91, 103), (92, 104), (93, 105), (94, 106),  (95, 107))
    time_in_out_indices = week_one_time_in_out_indices + week_two_time_in_out_indices

    week_one_total_indices = (59, 60, 61, 62, 63, 64, 65)
    week_two_total_indices = (82, 126, 127, 128, 129, 130, 131)
    total_indices = week_one_total_indices + week_two_total_indices

    week_one_hours_worked = (45, 46, 47, 48, 49, 50, 51)
    week_two_hours_worked = (79, 108, 109, 110, 111, 112, 113)
    hours_worked_indices = week_one_hours_worked + week_two_hours_worked
    
    def __init__(self, input_file_name: str, last_name: str, first_name: str, pay_period: int):
        self.writer = PdfWriter(input_file_name)
        self.page = self.writer.pages[0]
        self.last_name = last_name
        self.first_name = first_name
        self.name = first_name + " " + last_name
        self.pay_period = pay_period
        self.dates = SheetWriter.pay_table.get_period_dates(self.pay_period)

    @staticmethod
    def txt_field(index: int) -> str:
        """A getter method to allow us to access a text field based on index. This function call
        will make your life easier, you don't need to write {topmost...} all the time."""

        return f"topmostSubform[0].Page1[0].TextField1[{index}]"
    
    def update_field(self, field: str, text: str):
        """Writes the given text data into the given field. Method exists to make updating much easier,
        rather than the excessively long {update_page...} function."""

        self.writer.update_page_form_field_values(self.page,{field: text})

    def write_last_name(self):
        last_name_field = SheetWriter.txt_field(SheetWriter.last_name_index)
        self.update_field(last_name_field, self.last_name.capitalize())

    def write_first_name(self):
        first_name_field = SheetWriter.txt_field(SheetWriter.first_name_index)
        self.update_field(first_name_field, self.first_name.capitalize())

    def write_pay_period(self):
        pay_period_field = SheetWriter.txt_field(SheetWriter.pay_period_index)
        pay_period_string = f"{self.pay_period}: {SheetWriter.pay_table.start_date_string(self.pay_period)} - {SheetWriter.pay_table.end_date_string(self.pay_period)}"
        self.update_field(pay_period_field, pay_period_string)

    def write_department(self):
        self.update_field(SheetWriter.txt_field(9), "Learning Center")
        self.update_field(SheetWriter.txt_field(1), "885-01")
        self.update_field(SheetWriter.txt_field(2), "19.12")
        self.update_field(SheetWriter.txt_field(151), "5821")

    def write_dates(self):

        for day, day_index in enumerate(SheetWriter.date_indices):
            date_field = SheetWriter.txt_field(day_index)
            date_string = pt.PayTable.date_str(self.dates[day])
            self.update_field(date_field, date_string)

    def write_hours(self):
        j = 0 
        k = 0 
        week_total = 0
        total_hours = 0
        invalid_dates = SheetWriter.pay_table.get_invalid_dates()

        for i in range(len(SheetWriter.time_in_out_indices)):

            date = self.dates[i]

            time_in_index = SheetWriter.time_in_out_indices[i][0]
            time_out_index = SheetWriter.time_in_out_indices[i][1]

            time_in_field = SheetWriter.txt_field(time_in_index)
            time_out_field = SheetWriter.txt_field(time_out_index)

            schedule = SheetWriter.schedule_table.get(self.name)

            time_in = schedule[j][0]
            time_out = schedule[j][1]

            if len(time_in) != 0 and date not in invalid_dates:

                hours_worked_int = c.Clock(time_in) - c.Clock(time_out)
                hours_worked_str = str(hours_worked_int)

                week_total += hours_worked_int

                self.update_field(time_in_field, time_in)
                self.update_field(time_out_field, time_out)

                hours_worked_index = SheetWriter.hours_worked_indices[i]
                total_index = SheetWriter.total_indices[i]

                hours_worked_field = SheetWriter.txt_field(hours_worked_index)
                self.update_field(hours_worked_field, hours_worked_str)

                total_field = SheetWriter.txt_field(total_index)
                self.update_field(total_field, hours_worked_str)
                
            if j == 6:
                sub_total_index = SheetWriter.sub_totals_indices[k][0]
                sub_total_field = SheetWriter.txt_field(sub_total_index)

                self.update_field(sub_total_field, str(week_total))

                sub_total_index = SheetWriter.sub_totals_indices[k][1]
                sub_total_field = SheetWriter.txt_field(sub_total_index)

                self.update_field(sub_total_field, str(week_total))

                total_hours += week_total

                week_total = 0

                j = 0
                k = k + 1
            else:
                j = j + 1

        total_hours_field = SheetWriter.txt_field(SheetWriter.total_hours_index[0])
        self.update_field(total_hours_field, str(total_hours))

        total_hours_field = SheetWriter.txt_field(SheetWriter.total_hours_index[1])
        self.update_field(total_hours_field, str(total_hours))

    def write_timesheet(self):
        self.write_last_name()
        self.write_first_name()
        self.write_pay_period()
        self.write_department()
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