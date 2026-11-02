from src.utils.terminal import Color, color


class QuitApp(Exception):
    """Raised when the user enters the global quit command."""


class BackApp(Exception):
    """Raised when the user enters the prompt-level back command."""


def rule(char: str = "─", width: int = 50) -> None:
    print(color("  " + char * width, Color.DIM))


def blank() -> None:
    print()


def success(message: str) -> None:
    print(f"  {color('✔  ' + message, Color.GREEN)}")


def error(message: str) -> None:
    print(f"  {color('✘  ' + message, Color.RED)}")


def warn(message: str) -> None:
    print(f"  {color('⚠  ' + message, Color.YELLOW)}\n")


def info(message: str) -> None:
    print(f"  {color('ℹ  ' + message, Color.CYAN)}")


def section(step: int, total: int, title: str) -> None:
    blank()
    rule()
    print(f"{color(f'  [{step}/{total}]', Color.DIM)}  {color(title, Color.BOLD, Color.CYAN)}")
    rule()
    blank()


def prompt(label: str, hint: str = "") -> str:
    if hint:
        print(color(f"  ({hint})", Color.DIM))
    raw = input(color(f"  ▶ {label}: ", Color.CYAN)).strip()
    command = raw.casefold()
    if command == "exit()":
        raise QuitApp
    if command == "b":
        raise BackApp
    return raw


def yes_no(label: str) -> bool:
    while True:
        answer = prompt(label, hint="y / n").casefold()
        if answer == "y":
            return True
        if answer == "n":
            return False
        warn("Please enter y or n.")


_LOGO = (
    "  ███████╗  ██████╗  ██████╗██╗  ██╗███████╗",
    "  ██╔════╝ ██╔═══██╗██╔════╝██║ ██╔╝██╔════╝",
    "  ███████╗ ██║   ██║██║     █████╔╝ ███████╗ ",
    "  ╚════██║ ██║   ██║██║     ██╔═██╗ ╚════██║ ",
    "  ███████║ ╚██████╔╝╚██████╗██║  ██╗███████║ ",
    "  ╚══════╝  ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝ ",
)


def banner() -> None:
    blank()
    for line in _LOGO:
        print(color(line, Color.CYAN, Color.BOLD))
    blank()
    rule("═")
    print(color("  [exit()] at any prompt to quit. [b] to go back", Color.DIM))
    rule("═")
