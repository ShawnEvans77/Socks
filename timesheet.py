
import os
import sheet_writer as sw
from pypdf import PdfWriter # type: ignore

writer = PdfWriter("init.pdf")
page = writer.pages[0]

sheet = sw.SheetWriter(writer, page)

last = input("Please enter your last name: ")
sheet.write_last(last)

first = input("Please enter your first name: ")
sheet.write_first(first)

pay_period = input("Please enter the pay period: ")
sheet.write_pay_period(pay_period)

# # week_one = [10, 14, 18, 22, 26, 30, 34]
# # week_two = [75, 84, 85, 86, 87, 88, 89]

writer.write("timesheet.pdf")
os.startfile("timesheet.pdf")