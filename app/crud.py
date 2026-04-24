from src.utils import wrapper
from src.utils.wrapper import QuitApp, Color, c

# ─── Menu ─────────────────────────────────────────────────────────────────────

_W = 44  # visible box width (inner)

def _row(content: str = "") -> str:
    """Build a ║…║ box row padded to _W visible chars."""
    return c("  ║ ", Color.CYAN) + _pad(content, _W - 2) + c(" ║", Color.CYAN)

def _pad(s: str, width: int) -> str:
    import re, unicodedata
    stripped = re.sub(r"\033\[[0-9;]*m", "", s)
    visible  = sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in stripped)
    return s + " " * max(0, width - visible)

def menu():
    top    = c("  ╔" + "═" * _W + "╗", Color.CYAN)
    div    = c("  ╠" + "═" * _W + "╣", Color.CYAN)
    bot    = c("  ╚" + "═" * _W + "╝", Color.CYAN)

    title  = c("🧦  SOCKS CRUD INTERFACE", Color.BOLD + Color.CYAN)
    hint   = c("[b] back inside any operation  [q] quit", Color.DIM)

    def group(label: str, color: str) -> str:
        return c(label, color + Color.BOLD)

    def opt(key: str, label: str, color: str) -> str:
        return c(f"  {key}", color + Color.BOLD) + c(f"  {label}", Color.RESET)

    print(top)
    print(_row(title))
    print(_row(hint))
    print(div)
    print(_row(group("  CREATE", Color.GREEN)))
    print(_row(opt("1", "New Pay Period",          Color.GREEN)))
    print(_row(opt("2", "New Invalid Date",         Color.GREEN)))
    print(_row(group("  READ", Color.BLUE)))
    print(_row(opt("3", "View Pay Period Schedule", Color.BLUE)))
    print(_row(opt("4", "View Invalid Dates",       Color.BLUE)))
    print(_row(group("  UPDATE", Color.YELLOW)))
    print(_row(opt("5", "Update Pay Period",        Color.YELLOW)))
    print(_row(opt("6", "Update Invalid Date",      Color.YELLOW)))
    print(_row(group("  DELETE", Color.RED)))
    print(_row(opt("7", "Delete Pay Period(s)",     Color.RED)))
    print(_row(opt("8", "Delete Invalid Date(s)",   Color.RED)))
    print(div)
    print(_row(c("  m", Color.DIM + Color.BOLD) + c("  Show menu", Color.DIM)))
    print(bot)
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    wp = wrapper.Wrapper()
    menu()

    while True:
        try:
            choice = input(c("  ▶ Selection: ", Color.CYAN)).strip().lower()

            match choice:
                case "1": wp.create_pay_period()
                case "2": wp.create_invalid_date()
                case "3": wp.read_pay_period_start_end()
                case "4": wp.read_invalid_dates()
                case "5": wp.update_pay_period()
                case "6": wp.update_invalid_date()
                case "7": wp.delete_pay_period()
                case "8": wp.delete_invalid_date()
                case "m": menu()
                case "q": raise QuitApp
                case "":  pass
                case _:
                    print(f"  {c('⚠', Color.YELLOW)}  {c(repr(choice), Color.DIM)} is not a valid option.\n")

        except QuitApp:
            break
        except KeyboardInterrupt:
            print()
            break

    print(f"\n  {c('🧦  Goodbye!', Color.CYAN + Color.BOLD)}\n")


if __name__ == "__main__":
    main()
