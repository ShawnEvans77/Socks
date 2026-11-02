import re
import unicodedata


class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


_ANSI_ESCAPE = re.compile(r"\033\[[0-9;]*m")


def color(text: object, *codes: str) -> str:
    return "".join(codes) + str(text) + Color.RESET


def visible_width(text: str) -> int:
    plain = _ANSI_ESCAPE.sub("", text)
    return sum(
        2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
        for char in plain
    )


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - visible_width(text))
