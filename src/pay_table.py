import datetime as d

class PayTable:

    def __init__(self):
        
        self.pay_dict = {}

        with open("resources/text input/pay_period.txt", "r") as file:
            for line in file:
                tokens = line.split(',')
                pay_period = int(tokens[0])
                date = tokens[1].split('/')
                self.pay_dict[pay_period] = d.datetime(month=int(date[0]), day=int(date[1]), year=int(date[2]))

    def get_period_dates(self, pay_period: int):
        pass
        # to write: feature to get a list of dates for the given pay_period, all 14 of them. 

    def get(self, pay_period: int):
        return self.pay_dict[pay_period]
    
    def month_day(self, date: d.datetime) -> str:
        return date.strftime("%m/%d")
    
    def start_date_string(self, pay_period: int) -> str:
        return self.month_day(self.pay_dict[pay_period])
   
    def end_date_string(self, pay_period: int) -> str:
        return self.month_day(self.pay_dict[pay_period] + d.timedelta(days=13))
    
    def date_offset_string(self, pay_period: int, offset: int) -> str:
        return self.month_day(self.pay_dict[pay_period] + d.timedelta(days=offset))