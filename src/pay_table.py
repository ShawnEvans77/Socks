import datetime as d
from typing import List
import sqlite3

class PayTable:
    """The PayTable class is how we access pay period dates from an integer representing the pay period. 

    Attributes
        pay_dict - A dictionary that relates pay periods to their proper start date. 
        invalid_dates - A list representing all dates where college assistants do not work.
    """

    days_in_period = 14

    con = sqlite3.connect("resources/database/socks.db")
    cur = con.cursor()

    def __init__(self):

        self.pay_dict = {}
        self.invalid_dates = []

        # create pay-table using databases
        res = PayTable.cur.execute("SELECT pay_period, start_date FROM payroll_schedule;")
        matrix = res.fetchall()

        for tuple in matrix:
            pay_period = int(tuple[0])
            date = d.datetime.strptime(str(tuple[1]), "%Y-%m-%d")
            self.pay_dict[pay_period] = date

        res = PayTable.cur.execute("SELECT * FROM days_off;")
        matrix = res.fetchall()

        for tuple in matrix:
            self.invalid_dates.append(d.datetime.strptime(str(tuple[0]), "%Y-%m-%d"))

        # # create pay-table using a .txt file

        # with open("resources/text input/pay_period.txt", "r") as period_file:
        #     for line in period_file:
        #         tokens = line.split(',')
        #         pay_period = int(tokens[0])
        #         self.pay_dict[pay_period] = PayTable.str_to_datetime(tokens[1])

        # with open("resources/text input/invalid_dates.txt", "r") as invalid_dates_file:
        #     for line in invalid_dates_file:
        #         self.invalid_dates.append(self.str_to_datetime(line))

    @staticmethod
    def str_to_datetime(date_str: str) -> d.datetime:
        """Takes a string in the form MM/DD/YYYY and converts it into a datetime object."""

        date_parts = date_str.split('/')
        return d.datetime(month=int(date_parts[0]), day=int(date_parts[1]), year=int(date_parts[2]))
    
    @staticmethod
    def date_str(date: d.datetime) -> str:
        """Given a datetime object, return a string in the form DD/YY. Needed when filling out the 14 date fields
        of the timesheet."""

        return date.strftime("%m/%d")

    def get_period_dates(self, pay_period: int) -> List[d.datetime]:
        """Returns a list of datetime objects representing the days in a given pay period."""

        list = []

        for i in range(PayTable.days_in_period):
            list.append(self.date_offset(pay_period, i))

        return list
    
    def get_invalid_dates(self) -> List[d.datetime]:
        return self.invalid_dates

    def get(self, pay_period: int):
        return self.pay_dict[pay_period]
    
    def date_offset(self, pay_period: int, offset: int) -> d.datetime:
        return self.pay_dict[pay_period] + d.timedelta(days=offset)
    
    def start_date_string(self, pay_period: int) -> str:
        return PayTable.date_str(self.pay_dict[pay_period])
   
    def end_date_string(self, pay_period: int) -> str:
        return PayTable.date_str(self.pay_dict[pay_period] + d.timedelta(days=13))
    
    def date_offset_string(self, pay_period: int, offset: int) -> str:
        return PayTable.date_str(self.date_offset(pay_period, offset))