# Socks

Socks is a command line application that generates Brooklyn College part-time worker timesheets.

## Installation
```
git clone https://github.com/ShawnEvans77/Socks
cd Socks
pip install -r requirements.txt
```

## Usage
```
py -m app.main
```

Enter an employee's name and required EMPLID, then choose a pay period. The program uses the employee's saved weekly schedule and asks about missed days and extra work. Extra work times accept 12-hour input, including minutes, such as `2:15PM`. The program checks that start and end times make sense and reports the timesheet due date and pay date when finished.

An employee can have up to two work intervals per weekday. Split intervals are shown in the Time In and Time Out fields, with Meal Period left blank. Both intervals count toward the day's total hours.

Generated timesheets are saved in `timesheets`. PDFs are flattened and are not editable. Each sheet includes the employee's EMPLID, the employee's name in Prepared by, a checked CA box, and department number `885-54`.

## Database and CRUD
The application uses `resources/database/socks.db` for pay periods, timesheet due dates and pay dates, invalid dates, employee names, EMPLIDs, and weekly work intervals. The former `schedules.json` file is no longer used.

Run the CRUD interface with:
```
py -m crud.crud
```

CRUD can create, view, update, and delete pay periods and invalid dates. It can also display employee names, EMPLIDs, and weekly schedules, and update an employee's recurring weekday schedule by name or 3-letter abbreviation with one or two work intervals.

## Tests
Run the test suite with:
```
python -m unittest discover -s tests
```

## Motivation
Filling out my timesheets manually and remembering pay period dates was tough, so I built this application to simplify the process.
