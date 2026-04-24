# Socks 🧦

Socks is a command line application that automatically generates Brooklyn College part-time worker timesheets.

## Installation
```
git clone https://github.com/ShawnEvans77/Socks

pip install -r requirements.txt
```

## Usage

```
$ py -m app.main


  ███████╗  ██████╗  ██████╗██╗  ██╗███████╗
  ██╔════╝ ██╔═══██╗██╔════╝██║ ██╔╝██╔════╝
  ███████╗ ██║   ██║██║     █████╔╝ ███████╗ 
  ╚════██║ ██║   ██║██║     ██╔═██╗ ╚════██║ 
  ███████║ ╚██████╔╝╚██████╗██║  ██╗███████║ 
  ╚══════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝ 

  ══════════════════════════════════════════════════
  [q] at anytime to quit. [b] to go back
  ══════════════════════════════════════════════════

  ──────────────────────────────────────────────────
  [1/3]  Employee
  ──────────────────────────────────────────────────

  ▶ First name: shawn
  ▶ Last name: evans
  ✔  Welcome, Shawn Evans!

  ──────────────────────────────────────────────────
  [2/3]  Pay Period
  ──────────────────────────────────────────────────

  (y / n)
  ▶ Auto-detect current pay period?: y
  ℹ  Detected pay period 5  04/19  →  05/02

  ──────────────────────────────────────────────────
  [3/3]  Missed Days
  ──────────────────────────────────────────────────

  (y / n)
  ▶ Did you miss any days this pay period?: n
  ℹ  No missed days — all slots will be filled.

  ══════════════════════════════════════════════════
  Generating timesheet...
  ══════════════════════════════════════════════════

  ✔  Saved  →  Evans_Timesheet_5.pdf
  ──────────────────────────────────────────────────
  Thanks for using Socks, Shawn! 🧦
  ──────────────────────────────────────────────────
```

The application uses an SQLite based database, socks.db, stored in the resources directory. This database can be queried easily through the execution of crud.py. 

```
$ py -m crud.crud
  ╔════════════════════════════════════════════╗
  ║ 🧦  SOCKS CRUD INTERFACE                   ║
  ║ [b] back inside any operation  [q] quit    ║
  ╠════════════════════════════════════════════╣
  ║   CREATE                                   ║
  ║   1  New Pay Period                        ║
  ║   2  New Invalid Date                      ║
  ║   READ                                     ║
  ║   3  View Pay Period Schedule              ║
  ║   4  View Invalid Dates                    ║
  ║   UPDATE                                   ║
  ║   5  Update Pay Period                     ║
  ║   6  Update Invalid Date                   ║
  ║   DELETE                                   ║
  ║   7  Delete Pay Period(s)                  ║
  ║   8  Delete Invalid Date(s)                ║
  ╠════════════════════════════════════════════╣
  ║   m  Show menu                             ║
  ╚════════════════════════════════════════════╝
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

# Tests
To test the application, type:

```
python -m unittest discover -s tests
```

## Motivation
Filling out my timesheets manually and remembering pay period dates was tough, so I built this application to simplify the process.