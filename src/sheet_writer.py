from pypdf import PdfWriter
import pay_table as pt
import datetime as d
import schedule_table as st
import clock as c
import guide

class SheetWriter:
    """The SheetWriter class is the main way Socks creates your timesheet. It has various static constants
    that represent indices in the PDF. It uses methods like write_last_name() to write and create your sheet."""

    pay_table = pt.PayTable()
    schedule_table = st.ScheduleTable()

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
        '''Writes the person's last name to time the time sheet.'''

        last_name_field = SheetWriter.txt_field(guide.Indices.last_name_index.value)
        self.update_field(last_name_field, self.last_name.capitalize())

    def write_first_name(self):
        '''Write this person's first name to the time sheet.'''

        first_name_field = SheetWriter.txt_field(guide.Indices.first_name_index.value)
        self.update_field(first_name_field, self.first_name.capitalize())

    def write_pay_period(self):
        '''Writes the pay period to itme the time sheet.'''
        pay_period_field = SheetWriter.txt_field(guide.Indices.pay_period_index.value)
        pay_period_string = f"{self.pay_period}: {SheetWriter.pay_table.start_date_string(self.pay_period)} - {SheetWriter.pay_table.end_date_string(self.pay_period)}"
        self.update_field(pay_period_field, pay_period_string)

    def write_department(self):
        '''Writes the person's department to the time sheet.'''
        self.update_field(SheetWriter.txt_field(guide.Indices.dept_index.value), guide.LearningCenter.lc_dept_name.value)

    def write_pay(self):
        '''Writes the pay rate to the timesheet.'''
        self.update_field(SheetWriter.txt_field(guide.Indices.rate_index.value), guide.LearningCenter.lc_ca_rate.value)

    def write_department_number(self):
        self.update_field(SheetWriter.txt_field(guide.Indices.dept_num_index.value), guide.LearningCenter.lc_dept_num.value)

    def write_department_extension(self):
        self.update_field(SheetWriter.txt_field(guide.Indices.dept_ext_index.value), guide.LearningCenter.lc_dept_ext.value)

    def fill_top_section(self):
        '''Fills all 'boilerplate' of the timesheet.'''
        self.write_last_name()
        self.write_first_name()
        self.write_pay_period()
        self.write_department()
        self.write_pay()
        self.write_department_number()
        self.write_department_extension()

    def write_dates(self):
        '''Writes all fourteen days of the current pay period to the timesheet.'''

        for day, day_index in enumerate(guide.Indices.date_indices.value):
            date_field = SheetWriter.txt_field(day_index)
            date_string = pt.PayTable.date_str(self.dates[day])
            self.update_field(date_field, date_string)

    def write_hours(self):
        '''Writes all hours the person worked for both weeks in the timesheet.'''

        j = 0 
        k = 0 
        week_total = 0
        total_hours = 0
        invalid_dates = SheetWriter.pay_table.get_invalid_dates()

        for i in range(len(guide.Indices.time_in_out_indices.value)):

            date = self.dates[i]

            time_in_index = guide.Indices.time_in_out_indices.value[i][0]
            time_out_index = guide.Indices.time_in_out_indices.value[i][1]

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

                hours_worked_index = guide.Indices.hours_worked_indices.value[i]
                total_index = guide.Indices.total_indices.value[i]

                hours_worked_field = SheetWriter.txt_field(hours_worked_index)
                self.update_field(hours_worked_field, hours_worked_str)

                total_field = SheetWriter.txt_field(total_index)
                self.update_field(total_field, hours_worked_str)
                
            if j == 6:
                sub_total_index = guide.Indices.sub_totals_indices.value[k][0]
                sub_total_field = SheetWriter.txt_field(sub_total_index)

                self.update_field(sub_total_field, str(week_total))

                sub_total_index = guide.Indices.sub_totals_indices.value[k][1]
                sub_total_field = SheetWriter.txt_field(sub_total_index)

                self.update_field(sub_total_field, str(week_total))

                total_hours += week_total

                week_total = 0

                j = 0
                k = k + 1
            else:
                j = j + 1

        total_hours_field = SheetWriter.txt_field(guide.Indices.total_hours_index.value[0])
        self.update_field(total_hours_field, str(total_hours))

        total_hours_field = SheetWriter.txt_field(guide.Indices.total_hours_index.value[1])
        self.update_field(total_hours_field, str(total_hours))

    def write_timesheet(self):
        '''Writes the top part of the timesheet, the dates, and the hours, completing the time sheet.'''
        
        self.fill_top_section()
        self.write_dates()
        self.write_hours()

    def output_timesheet(self, output_file_name: str):
        '''Creates a file with the timesheet stored in PDF form.'''

        self.writer.write(f"timesheets/{output_file_name}")

    def generate_fields(self):
        '''Helper method to list all fields.'''

        fields = self.writer.get_fields()

        with open("resources/fields.txt", "w") as field_file:
            for key in fields.keys():
                field_file.write(key + "\n")

    def view_fields_index(self):
        '''Helper method that populates a timesheet with indexes.'''

        start = 0
        end = 151

        for i in range(start, end):
            self.writer.update_page_form_field_values(self.page, {f"topmostSubform[0].Page1[0].TextField1[{i}]":  i} )