from ..objects import pay_table as pt, schedule_table as st
from enum import Enum
from .payroll import DEFAULT_BUDGET, FIRST_PAY_PERIOD, LAST_PAY_PERIOD

class Indices(Enum):
    last_name_index, first_name_index = 6, 7
    pay_period_index = 5

    dept_num_index = 1
    dept_index = 9
    rate_index = 2
    dept_ext_index = 151
    ca_checkbox_name = "topmostSubform[0].Page1[0].CheckBox1[0]"

    sub_totals_indices = ((74, 73), (132,137))
    total_hours_index = (138, 141)

    week_one_date_indices = (10, 14, 18, 22, 26, 30, 34)
    week_two_date_indices = (75, 84, 85, 86, 87, 88, 89)
    date_indices = week_one_date_indices + week_two_date_indices

    week_one_time_in_out_indices = ((11, 13), (15,  17), (19,21),   (23, 25),  (27, 29),  (31, 33), (35, 37))
    week_two_time_in_out_indices = ((76, 78), (90, 102), (91, 103), (92, 104), (93, 105), (94, 106),  (95, 107))
    time_in_out_indices = week_one_time_in_out_indices + week_two_time_in_out_indices
    meal_period_indices = (12, 16, 20, 24, 28, 32, 36, 77, 96, 97, 98, 99, 100, 101)

    week_one_total_indices = (59, 60, 61, 62, 63, 64, 65)
    week_two_total_indices = (82, 126, 127, 128, 129, 130, 131)
    total_indices = week_one_total_indices + week_two_total_indices

    week_one_hours_worked = (45, 46, 47, 48, 49, 50, 51)
    week_two_hours_worked = (79, 108, 109, 110, 111, 112, 113)
    hours_worked_indices = week_one_hours_worked + week_two_hours_worked

class LearningCenter(Enum):
    lc_dept_name = 'Learning Center'
    lc_dept_prefix = '885'
    default_budget = DEFAULT_BUDGET
    lc_ca_rate = '$19.12'
    lc_dept_ext = '5821'

class PeriodLength(Enum):
    first_period = FIRST_PAY_PERIOD
    last_period = LAST_PAY_PERIOD

class Tables(Enum):
    pay_table = pt.PayTable()
    schedule_table = st.ScheduleTable()
