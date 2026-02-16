import sheet_writer, guide, filenames, datetime

def valid_period(pay_period: str) -> bool:
    return pay_period.isnumeric() and (guide.PeriodLength.first_period.value <= int(pay_period) <= guide.PeriodLength.last_period.value) and guide.Tables.pay_table.value.has_pay_period(pay_period)

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

    first_name = input("Please enter your first name: ").lower().strip()
    last_name = input("Please enter your last name: ").lower().strip()

    while not guide.Tables.schedule_table.value.has_name(f"{first_name} {last_name}"):
        print(f"ERROR: Socks currently has no employee called {first_name.title()} {last_name.title()}. Try again.")
        first_name = input("Please enter your first name: ").lower()
        last_name = input("Please enter your last name: ").lower()

    choice = input("\nAutomatically select pay period? (y/n): ").lower().strip()

    while choice != "y" and choice != "n":
        print("ERROR: Choice must be y or n.")
        choice = input("Automatically select pay period? (y/n): ").lower().strip()

    if choice == "y":
        if pay_period := retrieve_pay_period(guide.Tables.pay_table.value.get_pay_dict()):
            pay_period = int(pay_period)
            print(f"Socks has determined the current pay period is {pay_period}, starting at {guide.Tables.pay_table.value.start_date_string(pay_period)} and ending at {guide.Tables.pay_table.value.end_date_string(pay_period)}.")
        else:
            print("Unfournately, the system time does not exist within Socks' pay periods. Please enter the pay period manually.")

    if choice == "n" or not pay_period:

        pay_period = input("\nPlease enter the pay period: ").strip()

        while not valid_period(pay_period):

            if not pay_period.isnumeric():
                print("ERROR: Pay Period must be a number. Try again.")
                pay_period = input("Please enter the pay period: ").strip()
                continue

            first_period = guide.PeriodLength.first_period.value
            last_period = guide.PeriodLength.last_period.value

            if not first_period <= int(pay_period) <= last_period:
                print(f"ERROR: Pay Period must be between {first_period} and {last_period}. Try again.")
                pay_period = input("Please enter the pay period: ").strip()
                continue

            if not guide.Tables.pay_table.value.has_pay_period(pay_period):
                print(f"ERROR: Socks currently has no pay period {pay_period}. Try again.")
                pay_period = input("Please enter the pay period: ").strip()
                continue

        pay_period = int(pay_period)

    choice = input("\nDid you miss any days this week? (y/n): ").lower().strip()

    while choice != "y" and choice != "n":
        print("ERROR: Choice must be y or n.")
        choice = input("Did you miss any days this week? (y/n): ").lower().strip()

    match choice:
        case "y":
            days = guide.Tables.pay_table.value.get_period_dates(int(pay_period))
            day_map = {guide.Tables.pay_table.value.date_str(day): day for day in days}
            day_map_keys = day_map.keys()

            print(f"\nPay Period {pay_period} Days: \n{" | ".join(day_map_keys)}\n")
            missed_days = input("Which days from this week did you miss?: ").strip().lower()
            missed_list = missed_days.split()

            while not set(missed_list) <= set(day_map_keys):
                print("ERROR: Please enter all days you missed on one line separated by spaces. Ensure all days are only from the above line.")
                missed_days = input("Which days from this week did you miss?: ").strip().lower()
                missed_list = missed_days.split()

            missed_date_times = {day_map[date_str] for date_str in missed_list}
            guide.Tables.schedule_table.value.add_missed_days(f"{first_name} {last_name}", missed_date_times)

            print("\nYour missed days have been accounted for, generating time sheet with missed days left blank...")
        case "n":
            print("\nNo missed days, generating time sheet will all days filled...")

    print("*********************************************************")

    input_path = f"{filenames.asset_folder}/{filenames.pdf_input_folder}"
    input_file_name = f"{filenames.starting_pdf}"

    sheet = sheet_writer.SheetWriter(f"{input_path}/{input_file_name}", last_name, first_name, pay_period)

    sheet.write_timesheet()

    file_name = f"{last_name.capitalize()}_Timesheet_{pay_period}.pdf"
    
    sheet.output_timesheet(file_name)

    print(f"\n{first_name.capitalize()}, your timesheet has been generated in the timesheet folder.")
    print(f"\nThank you for using (🧦) Socks (🧦)!")
    print("*********************************************************")

if __name__ == '__main__':
    main()