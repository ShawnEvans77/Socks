# Socks

A command line timesheet generator for Brooklyn College part-time workers.

## Setup
```sh
git clone https://github.com/ShawnEvans77/Socks
cd Socks
pip install -r requirements.txt
```

## Run the web app
```sh
py -m web
```
Your browser opens to http://127.0.0.1:5050/. Pick an employee, mark anything
that was different this pay period, and press **MAKE MY TIMESHEET**. The
Employees, Pay Periods, and Days Off tabs replace the CRUD menu.

- Press `Ctrl+C` in the terminal to stop it.
- `py -m web --port 5051` uses a different port; `--no-browser` skips opening the browser.
- It only listens on this computer, and uses the same database and `timesheets/` folder as the command line app.

## Run the command line app
```sh
py -m app.main
```

### Main app
```text
  ███████╗  ██████╗  ██████╗██╗  ██╗███████╗
  ██╔════╝ ██╔═══██╗██╔════╝██║ ██╔╝██╔════╝
  ███████╗ ██║   ██║██║     █████╔╝ ███████╗
  ╚════██║ ██║   ██║██║     ██╔═██╗ ╚════██║
  ███████║ ╚██████╔╝╚██████╗██║  ██╗███████║
  ╚══════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝

  ══════════════════════════════════════════════════
  [exit()] at any prompt to quit. [b] to go back
  ══════════════════════════════════════════════════

  ──────────────────────────────────────────────────
  [1/3]  Employee
  ──────────────────────────────────────────────────

  ▶ First name: shawn
  ▶ Last name: evans
  ✔  Welcome, Shawn Evans!
  ℹ  Using the EMPLID saved for this employee.

  ──────────────────────────────────────────────────
  [2/3]  Pay Period
  ──────────────────────────────────────────────────

  (y / n)
  ▶ Auto-detect current pay period?: y
  ℹ  Detected pay period 19  11/01  →  11/14

  ──────────────────────────────────────────────────
  [3/3]  Work Days
  ──────────────────────────────────────────────────

  (y / n)
  ▶ Any notable changes to account for this week?: n
  ℹ  No schedule changes. Using the saved schedule.

  ══════════════════════════════════════════════════
  Generating timesheet...
  ══════════════════════════════════════════════════

  ✔  Saved  →  Evans_Timesheet_19.pdf
  ℹ  Timesheet is due on 11/16/2026. You will be paid on 12/10/2026.
  ──────────────────────────────────────────────────
  Thanks for using Socks, Shawn!
  ──────────────────────────────────────────────────
```

## CRUD
```sh
py -m crud.crud
```

```text
╔════════════════════════════════════════════╗
  ║  SOCKS CRUD INTERFACE                      ║
  ║ [b] back  [q] quit here  [exit()] quit all ║
  ╠════════════════════════════════════════════╣
  ║   CREATE                                   ║
  ║   1  New Pay Period                        ║
  ║   2  New Invalid Date                      ║
  ║   3  New Employee                          ║
  ║   READ                                     ║
  ║   4  View Pay Period Schedule              ║
  ║   5  View Invalid Dates                    ║
  ║   6  Employee Names, EMPLIDs & Budgets     ║
  ║   7  View Employee Schedules               ║
  ║   UPDATE                                   ║
  ║   8  Update Pay Period                     ║
  ║   9  Update Invalid Date                   ║
  ║  10  Update Employee Schedule              ║
  ║  11  Update Employee Budget                ║
  ║   DELETE                                   ║
  ║  12  Delete Pay Period(s)                  ║
  ║  13  Delete Invalid Date(s)                ║
  ╠════════════════════════════════════════════╣
  ║   m  Show menu                             ║
  ╚════════════════════════════════════════════╝
```

## Notes
- Data is stored in `resources/database/socks.db`. 
- The main app asks about schedule changes once. Answering `n` uses the saved schedule without asking about missed or extra days.
- Answering `y` lets employees record missed days, missed split intervals, and extra workdays.
- CRUD can add employees with required EMPLIDs, budgets, and seven-day schedules, including split shifts. Budgets can be updated through CRUD.
- Employees can have split shifts. Generated PDFs are flattened and include the EMPLID, Prepared by name, checked CA box, and department number `885-<budget>`.
- Existing employees default to budget `54`, producing department number `885-54`.
- Timesheets are saved in `timesheets`.

## Tests
```sh
python -m unittest discover -s tests
```

## Motivation
Filling out timesheets and remembering pay period dates was tough, so I built Socks to make it easier.
