import sqlite3
import datetime as d
import re

con = sqlite3.connect("resources/database/socks.db")
cur = con.cursor()

def menu():
    print("******************************************************")
    print("Welcome to Socks (🧦) C.R.U.D interface! What would you like to do? ")
    print("1. Insert a new Pay Period")
    print("2. Insert an Invalid Date")
    print("3. View Pay Period Start & End Dates")
    print("4. View Invalid Dates")
    print("5. View this menu")
    print("6. Delete a Pay Period")
    print("q. Quit")
    print("******************************************************")

def insert_pay_period():
    print("\n-------------------------------------")
    print("STARTING: Pay Period Insertion.")
    pay_period = input("Enter the pay period you are adding: ")

    while not pay_period.isnumeric():
        print("ERROR: Pay Periods must be numeric. Try again.")
        pay_period = input("Enter the pay period you are adding: ")

    start_str = input("When does this pay period start? MM/DD/YYYY format only: ")

    pattern = "(0?[1-9]|1[012])\\/(0?[1-9]|[12][0-9]|3[01])\\/((19|20)\\d\\d)"

    while not re.search(pattern, start_str):
        print(f"ERROR: Input String {start_str} is not in MM/DD/YYYY format.")
        start_str = input("When does this pay period start? MM/DD/YYYY format only: ")

    start_date = d.datetime.strptime(start_str, "%m/%d/%Y")
    end_date = start_date + d.timedelta(days=13)

    tuple = (pay_period, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    cur.execute("INSERT INTO payroll_schedule(pay_period,start_date,end_date) VALUES(?,?,?);", tuple)

    con.commit()

    print(f"Pay Period {pay_period} has been successfully added to the Socks database!")

    print("ENDING: Pay Period Insertion.")
    print("-------------------------------------\n")

def insert_invalid_date():
    print("\n-------------------------------------")
    print("STARTING: Invalid Date Insertion.")

    date_str = input("Enter the invalid date you are adding. MM/DD/YYY format only: ")
    pattern = "(0?[1-9]|1[012])\\/(0?[1-9]|[12][0-9]|3[01])\\/((19|20)\\d\\d)"

    while not re.search(pattern, date_str):
        print(f"ERROR: Input String {date_str} is not in MM/DD/YYYY format.")
        date_str = input("Enter the invalid date you are adding. MM/DD/YYY format only: ")

    invalid_date = d.datetime.strptime(date_str, "%m/%d/%Y")
    invalid_str = invalid_date.strftime("%Y-%m-%d")
    tuple = (invalid_str,)

    cur.execute("INSERT INTO days_off(invalid_dates) VALUES(?);", tuple)

    con.commit()

    print("ENDING: Invalid Date Insertion.")
    print("-------------------------------------\n")

def view_pay_period_start_end():
    cur.execute("SELECT * FROM payroll_schedule")

    matrix = cur.fetchall()

    print()

    print("----------------------------------------")
    print(f"| {"pay period":<8s} | {"start date"} | {"end date":<10s} |")
    print("----------------------------------------")

    for tuple in matrix:
        print(f"| {int(tuple[0]):<10d} | {tuple[1]} | {tuple[2]} |")
    print("---------------------------------------\n")

def delete_pay_period():
    print("\n-------------------------------------")
    print("STARTING: Pay Period Deletion.")

    pay_period = input("Please enter the pay period you would like to delete: ")

    con.execute("DELETE FROM payroll_schedule WHERE pay_period = ?", (pay_period,))
    con.commit()

    print(f"Pay Period {pay_period} has been successfully removed from the database.")
    print("-------------------------------------\n")

def view_invalid_dates():
    cur.execute("SELECT * FROM days_off;")

    matrix = cur.fetchall()

    print("\n-----------------")
    print("| invalid dates |")
    print("-----------------")

    for tuple in matrix:
        print(f"|  {str(tuple[0])}  |")
        
    print("-----------------\n")

def main():

    menu()
    running = True

    while running:

        choice = input("Please type your selection: ").lower()

        match choice:
            case "1":
                insert_pay_period()
            case "2":
                insert_invalid_date()
            case "3":
                view_pay_period_start_end()
            case "4":
                view_invalid_dates()
            case "5":
                menu()
            case "6":
                delete_pay_period()
            case "q":
                running = False
            case _:
                print(f"Choice {choice} is invalid, please try again.")

    print("\nThank you for using the (🧦) Socks (🧦) database!")

if __name__ == '__main__':
    main()