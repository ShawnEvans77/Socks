import sheet_writer as sw
from pypdf import PdfWriter # type: ignore
import os

def main():
    print("*********************************************************")
    print("(🧦) Welcome to Socks (🧦)\n")

    first_name = input("Please enter your first name: ").lower()
    last_name = input("Please enter your last name: ").lower()
    pay_period = int(input("Please enter the pay period: "))
    print("*********************************************************")


    input_path = "resources/pdf input"
    input_file_name = "init.pdf"

    sheet = sw.SheetWriter(f"{input_path}/{input_file_name}", last_name, first_name, pay_period)

    sheet.write_timesheet()

    file_name = f"{last_name.capitalize()}_Timesheet_{pay_period}.pdf"
    
    sheet.output_timesheet(file_name)

if __name__ == '__main__':
    main()