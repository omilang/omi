import os
import sys
from src.run.run import run
from src.run.source import read_source_file
from src.var.keyword import FILE_FORMAT
from src.var.constant import VERSION, HELP_TEXT

debug = ("--debug" in sys.argv) or ("-d" in sys.argv)

if ("--version" in sys.argv) or ("-v" in sys.argv):
    print(f"Omi {VERSION}")
    sys.exit(0)

if ("--help" in sys.argv) or ("-h" in sys.argv):
    print(HELP_TEXT, end="")
    sys.exit(0)

_args = [a for a in sys.argv[1:] if not a.startswith("-")]
if len(_args) >= 2 and _args[0] == "run":
    fn = _args[1]
    _, file_extension = os.path.splitext(fn)
    if file_extension not in FILE_FORMAT:
        print("Invalid file format (expected .omi)")
        sys.exit(1)
    try:
        script = read_source_file(fn)
    except Exception as e:
        print(f"Failed to load script \"{fn}\"\n{e}")
        sys.exit(1)
    result, error, file_flags = run(fn, script)
    if error:
        print(error.as_string())
        sys.exit(1)
    elif (debug or file_flags.get("debug", False)) and result:
        if len(result.elements) == 1:
            print(repr(result.elements[0]))
        else:
            print(repr(result))
    sys.exit(0)

while True:
    try:
        text = input("OmiShell >>> ")
        if text.strip() == "": continue

        if text.strip().startswith("run "):
            fn = text.strip()[4:].strip()
            filename, file_extension = os.path.splitext(fn)

            if file_extension not in FILE_FORMAT:
                print("Invalid file format (expected .omi)")
                continue

            try:
                script = read_source_file(fn)
            except Exception as e:
                print(f"Failed to load script \"{fn}\"\n{e}")
                continue

            result, error, file_flags = run(fn, script)
            if error:
                print(error.as_string())
            elif (debug or file_flags.get('debug', False)) and result:
                if len(result.elements) == 1:
                    print(repr(result.elements[0]))
                else:
                    print(repr(result))
            continue

        result, error, _ = run("<stdin>", text)

        if error: 
            print(error.as_string())
        elif debug and result:
            if len(result.elements) == 1:
                print(repr(result.elements[0]))
            else:
                print(repr(result))
    except KeyboardInterrupt:
        exit(0)