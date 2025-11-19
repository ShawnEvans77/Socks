import datetime as d

class PayTable:

    pay_dict = {}

    def __init__(self):
        with open("resources/pay_period.txt", "r") as file:
            for line in file:
                tokens = line.split(',')
                pay_period = tokens[0]
                date = tokens[1].split('/')
                self.pay_dict[pay_period] = d.datetime(month=int(date[0]), day=int(date[1]), year=int(date[2]))

    def get(self, pay_period):
        return self.pay_dict[pay_period]
    
    def month_day(self, date):
        return f"{date.month}/{date.day}"
    
    def start_string(self, pay_period) -> str:
        return self.month_day(self.pay_dict[pay_period])
   
    def end_string(self, pay_period) -> str:
        return self.month_day(self.pay_dict[pay_period] + d.timedelta(days=13))
    
    def offset_string(self, pay_period, offset):
        return self.month_day(self.pay_dict[pay_period] + d.timedelta(days=offset))


    
