import sqlite3
import datetime as d

con = sqlite3.connect("resources/database/socks.db")
cur = con.cursor()

def menu():
    print("******************************************************")
    print("Welcome to Socks (🧦) C.R.U.D interface! What would you like to do? ")
    print("P. Insert a new Pay Period")
    print("I. Insert an Invalid Date")
    print("C. View Pay Period Start & End Dates")
    print("H. View Invalid Dates")
    print("M. View this menu")
    print("Q. Quit Program")
    print("******************************************************")
    
def insert_pay_period():
    print("\n-------------------------------------")
    print("STARTING: Pay Period Insertion.")
    pay_period = input("Enter the pay period you are adding: ")
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

    print("\n-------------------------------------")
    for tuple in matrix:
        print(f"{int(tuple[0]):7d} | {tuple[1]} | {tuple[2]}")
    print("-------------------------------------\n")

def view_invalid_dates():
    cur.execute("SELECT * FROM days_off;")

    matrix = cur.fetchall()

    print("\n-------------------------------------")
    for tuple in matrix:
        print(f"{str(tuple[0])}")
    print("-------------------------------------\n")

def main():

    menu()

    running = True

    while running:

        choice = input("Please type your selection: ").lower()

        match choice:
            case "p":
                insert_pay_period()
            case "i":
                insert_invalid_date()
            case "c":
                view_pay_period_start_end()
            case "h":
                view_invalid_dates()
            case "m":
                menu()
            case "q":
                running = False
            case _:
                print(f"Choice {choice} is invalid, please try again.")

    print("\nThank you for using the (🧦) Socks (🧦) database!")

if __name__ == '__main__':
    main()