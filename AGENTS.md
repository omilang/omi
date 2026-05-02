# Omi Language Interpreter - Agent Guide

Omi is an interpreted programming language built in Python. This guide covers essential context for agents working on the codebase.

## Project Structure

- **src/main/** - Core interpreter: lexer, parser, symbol table, AST interpretation
  - `lexer.py` - Tokenization
  - `parser/` - AST construction
  - `interpret.py` - Main entry point for interpretation
  - `interpreter/` - Execution engine (control flow, functions, async, testing, modules)
- **src/run/** - Runtime execution and test infrastructure
  - `run.py` - Main execution wrapper
  - `test_runner.py` - Test suite runner with reporter
  - `typecheck.py` - Type checking
  - `async_runtime.py` - Async/await support
- **src/linter/** - Linting and auto-fix system
  - `runner.py` - Lint execution
  - `rule.py` - Rule definitions
  - `fixer.py` - Auto-fix logic
- **src/stdlib/** - Standard library modules (color, files, http, json, log, math, paths, python, regex, string, system, time, txt)
- **src/var/** - Constants, keywords, tokens, type system, flags, builtin functions
- **shell.py** - CLI entry point (main command dispatcher)
- **tests/** - Test files and custom test runners (not pytest-based)

## File Formats

- `.omi` - Omi source files
- `.test.omi` - Test files (suite/test structure with expect assertions)
- `.omilint` - Lint configuration (INI format)

## Key Commands

```bash
# Run a file
python shell.py run <file.omi>
omi run <file.omi>

# Run tests (single file or directory)
python shell.py test <file.test.omi>
python shell.py test tests/

# Lint a file or directory
python shell.py lint <file.omi>
python shell.py lint <file.omi> --fix

# Interactive REPL
python shell.py
omi
```

## Testing

- **Native test runner**: `omi test <file.test.omi>` - Runs `.test.omi` files with suite/test/expect syntax
- **Custom Python test runners**: `tests/run_*.py` - Direct Python scripts that test specific features
  - `run_error_tests.py` - Error handling validation
  - `run_async_tests.py` - Async/await behavior
  - `run_color_tests.py` - Color module output
  - `run_defer_files_tests.py` - File defer handling
  - `run_io_builtin_tests.py` - I/O functions
  - `run_try_match_tests.py` - Exception/match handling
  - `run_for_iter.py` - For loop iteration

Run custom tests: `python tests/run_error_tests.py`

## Language Syntax

- **Keywords**: and, as, async, break, case, catch, const, continue, defer, elif, else, end, enum, final, for, func, if, import, is, isnt, match, or, return, set, step, to, trait, try, type, use, var, while
- **Directives**: `@import`, `@set`, `@use`
- **Preprocessor**: `@set` directives enable variable substitution before parsing

## Linting

- Config file: `.omilint` (INI format with `[general]` and `[rules]` sections)
- Lint directives in code: `@use level as <level>`, `@use rules as <rule1,rule2>`, `@use fix`, `@use json`, `@use failfast`
- Severity levels: error, warning, style, security
- Auto-fix support: `--fix` flag applies fixes to source files
- JSON output: `--json` flag for machine-readable lint reports

## Runtime Flags

Located in `src/var/flags.py`. Key flags:
- `notypes` - Disable type checking
- `noecho` - Suppress REPL output
- `noasync` - Disable async/await (with warning)
- `debug` - Print AST after execution
- `no_colors` - Disable ANSI colors

## Type System

- Defined in `src/var/type_system.py`
- Supports: int, string, bool, array, dict, null, void, generics
- Type annotations: `var<type>`, `func<return_type>`, `array<type>`
- Nullable types: `var<type|null>`

## Execution Flow

1. **shell.py** parses CLI args and dispatches to appropriate handler
2. **run.py** or **test_runner.py** loads source file
3. **Lexer** tokenizes source → **Parser** builds AST
4. **Preprocessor** handles `@import` and `@use` directives
5. **Interpreter** executes AST with symbol table and context
6. **Async runtime** manages event loop for async functions
7. **Test reporter** collects and formats test results

## Common Patterns

- **Error handling**: Errors are objects with `as_string()` method; check `err` return value from `run()`
- **Symbol table**: Global and local scopes; functions create new scope
- **Async execution**: `async func` keyword; `await` for futures; `async group` for concurrent execution
- **Module imports**: `@import "module_name" as alias` or `@import "omi:stdlib_module"`
- **Test structure**: Suites contain tests; tests use `expect` assertions; `before_each`/`after_each` hooks

## Important Quirks

- **Encoding**: Source files support utf-8-sig, utf-8, cp1251 (see `SOURCE_FILE_ENCODINGS`)
- **Color output**: Uses ANSI codes; disabled with `--nocolors` flag
- **Test directives**: `@use save` only works in `.test.omi` files
- **Linter config**: Can be inline (`@use`) or in `.omilint` file; inline takes precedence
- **Async strictness**: By default, sync functions can be called with `await`; `@use strict` enforces async-only calls
- **Type checking**: Enabled by default; disabled with `--notypes` flag or `notypes` flag in code

## Development Notes

- Python 3.11+ required
- No pytest dependency; custom test infrastructure
- Linter uses rule-based system with auto-fix capability
- Async runtime uses asyncio event loop
- Symbol table tracks variable initialization state (catches uninitialized access)
