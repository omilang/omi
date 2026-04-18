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
Copyright 2026 Qualsu. Distributed under the MIT License

USAGE
  python shell.py [flags]
  python shell.py run <file.omi> [flags]
  python shell.py test <file.test.omi|directory> [flags]
  python shell.py lint <file.omi|directory> [flags]

FLAGS
  main
  --version | -v   Print the Omi version and exit
  --help    | -h   Show this help message and exit
  --debug   | -d   Print the parsed AST result after execution
  lint
  --fix            Apply auto-fixes when possible
  --json           Print lint report as JSON
  --failfast       Stop after lint errors when used with run --lint
  --level=<name>   Filter by severity level
  --rules=<list>   Comma-separated list of rule names
  --config[=path]  Load lint config from .omilint or the provided path
  test
  --failfast       Stop after first failed test
  --json           Print test report as JSON
  --save[=path]    Save JSON report to file

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
