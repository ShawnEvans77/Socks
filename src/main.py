import sheet_writer, guide, filenames, datetime

def retrieve_pay_period(pay_dict: dict) -> str:
    now = datetime.datetime.now()
    items = pay_dict.items()

    for pay_period, dates in items:
         if dates[0] <= now <= dates[1]:
             return pay_period
            
    return None

def main():
    print("*********************************************************")
    print("(🧦) Welcome to Socks (🧦)\n")

    first_name = input("Please enter your first name: ").lower()
    last_name = input("Please enter your last name: ").lower()

    while not guide.Tables.schedule_table.value.has_name(f"{first_name} {last_name}"):
        print(f"ERROR: Socks currently has no employee called {first_name.title()} {last_name.title()}. Try again.")
        first_name = input("Please enter your first name: ").lower()
        last_name = input("Please enter your last name: ").lower()

    choice = input("Do you want to select the pay period based on the system time? (y/n): ").lower()

    while choice != "y" and choice != "n":
        print("ERROR: Choice must be y or n.")
        choice = input("Do you want to select the pay period based on the system time? (y/n): ").lower()

    if choice == "y":
        if pay_period := retrieve_pay_period(guide.Tables.pay_table.value.get_pay_dict()):
            pay_period = int(pay_period)
            print(f"Socks has determined the current pay period is {pay_period}, starting at {guide.Tables.pay_table.value.start_date_string(pay_period)} and ending at {guide.Tables.pay_table.value.end_date_string(pay_period)}.")
        else:
            print("Unfournately, the system time does not exist within Socks' pay periods. Please enter the pay period manually.")

    if choice == "n" or not pay_period:

        pay_period = input("Please enter the pay period: ")

        while not pay_period.isnumeric():
            print("ERROR: Pay Period must be a number. Try again.")
            pay_period = input("Please enter the pay period: ")

        while not guide.Tables.pay_table.value.has_pay_period(pay_period):
            print(f"ERROR: Socks currently has no pay period {pay_period}. Try again.")
            pay_period = input("Please enter the pay period: ")

        pay_period = int(pay_period)

    print("*********************************************************")

    input_path = f"{filenames.asset_folder}/{filenames.pdf_input_folder}"
    input_file_name = f"{filenames.starting_pdf}"

    sheet = sheet_writer.SheetWriter(f"{input_path}/{input_file_name}", last_name, first_name, pay_period)

    sheet.write_timesheet()

    file_name = f"{last_name.capitalize()}_Timesheet_{pay_period}.pdf"
    
    sheet.output_timesheet(file_name)

    print(f"{first_name.capitalize()}, your timesheet has been generated in the timesheet folder.")
    print(f"\nThank you for using (🧦) Socks (🧦)!")
    print("*********************************************************")

if __name__ == '__main__':
    main()