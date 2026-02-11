from typing import List
import json, filenames

class ScheduleTable:
    """The ScheduleTable takes schedule data from a file and converts it into an easy to use dictionary.
    This is how we get a person's schedule given their name."""

    def __init__(self):
        self.schedule_dict = {}

        with open(f"{filenames.asset_folder}/{filenames.text_folder}/schedules.json", "r") as file:
            data = json.load(file)

            employees = data['employees']

            for employee in employees:

                name = employee['name'].lower()
                portions = employee['schedule'].values()
                schedule = []

                for portion in portions:
                    start_end = [""] * 2
                    start_end[0], start_end[1] = portion[0], portion[1]

                    schedule.append(start_end)

                self.schedule_dict[name] = schedule

    def get(self, name: str) -> List[List]:
        '''Recieves a person's name as input, returns their schedule.'''
        
        return self.schedule_dict[name]
    
    def has_name(self, name: str) -> bool:
        '''Returns if this person's name exists in the schedule table.'''

        return name in self.schedule_dict.keys()