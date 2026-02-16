import sqlite3, re, filenames, datetime as d, guide

class Database:
    '''The Database Class is a wrapper for an Sqlite3 database. This class supports CRUD operations.'''

    def __init__(self):
        self.con = sqlite3.connect(f"{filenames.asset_folder}/{filenames.database_folder}/{filenames.database_name}")
        self.cur = self.con.cursor()

    def create_pay_period(self):
        '''Inserts a Pay Period into the database, doing error checking for the pay period & start date.'''

        print("\n-------------------------------------")
        print("STARTING: Pay Period Creation.")

        pay_period = Database.fetch_period("Enter the pay period you are adding: ")
        self.cur.execute("SELECT pay_period FROM payroll_schedule WHERE pay_period=?",(pay_period,))

        if len(self.cur.fetchall()) != 0:
            print(f"ERROR: {pay_period} is already inside the database.")
        else:
            start_str = Database.fetch_date("When does this pay period start: ")
            start_date = d.datetime.strptime(start_str, "%m/%d/%Y")

            self.cur.execute("SELECT pay_period, start_date FROM payroll_schedule WHERE start_date=?", (start_date.strftime("%Y-%m-%d"),))
            matrix = self.cur.fetchall()

            if len(matrix) != 0:
                print(f"ERROR: Start date {start_str} already belongs to pay period {matrix[0][0]}.")
            else:
                end_date = start_date + d.timedelta(days=13)
                tuple = (pay_period, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                self.cur.execute("INSERT INTO payroll_schedule(pay_period,start_date,end_date) VALUES(?,?,?);", tuple)
                self.con.commit()
                print(f"Pay Period {pay_period} has been successfully added to the database!")

        print("ENDING: Pay Period Creation.")
        print("-------------------------------------\n")

    def create_invalid_date(self):
        '''Inserts an invalid date, doing error checking for the invalid date.'''
        
        print("\n-------------------------------------")
        print("STARTING: Invalid Date Creation.")

        date_str = Database.fetch_date("Enter the invalid date you are adding: ")
        invalid_date = d.datetime.strptime(date_str, "%m/%d/%Y")
        tuple = (invalid_date.strftime("%Y-%m-%d"),)

        self.cur.execute("SELECT invalid_dates FROM days_off WHERE invalid_dates=?",tuple)

        if len(self.cur.fetchall()) != 0:
            print(f"ERROR: Invalid Date {date_str} is already in the database.")
        else:
            self.cur.execute("INSERT INTO days_off(invalid_dates) VALUES(?);", tuple)
            self.con.commit()
            print(f"Invalid Date {date_str} has been successfully added to the database!")

        print("ENDING: Invalid Date Creation.")
        print("-------------------------------------\n")

    def read_pay_period_start_end(self):
        '''Read pay periods & their associated start and end dates.'''

        self.cur.execute("SELECT * FROM payroll_schedule")
        matrix = self.cur.fetchall()

        print()
        print("----------------------------------------")
        print(f"| {"pay period":<8s} | {"start date"} | {"end date":<10s} |")
        print("----------------------------------------")

        for tuple in matrix:
            print(f"| {int(tuple[0]):<10d} | {tuple[1]} | {tuple[2]} |")

        print("---------------------------------------\n")

    def read_invalid_dates(self):
        '''View all invalid dates in the databae.'''

        self.cur.execute("SELECT * FROM days_off;")
        matrix = self.cur.fetchall()

        print("\n-----------------")
        print("| invalid dates |")
        print("-----------------")

        for tuple in matrix:
            print(f"|  {str(tuple[0])}  |")
            
        print("-----------------\n")

    def update_pay_period(self):
        '''Updates the start date of a given pay period, doing error checking for the pay period & start date.'''

        print("\n-------------------------------------")
        print("STARTING: Pay Period Update.")

        pay_period = Database.fetch_period("Please enter the pay period you would like to update: ")
        self.cur.execute("SELECT pay_period, start_date FROM payroll_schedule WHERE pay_period=?", (pay_period,))
        matrix = self.cur.fetchall()

        if len(matrix) == 0:
            print(f"ERROR: Pay Period {pay_period} does not exist in the Database.")
        else:
            old = d.datetime.strptime(matrix[0][1], "%Y-%m-%d").strftime("%m/%d/%Y")
            print(f"Pay Period {pay_period} old date: {old}")

            start_str = Database.fetch_date(f"Please enter the new start date for pay period {pay_period}: ")
            start_date = d.datetime.strptime(start_str, "%m/%d/%Y")

            self.cur.execute("SELECT pay_period FROM payroll_schedule WHERE start_date=?", (start_date.strftime("%Y-%m-%d"),))
            matrix = self.cur.fetchall()

            if len(matrix) != 0:
                print(f"ERROR: Start date {start_str} already belongs to pay period {matrix[0][0]}.")
            else:
                end_date = start_date + d.timedelta(days=13)
                tuple = (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), pay_period)
                self.cur.execute("UPDATE payroll_schedule SET start_date=?, end_date=? WHERE pay_period=?", tuple)
                self.con.commit()
                print(f"Successfully replaced pay period {pay_period}'s start date from {old} to {start_str}!")

        print("ENDING: Pay Period Update.")
        print("-------------------------------------\n")

    def update_invalid_date(self):
        '''Updates the given invalid date, doing error checking for the invalid date.'''

        print("\n-------------------------------------")
        print("STARTING: Invalid Date Update")

        date_str = Database.fetch_date("Please enter the date you want to change: " )
        invalid_date = d.datetime.strptime(date_str, "%m/%d/%Y")
        invalid_str = invalid_date.strftime("%Y-%m-%d")
        self.cur.execute("SELECT invalid_dates FROM days_off WHERE invalid_dates=?",(invalid_str,))

        if len(self.cur.fetchall()) == 0:
            print(f"ERROR: Invalid Date {date_str} does not exist in the Database.")
        else:
            to_add_date = Database.fetch_date(f"Please enter the new date that will replace {date_str}: ")
            new_date = d.datetime.strptime(to_add_date, "%m/%d/%Y")
            new_str = new_date.strftime("%Y-%m-%d")

            self.cur.execute("SELECT invalid_dates FROM days_off WHERE invalid_dates=?",(new_str,))

            if len(self.cur.fetchall()) != 0:
                print(f"ERROR: Invalid Date {to_add_date} already exists inside of the database.")
            else:
                tuple = (new_str, invalid_str)
                self.cur.execute("UPDATE days_off SET invalid_dates=? WHERE invalid_dates=?", (tuple))
                self.con.commit()
                print(f"Successfully replaced invalid date {date_str} to {to_add_date}!")

        print("ENDING: Invalid Date Update.")
        print("-------------------------------------\n")

    def delete_pay_period(self):
        '''Delete a pay period from the databse, doing error checking for the pay period.'''

        print("\n-------------------------------------")
        print("STARTING: Pay Period Deletion.")

        pay_period = Database.fetch_period("Please enter the pay period you would like to delete: ")
        self.cur.execute("SELECT pay_period FROM payroll_schedule WHERE pay_period=?",(pay_period,))

        if len(self.cur.fetchall()) == 0:
            print(f"ERROR: Pay Period {pay_period} does not exist in the Database.")
        else:
            self.con.execute("DELETE FROM payroll_schedule WHERE pay_period = ?", (pay_period,))
            self.con.commit()
            print(f"Pay Period {pay_period} has been successfully removed from the database.")

        print("ENDING: Pay Period Deletion.")
        print("-------------------------------------\n")

    def delete_invalid_date(self):
        '''Deletes an invalid date from the database, doing error checking for the invalid date.'''

        print("\n-------------------------------------")
        print("STARTING: Invalid Date Deletion.")

        date_str = Database.fetch_date("Please enter the invalid date you want to delete: ")
        invalid_date = d.datetime.strptime(date_str, "%m/%d/%Y")
        tuple = (invalid_date.strftime("%Y-%m-%d"),)

        self.cur.execute("SELECT invalid_dates FROM days_off WHERE invalid_dates=?",tuple)

        if len(self.cur.fetchall()) == 0:
            print(f"ERROR: Invalid Date {date_str} does not exist in the Database.")
        else:
            self.con.execute("DELETE FROM days_off WHERE invalid_dates=?",tuple)
            self.con.commit()
            print(f"Invalid Date {date_str} has been successfully removed from the database.")

        print("ENDING: Invalid Date Deletion.")
        print("-------------------------------------\n")

    @staticmethod
    def fetch_period(prompt: str) -> str:
        '''Fetches a pay period from user input, doing input validation as well.'''

        pay_period = input(prompt).strip()

        while not Database.insertable_period(pay_period):

            if not pay_period.isnumeric():
                print("ERROR: Pay Period must be a number. Try again.")
                pay_period = input(prompt).strip()
                continue

            first_period = guide.PeriodLength.first_period.value
            last_period = guide.PeriodLength.last_period.value

            if not first_period <= int(pay_period) <= last_period:
                print(f"ERROR: Pay Period must be between {first_period} and {last_period}. Try again.")
                pay_period = input(prompt).strip()
                continue

        return pay_period

    @staticmethod
    def insertable_period(pay_period: str) -> bool:
        '''Determines if a pay period can be inserted into the databse.'''

        return pay_period.isnumeric() and 1 <= int(pay_period) <= 26
    
    @staticmethod
    def fetch_date(prompt: str) -> str:
        '''Fetches a date, doing error checking for if the date is in MM/DD/YYYY.'''

        date_str = input(prompt)
        pattern = "(0?[1-9]|1[012])\\/(0?[1-9]|[12][0-9]|3[01])\\/((19|20)\\d\\d)"

        while not re.search(pattern, date_str):
            print(f"ERROR: Input String {date_str} is not in MM/DD/YYYY format.")
            date_str = input(prompt)

        return date_str