
import os
import sheet_writer as sw
from pypdf import PdfWriter # type: ignore

def main():
    writer = PdfWriter("resources/init.pdf")
    page = writer.pages[0]

    sheet = sw.SheetWriter(writer, page)

    print("************************************************")
    last = input("Please enter your last name: ")
    sheet.write_last(last)

    first = input("Please enter your first name: ")
    sheet.write_first(first)

    pay_period = input("Please enter the pay period: ")
    sheet.write_pay_period(pay_period)
    print("************************************************")

    writer.write("timesheet.pdf")
    os.startfile("timesheet.pdf")

if __name__ == '__main__':
    main()