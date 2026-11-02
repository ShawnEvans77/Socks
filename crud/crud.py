from src.utils import wrapper
from src.utils.terminal import Color, color as c, pad
from src.utils.wrapper import QuitApp


_WIDTH = 44
_MENU_GROUPS = (
    ("CREATE", Color.GREEN, (
        ("1", "New Pay Period", "create_pay_period"),
        ("2", "New Invalid Date", "create_invalid_date"),
        ("3", "New Employee", "create_employee"),
    )),
    ("READ", Color.BLUE, (
        ("4", "View Pay Period Schedule", "read_pay_period_start_end"),
        ("5", "View Invalid Dates", "read_invalid_dates"),
        ("6", "Employee Names, EMPLIDs & Budgets", "read_employee_names_and_emplids"),
        ("7", "View Employee Schedules", "read_employee_schedules"),
    )),
    ("UPDATE", Color.YELLOW, (
        ("8", "Update Pay Period", "update_pay_period"),
        ("9", "Update Invalid Date", "update_invalid_date"),
        ("10", "Update Employee Schedule", "update_employee_schedule"),
        ("11", "Update Employee Budget", "update_employee_budget"),
    )),
    ("DELETE", Color.RED, (
        ("12", "Delete Pay Period(s)", "delete_pay_period"),
        ("13", "Delete Invalid Date(s)", "delete_invalid_date"),
    )),
)
_ACTIONS = {
    key: method
    for _, _, options in _MENU_GROUPS
    for key, _, method in options
}


def _row(content: str = "") -> str:
    return c("  ║ ", Color.CYAN) + pad(content, _WIDTH - 2) + c(" ║", Color.CYAN)


def _option(key: str, label: str, color: str) -> str:
    return c(f"  {key}", color, Color.BOLD) + c(f"  {label}")


def menu() -> None:
    print(c("  ╔" + "═" * _WIDTH + "╗", Color.CYAN))
    print(_row(c("🧦  SOCKS CRUD INTERFACE", Color.BOLD, Color.CYAN)))
    print(_row(c("[b] back  [q] quit here  [exit()] quit all", Color.DIM)))

    for title, group_color, options in _MENU_GROUPS:
        print(c("  ╠" + "═" * _WIDTH + "╣", Color.CYAN))
        print(_row(c(f"  {title}", group_color, Color.BOLD)))
        for key, label, _ in options:
            print(_row(_option(key, label, group_color)))

    print(c("  ╠" + "═" * _WIDTH + "╣", Color.CYAN))
    print(_row(c("  m  Show menu", Color.DIM, Color.BOLD)))
    print(c("  ╚" + "═" * _WIDTH + "╝", Color.CYAN))
    print()


def main() -> None:
    commands = wrapper.Wrapper()
    menu()

    while True:
        try:
            choice = input(c("  ▶ Selection: ", Color.CYAN)).strip().lower()
            if choice in ("q", "exit()"):
                raise QuitApp
            if choice == "m":
                menu()
            elif choice in _ACTIONS:
                getattr(commands, _ACTIONS[choice])()
            elif choice:
                warning = c("⚠", Color.YELLOW)
                invalid_choice = c(repr(choice), Color.DIM)
                print(f"  {warning}  {invalid_choice} is not a valid option.\n")
        except QuitApp:
            break
        except KeyboardInterrupt:
            print()
            break

    print(f"\n  {c('🧦  Goodbye!', Color.CYAN, Color.BOLD)}\n")


if __name__ == "__main__":
    main()
