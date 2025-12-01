# Socks 🧦

Socks is a Python application that automatically generates Brooklyn College part-time worker timesheets. Filling out my timesheets manually was far too ardous, so I wrote this piece of software to simplify the process.  You will need to install Pypdf, pip, and python for this script to work properly. 

Usage:

```
$ python3 src/main.py

*********************************************************
(🧦) Welcome to Socks (🧦)

Please enter your first name: shawn
Please enter your last name: evans
Please enter the pay period: 21
*********************************************************
Shawn, your timesheet has been generated in the timesheet folder.

Thank you for using (🧦) Socks (🧦)!
```

The application uses an SQLite based database, socks.db, stored in the resources directory. This database can be queried easily through the execution of crud.py. 

```
$ python3 src/crud.py

******************************************************
Welcome to Socks (🧦) C.R.U.D interface! What would you like to do? 
P. Insert a new Pay Period
I. Insert an Invalid Date
C. View Pay Period Start & End Dates
H. View Invalid Dates
M. View this menu
Q. Quit Program
******************************************************
Please type your selection: c

----------------------------------------
| pay period | start date | end date   |
----------------------------------------
| 20         | 2025-11-16 | 2025-11-29 |
| 21         | 2025-11-30 | 2025-12-13 |
---------------------------------------
```

Schedules are stored in schedules.txt, with employee names being associated with a matrix that represents their start and end times.

```Shawn Evans=[['',''], ['12PM','3PM'], ['11AM','2PM'], ['',''], ['11AM','1PM'], ['',''], ['','']]```