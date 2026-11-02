# Socks

A command line timesheet generator for Brooklyn College part-time workers.

## Setup
```sh
git clone https://github.com/ShawnEvans77/Socks
cd Socks
pip install -r requirements.txt
```

## Run
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
  ▶ Did you miss any days this pay period?: n
  ℹ  No missed days — all slots will be filled.
  (y / n)
  ▶ Did you work an extra day or days this pay period?: n
  ℹ  No extra days recorded.

  ══════════════════════════════════════════════════
  Generating timesheet...
  ══════════════════════════════════════════════════

  ✔  Saved  →  Evans_Timesheet_19.pdf
  ℹ  Timesheet is due on 11/16/2026. You will be paid on 12/10/2026.
  ──────────────────────────────────────────────────
  Thanks for using Socks, Shawn! 🧦
  ──────────────────────────────────────────────────
```

## CRUD
```sh
py -m crud.crud
```

```text
╔════════════════════════════════════════════╗
  ║ 🧦  SOCKS CRUD INTERFACE                   ║
  ║ [b] back  [q] quit here  [exit()] quit all ║
  ╠════════════════════════════════════════════╣
  ║   CREATE                                   ║
  ║   1  New Pay Period                        ║
  ║   2  New Invalid Date                      ║
  ║   3  New Employee                          ║
  ║   READ                                     ║
  ║   4  View Pay Period Schedule              ║
  ║   5  View Invalid Dates                    ║
  ║   6  View Employee Names & EMPLIDs         ║
  ║   7  View Employee Schedules               ║
  ║   UPDATE                                   ║
  ║   8  Update Pay Period                     ║
  ║   9  Update Invalid Date                   ║
  ║  10  Update Employee Schedule              ║
  ║   DELETE                                   ║
  ║  11  Delete Pay Period(s)                  ║
  ║  12  Delete Invalid Date(s)                ║
  ╠════════════════════════════════════════════╣
  ║   m  Show menu                             ║
  ╚════════════════════════════════════════════╝
```

## Notes
- Data is stored in `resources/database/socks.db`. 
- CRUD can add employees with required EMPLIDs and seven-day schedules, including split shifts.
- Employees can have split shifts. Generated PDFs are flattened and include the EMPLID, Prepared by name, checked CA box, and department `885-54`.
- Timesheets are saved in `timesheets`.

## Tests
```sh
python -m unittest discover -s tests
```

## Motivation
Filling out timesheets and remembering pay period dates was tough, so I built Socks to make it easier.
