import string

DIGITS = "0123456789"
LETTERS = string.ascii_letters
LETTERS_DIGITS = LETTERS + DIGITS

SOURCE_FILE_ENCODINGS = (
    "utf-8-sig",
    "utf-8",
    "cp1251",
)

VERSION = "1.2.0"

HELP_TEXT = f"""\
Omi {VERSION}
Copyright 2026 Qualsu. Distributed under the MIT License.

USAGE
  python shell.py [flags]
  python shell.py run <file.omi> [flags]

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