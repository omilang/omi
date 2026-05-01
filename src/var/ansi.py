import os
import re
import sys

import src.var.flags as runtime_flags

ANSI_CODES = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "italic": "\033[3m",
    "underline": "\033[4m",
    "blink": "\033[5m",
    "reverse": "\033[7m",
    "hidden": "\033[8m",
    "strikethrough": "\033[9m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bg_black": "\033[40m",
    "bg_red": "\033[41m",
    "bg_green": "\033[42m",
    "bg_yellow": "\033[43m",
    "bg_blue": "\033[44m",
    "bg_magenta": "\033[45m",
    "bg_cyan": "\033[46m",
    "bg_white": "\033[47m",
}

_CLEAR_SEQ = "\033[2J\033[H"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_SUPPORT_CACHE = None


def _enable_windows_vt_mode():
    if os.name != "nt":
        return True

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        if handle == 0 or handle == -1:
            return False

        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)) == 0:
            return False

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        new_mode = ctypes.c_uint32(mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
        if kernel32.SetConsoleMode(handle, new_mode) == 0:
            return False

        return True
    except Exception:
        return False


def supported():
    global _SUPPORT_CACHE
    if _SUPPORT_CACHE is not None:
        return _SUPPORT_CACHE

    if os.environ.get("NO_COLOR"):
        _SUPPORT_CACHE = False
        return _SUPPORT_CACHE

    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        _SUPPORT_CACHE = False
        return _SUPPORT_CACHE

    _SUPPORT_CACHE = _enable_windows_vt_mode()
    return _SUPPORT_CACHE


def enabled():
    return supported() and not runtime_flags.no_colors


def enable():
    runtime_flags.no_colors = False
    return enabled()


def disable():
    runtime_flags.no_colors = True
    return False


def code(name):
    value = ANSI_CODES.get(name, "")
    if not value:
        return ""
    return value if enabled() else ""


def rgb_code(r, g, b):
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"\033[38;2;{r};{g};{b}m"


def bg_rgb_code(r, g, b):
    r = max(0, min(255, int(r)))
    g = max(0, min(255, int(g)))
    b = max(0, min(255, int(b)))
    return f"\033[48;2;{r};{g};{b}m"


def wrap(text, *style_names):
    text = str(text)
    if not enabled():
        return text
    prefix = "".join(ANSI_CODES.get(name, "") for name in style_names)
    if not prefix:
        return text
    return f"{prefix}{text}{ANSI_CODES['reset']}"


def wrap_codes(text, *codes):
    text = str(text)
    if not enabled():
        return text
    prefix = "".join(c for c in codes if c)
    if not prefix:
        return text
    return f"{prefix}{text}{ANSI_CODES['reset']}"


def reset_after(text):
    text = str(text)
    if not enabled():
        return text
    return f"{text}{ANSI_CODES['reset']}"


def clear_seq():
    return _CLEAR_SEQ if enabled() else ""


def strip_ansi(text):
    return _ANSI_RE.sub("", str(text))
