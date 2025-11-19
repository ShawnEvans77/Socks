
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

writer.write("timesheet.pdf")
os.startfile("timesheet.pdf")