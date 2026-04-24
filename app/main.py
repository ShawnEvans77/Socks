from src.objects import sheet_writer
from src.constants import guide, filenames
import datetime, re


# ─── ANSI Colors ──────────────────────────────────────────────────────────────

class Color:
    RESET  = "\033[0m";  BOLD   = "\033[1m";  DIM    = "\033[2m"
    RED    = "\033[91m"; GREEN  = "\033[92m"; YELLOW = "\033[93m"
    BLUE   = "\033[94m"; CYAN   = "\033[96m"; WHITE  = "\033[97m"

def c(text: str, *codes: str) -> str:
    return "".join(codes) + str(text) + Color.RESET


# ─── Control Flow ─────────────────────────────────────────────────────────────

class QuitApp(Exception):
    pass

class BackApp(Exception):
    pass


# ─── UI Primitives ────────────────────────────────────────────────────────────

def _rule(ch: str = "─", n: int = 50) -> None:
    print(c("  " + ch * n, Color.DIM))

def _blank() -> None:
    print()

def _success(msg: str) -> None: print(f"  {c('✔  ' + msg, Color.GREEN)}")
def _error(msg: str)   -> None: print(f"  {c('✘  ' + msg, Color.RED)}")
def _warn(msg: str)    -> None: print(f"  {c('⚠  ' + msg, Color.YELLOW)}\n")
def _info(msg: str)    -> None: print(f"  {c('ℹ  ' + msg, Color.CYAN)}")

def _section(step: int, total: int, title: str) -> None:
    _blank()
    _rule()
    step_tag = c(f"  [{step}/{total}]", Color.DIM)
    print(f"{step_tag}  {c(title, Color.BOLD + Color.CYAN)}")
    _rule()
    _blank()

def _prompt(label: str, hint: str = "") -> str:
    """Styled input. Raises control-flow exceptions for q/back commands."""
    if hint:
        print(c(f"  ({hint})", Color.DIM))
    raw = input(c(f"  ▶ {label}: ", Color.CYAN)).strip()
    command = raw.lower()
    if command == "q":
        raise QuitApp
    if command == "b":
        raise BackApp
    return raw

def _yn(label: str) -> bool:
    """Binary yes/no prompt. Raises QuitApp on 'q'."""
    while True:
        raw = _prompt(label, hint="y / n").lower()
        if raw == "y": return True
        if raw == "n": return False
        _warn("Please enter y or n.")


# ─── Banner ───────────────────────────────────────────────────────────────────

_LOGO = [
    "  ███████╗  ██████╗  ██████╗██╗  ██╗███████╗",
    "  ██╔════╝ ██╔═══██╗██╔════╝██║ ██╔╝██╔════╝",
    "  ███████╗ ██║   ██║██║     █████╔╝ ███████╗ ",
    "  ╚════██║ ██║   ██║██║     ██╔═██╗ ╚════██║ ",
    "  ███████║ ╚██████╔╝╚██████╗██║  ██╗███████║ ",
    "  ╚══════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝ ",
]

def _banner() -> None:
    _blank()
    for line in _LOGO:
        print(c(line, Color.CYAN + Color.BOLD))
    _blank()
    _rule("═")
    print(c("  [q] at anytime to quit. [b] to go back", Color.DIM))
    _rule("═")


# ─── Step 1: Employee ─────────────────────────────────────────────────────────

def _step_employee() -> tuple[str, str]:
    _section(1, 3, "Employee")

    while True:
        first = _prompt("First name").lower()
        last  = _prompt("Last name").lower()
        full  = f"{first} {last}"

        if guide.Tables.schedule_table.value.has_name(full):
            _success(f"Welcome, {c(first.title() + ' ' + last.title(), Color.BOLD)}!")
            return first, last

        _error(f"No employee named {first.title()} {last.title()} found.")
        _blank()


# ─── Step 2: Pay Period ───────────────────────────────────────────────────────

def _step_pay_period() -> int:
    _section(2, 3, "Pay Period")

    if _yn("Auto-detect current pay period?"):
        pp = _detect_pay_period()
        if pp is not None:
            start = guide.Tables.pay_table.value.start_date_string(pp)
            end   = guide.Tables.pay_table.value.end_date_string(pp)
            _info(
                f"Detected pay period {c(str(pp), Color.BOLD + Color.CYAN)}"
                f"  {c(f'{start}  →  {end}', Color.DIM)}"
            )
            return pp
        _warn("System time falls outside all known pay periods — switching to manual entry.")
        _blank()

    first_p = guide.PeriodLength.first_period.value
    last_p  = guide.PeriodLength.last_period.value

    while True:
        raw = _prompt("Pay period", hint=f"{first_p} – {last_p}")

        if not raw.isnumeric():
            _warn("Pay period must be a number.")
            continue
        if not first_p <= int(raw) <= last_p:
            _warn(f"Pay period must be between {first_p} and {last_p}.")
            continue
        if not guide.Tables.pay_table.value.has_pay_period(raw):
            _warn(f"Pay period {raw} hasn't been set up yet.")
            continue

        pp = int(raw)
        _success(f"Pay period {c(str(pp), Color.BOLD)} selected.")
        return pp


# ─── Step 3: Missed Days ──────────────────────────────────────────────────────

def _step_missed_days(first: str, last: str, pay_period: int) -> None:
    _section(3, 3, "Missed Days")

    if not _yn("Did you miss any days this pay period?"):
        _info("No missed days — all slots will be filled.")
        return

    _blank()

    days    = guide.Tables.pay_table.value.get_period_dates(pay_period)
    day_map = {guide.Tables.pay_table.value.date_str(day): day for day in days}
    keys    = list(day_map)

    print(c("  Available days:", Color.DIM))
    print("  " + c(" | ", Color.DIM).join(c(k, Color.YELLOW + Color.BOLD) for k in keys))
    _blank()

    while True:
        raw    = _prompt("Missed days (space-separated)").lower()
        missed = raw.split()

        if not missed:
            _warn("Enter at least one day, or answer n above to skip.")
            continue

        invalid = set(missed) - set(keys)
        if invalid:
            _warn(f"Unrecognized: {c(', '.join(sorted(invalid)), Color.YELLOW)}. Use only the dates listed above.")
            continue

        guide.Tables.schedule_table.value.add_missed_days(f"{first} {last}", {day_map[s] for s in missed})
        _success(f"{len(missed)} missed day(s) recorded: {', '.join(c(d, Color.YELLOW) for d in sorted(missed))}")
        return


# ─── Generate ─────────────────────────────────────────────────────────────────

def _generate(first: str, last: str, pay_period: int) -> str:
    _blank()
    _rule("═")
    print(f"  {c('Generating timesheet...', Color.BOLD + Color.WHITE)}")
    _rule("═")
    _blank()

    input_path = f"{filenames.asset_folder}/{filenames.pdf_input_folder}"
    sheet = sheet_writer.SheetWriter(
        f"{input_path}/{filenames.starting_pdf}", last, first, pay_period
    )
    sheet.write_timesheet()

    file_name = f"{last.capitalize()}_Timesheet_{pay_period}.pdf"
    sheet.output_timesheet(file_name)

    return file_name


# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _detect_pay_period() -> int | None:
    now = datetime.datetime.now()
    for pay_period, dates in guide.Tables.pay_table.value.get_pay_dict().items():
        if dates[0] <= now <= dates[1]:
            return int(pay_period)
    return None


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    _banner()
    step = 1
    first = None
    last = None
    pay_period = None

    try:
        while True:
            try:
                if step == 1:
                    first, last = _step_employee()
                    step = 2
                elif step == 2:
                    pay_period = _step_pay_period()
                    step = 3
                elif step == 3:
                    _step_missed_days(first, last, pay_period)
                    file_name = _generate(first, last, pay_period)

                    _success(f"Saved  →  {c(file_name, Color.BOLD + Color.WHITE)}")
                    _rule()
                    print(f"  {c(f'Thanks for using Socks, {first.title()}! 🧦', Color.CYAN + Color.BOLD)}")
                    _rule()
                    _blank()
                    return
            except BackApp:
                if step > 1:
                    step -= 1
                else:
                    _info("Already at the first step.")

    except QuitApp:
        _blank()
        _rule()
        print(c("  Goodbye! 🧦", Color.DIM))
        _rule()
        _blank()

    except KeyboardInterrupt:
        _blank()
        _rule()
        print(c("  Interrupted. Goodbye! 🧦", Color.DIM))
        _rule()
        _blank()


if __name__ == "__main__":
    main()
