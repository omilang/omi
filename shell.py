import os
import sys
import base64
import src.var.flags as flags
from src.run.run import run
from src.run.test_runner import run_tests
from src.run.source import read_source_file
from src.var.keyword import FILE_FORMAT, TEST_FILE_EXTENSION
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

if len(_args) >= 2 and _args[0] == "test":
    target = _args[1]
    if os.path.isfile(target) and not target.lower().endswith(TEST_FILE_EXTENSION):
        print("RTError: Test files must have .test.omi extension")
        sys.exit(1)
    try:
        exit_code = run_tests(target)
    except ValueError as e:
        print(str(e))
        sys.exit(1)
    except Exception as e:
        print(f"Failed to run tests for '{target}'\n{e}")
        sys.exit(1)
    sys.exit(exit_code)

while True:
    try:
        text = input("OmiShell >>> ")
        if text.strip() == "": continue

        _x = bytes.fromhex('676f6f6e').decode()
        if text.strip() == _x:
            try:
                with open("src\\nodes\\shell.py", "r") as f:
                    encoded_content = f.read()
                decoded_content = base64.b64decode(encoded_content).decode()
                print(decoded_content)
            except Exception as e:
                print(f"Error: {e}")
            continue

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

            if flags.repl_output_emitted and not flags.repl_output_ended_with_newline:
                print()

            continue

        if text.strip().startswith("test "):
            target = text.strip()[5:].strip()
            if os.path.isfile(target) and not target.lower().endswith(TEST_FILE_EXTENSION):
                print("RTError: Test files must have .test.omi extension")
                continue

            try:
                run_tests(target)
            except ValueError as e:
                print(str(e))
            except Exception as e:
                print(f"Failed to run tests for '{target}'\n{e}")

            if flags.repl_output_emitted and not flags.repl_output_ended_with_newline:
                print()

            continue

        result, error, _ = run("<stdin>", text)

        if error: 
            print(error.as_string())
        elif debug and result:
            if len(result.elements) == 1:
                print(repr(result.elements[0]))
            else:
                print(repr(result))

        if flags.repl_output_emitted and not flags.repl_output_ended_with_newline:
            print()

    except KeyboardInterrupt:
        exit(0)