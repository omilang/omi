import string
import logging as _logging

DIGITS = "0123456789"
LETTERS = string.ascii_letters
LETTERS_DIGITS = LETTERS + DIGITS

SOURCE_FILE_ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp1251",
)

VERSION = "1.5.0"

HELP_TEXT = f"""\
Omi {VERSION}
Copyright 2026 Qualsu. Distributed under the MIT License.

USAGE
  python shell.py [flags]
  python shell.py run <file.omi> [flags]
  python shell.py test <file.test.omi|directory> [flags]

FLAGS
  --version | -v   Print the Omi version and exit
  --help    | -h   Show this help message and exit
  --debug   | -d   Print the parsed AST result after execution

LINKS
  Website          https://omilang.fun
  Source code      https://github.com/omilang/omi
  Documentation    https://github.com/omilang/docs
  VS Code ext.     https://github.com/omilang/vscode-extension
"""

LEVEL_NAMES = {
    "DEBUG": _logging.DEBUG,
    "INFO": _logging.INFO,
    "WARNING": _logging.WARNING,
    "ERROR": _logging.ERROR,
    "CRITICAL": _logging.CRITICAL,
}

SIZE_UNITS = {
    "B": 1,
    "KB": 1024,
    "MB": 1024 * 1024,
    "GB": 1024 * 1024 * 1024,
}

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "omi.log"
DEFAULT_LOG_MODE = "a"
DEFAULT_MAX_SIZE = "10MB"
DEFAULT_BACKUP_COUNT = 5
