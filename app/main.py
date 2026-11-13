from datetime import datetime
from pathlib import Path

from src.constants import filenames, guide
from src.objects import sheet_writer
from src.utils.database import DatabaseError

from . import console
from .work_days import WorkDaysFlow


QuitApp = console.QuitApp
BackApp = console.BackApp
_prompt = console.prompt
_yn = console.yes_no
_TOTAL_STEPS = 3


def _step_employee() -> tuple[str, str, str]:
    console.section(1, _TOTAL_STEPS, "Employee")

    while True:
        first = _prompt("First name").lower()
        last = _prompt("Last name").lower()
        full_name = f"{first} {last}"
        schedule_table = guide.Tables.schedule_table.value

        if not schedule_table.has_name(full_name):
            console.error(f"No employee named {first.title()} {last.title()} found.")
            console.blank()
            continue

        display_name = console.color(
            f"{first.title()} {last.title()}", console.Color.BOLD
        )
        console.success(f"Welcome, {display_name}!")
        saved_emplid = schedule_table.get_emplid(full_name)
        if saved_emplid:
            console.info("Using the EMPLID saved for this employee.")
            return first, last, saved_emplid

        console.info("This employee needs an EMPLID saved before a timesheet can be made.")
        while True:
            emplid = _prompt("EMPLID (required)")
            if not (emplid.isascii() and emplid.isdigit()):
                console.warn("EMPLID is required and must contain digits only.")
                continue
            try:
                schedule_table.set_emplid(full_name, emplid)
            except DatabaseError as exc:
                console.warn(str(exc))
                continue
            console.success("EMPLID saved to this employee's database record.")
            return first, last, emplid


def _step_pay_period() -> int:
    console.section(2, _TOTAL_STEPS, "Pay Period")
    pay_table = guide.Tables.pay_table.value

    if _yn("Auto-detect current pay period?"):
        pay_period = _detect_pay_period()
        if pay_period is not None:
            start = pay_table.start_date_string(pay_period)
            end = pay_table.end_date_string(pay_period)
            period_label = console.color(
                pay_period, console.Color.BOLD, console.Color.CYAN
            )
            date_range = console.color(f"{start}  →  {end}", console.Color.DIM)
            console.info(f"Detected pay period {period_label}  {date_range}")
            return pay_period
        console.warn("System time falls outside all known pay periods. Switching to manual entry.")
        console.blank()

    first_period = guide.PeriodLength.first_period.value
    last_period = guide.PeriodLength.last_period.value
    while True:
        raw = _prompt("Pay period", hint=f"{first_period} – {last_period}")
        if not (raw.isascii() and raw.isdigit()):
            console.warn("Pay period must be a number.")
            continue
        if not first_period <= int(raw) <= last_period:
            console.warn(f"Pay period must be between {first_period} and {last_period}.")
            continue
        if not pay_table.has_pay_period(raw):
            console.warn(f"Pay period {raw} hasn't been set up yet.")
            continue

        pay_period = int(raw)
        console.success(f"Pay period {console.color(pay_period, console.Color.BOLD)} selected.")
        return pay_period


def _step_work_days(first: str, last: str, pay_period: int) -> None:
    flow = WorkDaysFlow(
        schedule_table=guide.Tables.schedule_table.value,
        pay_table=guide.Tables.pay_table.value,
    )
    flow.run(first, last, pay_period)


def _generate(first: str, last: str, pay_period: int, emplid: str) -> str:
    console.blank()
    console.rule("═")
    print(f"  {console.color('Generating timesheet...', console.Color.BOLD, console.Color.WHITE)}")
    console.rule("═")
    console.blank()

    input_pdf = Path(filenames.asset_folder) / filenames.pdf_input_folder / filenames.starting_pdf
    sheet = sheet_writer.SheetWriter(str(input_pdf), last, first, pay_period, emplid)
    sheet.write_timesheet()

    file_name = f"{last.capitalize()}_Timesheet_{pay_period}.pdf"
    sheet.output_timesheet(file_name)
    return file_name


def _detect_pay_period() -> int | None:
    now = datetime.now()
    for pay_period, (start, end) in guide.Tables.pay_table.value.get_pay_dict().items():
        if start <= now <= end:
            return int(pay_period)
    return None


def main() -> None:
    console.banner()
    step = 1
    first = last = None
    emplid = ""
    pay_period = None

    try:
        while True:
            try:
                if step == 1:
                    first, last, emplid = _step_employee()
                    step = 2
                elif step == 2:
                    pay_period = _step_pay_period()
                    step = 3
                else:
                    _step_work_days(first, last, pay_period)
                    file_name = _generate(first, last, pay_period, emplid)
                    saved_name = console.color(
                        file_name, console.Color.BOLD, console.Color.WHITE
                    )
                    console.success(f"Saved  →  {saved_name}")

                    pay_table = guide.Tables.pay_table.value
                    due_date = console.color(
                        pay_table.due_date_string(pay_period), console.Color.BOLD
                    )
                    pay_date = console.color(
                        pay_table.pay_date_string(pay_period), console.Color.BOLD
                    )
                    console.info(
                        f"Timesheet is due on {due_date}. You will be paid on {pay_date}."
                    )
                    console.rule()
                    thanks = console.color(
                        f"Thanks for using Socks, {first.title()}!",
                        console.Color.CYAN,
                        console.Color.BOLD,
                    )
                    print(f"  {thanks}")
                    console.rule()
                    console.blank()
                    return
            except BackApp:
                if step > 1:
                    step -= 1
                else:
                    console.info("Already at the first step.")
    except QuitApp:
        console.blank()
        console.rule()
        print(console.color("  Goodbye! 🧦", console.Color.DIM))
        console.rule()
        console.blank()
    except KeyboardInterrupt:
        console.blank()
        console.rule()
        print(console.color("  Interrupted. Goodbye! 🧦", console.Color.DIM))
        console.rule()
        console.blank()


if __name__ == "__main__":
    main()
