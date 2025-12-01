import sqlite3
import datetime as d

con = sqlite3.connect("resources/database/socks.db")
cur = con.cursor()

print("******************************************************")
print("Welcome to Socks (🧦) C.R.U.D interface! What would you like to do? ")
print("P. Insert a new Pay Period")
print("I. Insert an Invalid Date")
print("V. View Database Contents")
print("Q. Quit Program")
print("******************************************************")

choice = input("Please type your selection: ").lower()

while choice != "q":

    match choice:
        case "p":
            print("STARTING: Pay Period Insertion.")
            pay_period = input("Please enter the pay period you are adding to the database: ")
            start_str = input("When does this pay period start? MM/DD/YYYY format only: ")

            start_date = d.datetime.strptime(start_str, "%m/%d/%Y")
            end_date = start_date + d.timedelta(days=13)

            tuple = (pay_period, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

            cur.execute("INSERT INTO payroll_schedule(pay_period,start_date,end_date) VALUES(?,?,?);", tuple)

            con.commit()

            print(f"Pay Period {pay_period} has been successfully added to the Socks database!")

            print("ENDING: Pay Period Insertion.")
            print("-------------------------------------")

    choice = input("Please type your selection: ").lower()

    



    


