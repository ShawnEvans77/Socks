
from pypdf import PdfReader, PdfWriter # type: ignore
import os

writer = PdfWriter("init.pdf")
page = writer.pages[0]

name = input("Please enter your name: ")

pay_period = input("Please enter the pay period: ")




week_one = [10, 14, 18, 22, 26, 30, 34]
week_two = [75, 84, 85, 86, 87, 88, 89]


# fields = writer.get_fields()

name = input("Please enter your name: ")
writer.update_page_form_field_values(page,{f"topmostSubform[0].Page1[0].TextField1[7]": "Shawn Evans"},auto_regenerate=True,)


writer.write("timesheet.pdf")

os.startfile("timesheet.pdf")