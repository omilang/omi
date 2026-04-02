import os
import sys
from src.run.run import run
from src.var.keyword import FILE_FORMAT

debug = "--debug" in sys.argv

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
                with open(fn, "r") as f:
                    script = f.read()
            except Exception as e:
                print(f"Failed to load script \"{fn}\"\n{e}")
                continue

            result, error = run(fn, script)
            if error:
                print(error.as_string())
            elif debug and result:
                if len(result.elements) == 1:
                    print(repr(result.elements[0]))
                else:
                    print(repr(result))
            continue

        result, error = run("<stdin>", text)

        if error: 
            print(error.as_string())
        elif debug and result:
            if len(result.elements) == 1:
                print(repr(result.elements[0]))
            else:
                print(repr(result))
    except KeyboardInterrupt:
        exit(0)