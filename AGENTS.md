# Omi: short agent notes
1. Project: Omi language interpreter in Python 3.11+, CLI entry point is `shell.py`.
2. Core lives in `src/main/`: `lexer.py`, `parser/`, `interpret.py`, `interpreter/`.
3. Runtime and checks live in `src/run/`: `run.py`, `test_runner.py`, `typecheck.py`, `async_runtime.py`.
4. Linter is in `src/linter/`, stdlib is in `src/stdlib/`, constants and types are in `src/var/`.
5. Formats: source `.omi`, tests `.test.omi`, linter config `.omilint`.
6. Commands: `python shell.py run <file.omi>`, `python shell.py test <path>`, `python shell.py lint <path>`.
7. Tests do not use pytest: there are Omi tests and Python runners in `tests/run_*.py`.
8. Execution flow: CLI -> lexer -> parser -> preprocessor `@import/@use/@set` -> interpreter.
9. Errors usually return as `err` with `as_string()`; remember to check the `run()` result.
10. Key quirks: types are on by default, async uses `async/await`, encodings are `utf-8-sig`, `utf-8`, `cp1251`.

# Notes
- Don't write comments in the code
- Write everything for testing and examples of use to test files in /tests