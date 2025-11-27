from typing import List
import ast

class ScheduleTable:
    """The ScheduleTable takes schedule data from a file and converts it into an easy to use dictionary.
    This is how we get a person's schedule given their name."""

    def __init__(self):
        self.schedule_dict = {}

        with open("resources/text input/schedules.txt", "r") as file:
            for line in file:
                tokens = line.split("=")
                name, schedule = str(tokens[0]).lower(), ast.literal_eval(tokens[1])
                self.schedule_dict[name] = schedule

    def get(self, name: str) -> List[List]:
        return self.schedule_dict[name]
