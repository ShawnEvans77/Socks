from typing import List
import ast

class ScheduleTable:

    def __init__(self):
        self.schedule_dict = {}

        with open("resources/text input/schedules.txt", "r") as file:
            for line in file:
                tokens = line.split("=")
                name, schedule = str(tokens[0]), ast.literal_eval(tokens[1])
                self.schedule_dict[name] = schedule

    def get(self, name: str) -> List[List]:
        return self.schedule_dict[name]
