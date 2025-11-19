
from pypdf import PdfReader, PdfWriter # type: ignore
import os

reader = PdfReader("init.pdf")
writer = PdfWriter()

writer.append(reader)
writer.set_need_appearances_writer(True)
page = writer.pages[0]
fields = writer.get_fields()

writer.update_page_form_field_values(page,{f"topmostSubform[0].Page1[0].TextField1[7]": "Shawn Evans"},auto_regenerate=True,)
writer.update_page_form_field_values(page,{f"topmostSubform[0].Page1[0].TextField1[84]": "11/28"},auto_regenerate=True,)
# writer.update_page_form_field_values(page, fields, flatten=True)
# writer.remove_annotations(subtypes="/Widget")

writer.write("timesheet.pdf")

os.startfile("timesheet.pdf")

# sun = 10
# mon = 14
# tues = 18
# wed = 22
# thurs = 26
# fri = 30
# sat = 34

# sun = 75
# mon = 84
# tues = 85
# wed = 86
# thurs = 87
# fri = 88
# sat = 89