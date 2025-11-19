import sheet_writer as sw
from pypdf import PdfWriter # type: ignore

def main():
    sheet = sw.SheetWriter("resources/pdf input/init.pdf")

    print("************************************************")
    last = input("Please enter your last name: ")
    sheet.write_last(last)

    first = input("Please enter your first name: ")
    sheet.write_first(first)

    pay_period = input("Please enter the pay period: ")
    sheet.write_pay_period(pay_period)
    print("************************************************")

    sheet.output_timesheet(f"{last}_Timesheet_{pay_period}.pdf")

if __name__ == '__main__':
    main()