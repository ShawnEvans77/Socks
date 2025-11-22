from typing import List

class ScheduleTable:

    def __init__(self):
        self.schedule_dict = {}
        self.schedule_dict["Shawn Evans"] = [['',''], ['12PM','3PM'], ['11AM','2PM'], ['',''], ['11AM','1PM'], ['',''], ['',''], ['','']]

        # with open("resources/text input/schedules.txt", "r") as file:
        #     for line in file:
        #         tokens = line.split("-")
        #         name, schedule = tokens[0], list(tokens[1])
        #         self.schedule_dict[name] = schedule

    def get(self, name: str) -> List[List]:
        return self.schedule_dict[name]
    

x = ScheduleTable()

print(x.get('Shawn Evans'))