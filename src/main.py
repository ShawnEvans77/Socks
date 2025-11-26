import sheet_writer as sw
from pypdf import PdfWriter # type: ignore
import os

def main():
    print("************************************************")

    last_name = input("Please enter your last name: ")
    first_name = input("Please enter your first name: ")
    pay_period = int(input("Please enter the pay period: "))

    print("************************************************")

    input_path = "resources/pdf input"
    input_file_name = "init.pdf"

    sheet = sw.SheetWriter(f"{input_path}/{input_file_name}", last_name, first_name, pay_period)

    sheet.write_timesheet()
    
    sheet.output_timesheet(f"{last_name}_Timesheet_{pay_period}.pdf")

if __name__ == '__main__':
    main()