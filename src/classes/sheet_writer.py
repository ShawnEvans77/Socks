import datetime as d, structures.clock as c, modules.guide as guide, modules.filenames as filenames
from pypdf import PdfWriter

class SheetWriter:
    """The SheetWriter class is the main way Socks creates your timesheet. It has various static constants
    that represent indices in the PDF. It uses methods like write_last_name() to write and create your sheet."""

    def __init__(self, input_file_name: str, last_name: str, first_name: str, pay_period: int):
        self.writer = PdfWriter(input_file_name)
        self.page = self.writer.pages[0]
        self.last_name = last_name
        self.first_name = first_name
        self.name = first_name + " " + last_name
        self.pay_period = pay_period
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
        pay_period_string = f"{self.pay_period}: {guide.Tables.pay_table.value.start_date_string(self.pay_period)} - {guide.Tables.pay_table.value.end_date_string(self.pay_period)}"
        self.update_field(pay_period_field, pay_period_string)

    def write_department(self):
        '''Writes the person's department to the time sheet.'''

        self.update_field(SheetWriter.txt_field(guide.Indices.dept_index.value), guide.LearningCenter.lc_dept_name.value)

    def write_pay(self):
        '''Writes the pay rate to the timesheet.'''

        self.update_field(SheetWriter.txt_field(guide.Indices.rate_index.value), guide.LearningCenter.lc_ca_rate.value)

    def write_department_number(self):
        '''Writes the Department Number to the timesheet.'''

        self.update_field(SheetWriter.txt_field(guide.Indices.dept_num_index.value), guide.LearningCenter.lc_dept_num.value)

    def write_department_extension(self):
        '''Writes the Department Extension to the timesheet.'''

        self.update_field(SheetWriter.txt_field(guide.Indices.dept_ext_index.value), guide.LearningCenter.lc_dept_ext.value)

    def write_dates(self):
        '''Writes all fourteen days of the current pay period to the timesheet.'''

        for day, day_index in enumerate(guide.Indices.date_indices.value):
            date_field = SheetWriter.txt_field(day_index)
            date_string = guide.Tables.pay_table.value.date_str(self.dates[day])
            self.update_field(date_field, date_string)

    def write_hours(self):
        '''Writes all hours the person worked for both weeks in the timesheet.'''

        j = 0 
        k = 0 
        week_total = 0
        total_hours = 0
        invalid_dates = guide.Tables.pay_table.value.get_invalid_dates()
        missed_days = guide.Tables.schedule_table.value.get_missed_days(self.name)

        for i in range(len(guide.Indices.time_in_out_indices.value)):

            date = self.dates[i]

            time_in_index = guide.Indices.time_in_out_indices.value[i][0]
            time_out_index = guide.Indices.time_in_out_indices.value[i][1]

            time_in_field = SheetWriter.txt_field(time_in_index)
            time_out_field = SheetWriter.txt_field(time_out_index)

            schedule = guide.Tables.schedule_table.value.get(self.name)

            time_in = schedule[j][0]
            time_out = schedule[j][1]

            if len(time_in) != 0 and date not in invalid_dates and date not in missed_days:

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

    def output_timesheet(self, output_file_name: str):
        '''Creates a file with the timesheet stored in PDF form.'''

        self.writer.write(f"{filenames.output_folder}/{output_file_name}")