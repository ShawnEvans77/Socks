import datetime as d
from typing import List

class PayTable:

    days_in_period = 14

    def __init__(self):
        self.pay_dict = {}
        self.invalid_dates = []
        
        with open("resources/text input/pay_period.txt", "r") as period_file:
            for line in period_file:
                tokens = line.split(',')
                pay_period = int(tokens[0])
                self.pay_dict[pay_period] = PayTable.str_to_datetime(tokens[1])

        with open("resources/text input/invalid_dates.txt", "r") as invalid_dates_file:
            for line in invalid_dates_file:
                self.invalid_dates.append(self.str_to_datetime(line))

    @staticmethod
    def str_to_datetime(date_str: str) -> d.datetime:
        date_parts = date_str.split('/')
        return d.datetime(month=int(date_parts[0]), day=int(date_parts[1]), year=int(date_parts[2]))

    def get_period_dates(self, pay_period: int) -> List[d.datetime]:
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
    
    @staticmethod
    def date_str(date: d.datetime) -> str:
        return date.strftime("%m/%d")
    
    def start_date_string(self, pay_period: int) -> str:
        return PayTable.date_str(self.pay_dict[pay_period])
   
    def end_date_string(self, pay_period: int) -> str:
        return PayTable.date_str(self.pay_dict[pay_period] + d.timedelta(days=13))
    
    def date_offset_string(self, pay_period: int, offset: int) -> str:
        return PayTable.date_str(self.date_offset(pay_period, offset))