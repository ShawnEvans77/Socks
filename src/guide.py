import pay_table as pt, schedule_table as st
from enum import Enum

class Indices(Enum):
    last_name_index, first_name_index = 6, 7 # SIX SEVEN!!! :3
    pay_period_index = 5

    dept_num_index = 1
    dept_index = 9
    rate_index = 2
    dept_ext_index = 151

    sub_totals_indices = ((74, 73), (132,137))
    total_hours_index = (138, 141)

    week_one_date_indices = (10, 14, 18, 22, 26, 30, 34)
    week_two_date_indices = (75, 84, 85, 86, 87, 88, 89)
    date_indices = week_one_date_indices + week_two_date_indices

    week_one_time_in_out_indices = ((11, 13), (15,  17), (19,21),   (23, 25),  (27, 29),  (31, 33), (35, 37))
    week_two_time_in_out_indices = ((76, 78), (90, 102), (91, 103), (92, 104), (93, 105), (94, 106),  (95, 107))
    time_in_out_indices = week_one_time_in_out_indices + week_two_time_in_out_indices

    week_one_total_indices = (59, 60, 61, 62, 63, 64, 65)
    week_two_total_indices = (82, 126, 127, 128, 129, 130, 131)
    total_indices = week_one_total_indices + week_two_total_indices

    week_one_hours_worked = (45, 46, 47, 48, 49, 50, 51)
    week_two_hours_worked = (79, 108, 109, 110, 111, 112, 113)
    hours_worked_indices = week_one_hours_worked + week_two_hours_worked

class LearningCenter(Enum):
    lc_dept_name = 'Learning Center'
    lc_dept_num = '885-01'
    lc_ca_rate = '$19.12'
    lc_dept_ext = '5821'

class WeekLength(Enum):
    days_in_period = 14

class PeriodLength(Enum):
    first_period = 1
    last_period = 26

class Tables(Enum):
    pay_table = pt.PayTable()
    schedule_table = st.ScheduleTable()