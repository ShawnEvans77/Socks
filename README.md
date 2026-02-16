# Socks 🧦

Socks is a command line application that automatically generates Brooklyn College part-time worker timesheets.

## Installation
```
git clone https://github.com/ShawnEvans77/Socks

pip install -r requirements.txt
```

## Usage

```
$ py src/main.py

*********************************************************
(🧦) Welcome to Socks (🧦)

Please enter your first name: shawn
Please enter your last name: evans

Automatically select pay period? (y/n): y
Socks has determined the current pay period is 26, starting at 02/08 and ending at 02/21.

Did you miss any days this week? (y/n): y

Pay Period 26 Days: 
02/08 | 02/09 | 02/10 | 02/11 | 02/12 | 02/13 | 02/14 | 02/15 | 02/16 | 02/17 | 02/18 | 02/19 | 02/20 | 02/21

Which days from this week did you miss?: 02/12 02/15

Your missed days have been accounted for, generating time sheet with missed days left blank...
*********************************************************

Shawn, your timesheet has been generated in the timesheet folder.

Thank you for using (🧦) Socks (🧦)!
*********************************************************
```

The application uses an SQLite based database, socks.db, stored in the resources directory. This database can be queried easily through the execution of crud.py. 

```
$ py src/crud.py

******************************************************
Welcome to Socks (🧦) C.R.U.D interface! What would you like to do? 
1. Create a new Pay Period
2. Create an Invalid Date
3. Read Pay Period Start & End Dates
4. Read Invalid Dates
5. Update a Pay Period
6. Update an Invalid Date
7. Delete a Pay Period
8. Delete Invalid Date
m. View Menu
q. Quit
******************************************************
Please type your selection: 3

----------------------------------------
| pay period | start date | end date   |
----------------------------------------
| 20         | 2025-11-16 | 2025-11-29 |
| 21         | 2025-11-30 | 2025-12-13 |
---------------------------------------
```

Schedules are stored in schedules.json.

```
{
    "employees": [
        {  
            "name": "Shawn Evans",
            "schedule": {
                "sunday": ["", ""],
                "monday": ["1PM", "4PM"],
                "tuesday": ["", ""],
                "wednesday": ["12PM", "2PM"],
                "thursday": ["3PM", "6PM"],
                "friday": ["",""],
                "saturday": ["",""]
            }  
        }
    ]
}
```

## Motivation
Filling out my timesheets manually and remembering pay period dates was tough, so I built this application to simplify the process.