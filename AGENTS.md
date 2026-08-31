# AGENTS.md — Omi Language Project Context & Agent Reference

## 1. Project Overview & Tech Stack
- **Language**: Omi (interpreted dynamic language with optional/strict type checking, async runtime, native testing DSL, and built-in linter).
- **Implementation**: Python 3.11+ (no external runtime dependencies for core interpretation).
- **CLI Entry Point**: `shell.py` (executable as `omi` or `python shell.py`).
- **File Extensions**:
  - `.omi`: Omi source files.
  - `.test.omi`: Native Omi test suite files.
  - `.omilint`: Linter configuration files (INI-style format).
- **Source File Encodings**: Attempted in order: `utf-8-sig`, `utf-8`, `cp1251` (see `src/run/source.py`).
- **Project Structure**: Packaged as `omilang` via `pyproject.toml` with console entry point `omi = "shell:main"`.

---

## 2. Agent Constraints & Coding Rules
- **No Comments in Code**: Do not write comments in any source code files (`.py`, `.omi`, etc.).
- **Tests & Examples in `/tests`**: All verification, test cases, and usage examples must be placed in `tests/`.
- **No Pytest**: Tests are written in `.test.omi` format (run via `omi test`) or as Python runner scripts (`tests/run_*.py`).
- **Error Handling**: Functions in the pipeline return `RTResult` or `(result, error, flags)`. Check `error` explicitly before accessing results.
- **Visitor Pattern**: Interpreter AST visitors follow `visit_<NodeName>(self, node, context)` returning `RTResult`.

---

## 3. CLI Commands & Options
- `python shell.py run <file.omi> [lint-flags] [-- script_args...]`: Run source file (runs linter before execution by default unless `--nolint` or `@use nolint` is set).
- `python shell.py test <file.test.omi|directory> [--failfast] [--json] [--save[=path]] [--nocolors]`: Run native test suites.
- `python shell.py lint <file.omi|directory> [--fix] [--json] [--failfast] [--level=<level>] [--rules=<r1,r2>] [--config[=path]] [--nocolors]`: Run static analyzer.
- `python shell.py` (no args): Start interactive REPL (`OmiShell >>>`).
- **Global Flags**:
  - `-v`, `--version`: Print version and exit.
  - `-h`, `--help`: Print CLI help text.
  - `-d`, `--debug`: Enable verbose debug AST representation output.
  - `--nocolors`: Disable ANSI color formatting in output.

---

## 4. Execution Pipeline & Architecture
```
Source Code (.omi / .test.omi)
       │
       ▼
1. Preprocessor (`src/preprocessor.py`)
   - Scans and applies text substitutions from `@set Source as Alias`
       │
       ▼
2. Lexer (`src/main/lexer.py`)
   - Tokenizes source text into `Token` objects (`src/tokens.py`, `src/var/token.py`)
   - Handles numbers, strings, f-strings `~name` / `~(expr)`, operators, symbols, keywords
       │
       ▼
3. Parser (`src/main/parser/parser.py`)
   - Recursive descent parser with operator precedence
   - Builds AST Nodes (`src/nodes/`) using `ParseResult` (`src/main/parser/result.py`)
       │
       ▼
4. Interpreter (`src/main/interpret.py`)
   - Walks AST nodes using `visit_*` methods
   - Evaluates expressions with `Context` (`src/run/context.py`) and `SymbolTable` (`src/main/symboltable.py`)
   - Enforces runtime type checks (`src/run/typecheck.py`)
   - Returns `RTResult` (`src/run/runtime.py`) holding value, runtime error, or control signal
       │
       ▼
5. Async Event Loop (`src/run/async_runtime.py`)
   - Drains pending background tasks registered in `FutureValue` objects
```

---

## 5. Codebase Directory Map

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| `src/` | Root source package | `tokens.py`, `position.py`, `arrow.py`, `preprocessor.py` |
| `src/main/` | Core compiler & runtime engine | `lexer.py`, `interpret.py`, `symboltable.py`, `parser/parser.py`, `parser/result.py` |
| `src/nodes/` | AST node class definitions | `types/`, `ops/`, `variables/`, `condition/`, `loops/`, `function/`, `jump/`, `imports/`, `directives/`, `control/` |
| `src/values/` | Runtime value wrappers | `value.py`, `convert.py`, `future.py`, `types/` (`number.py`, `string.py`, `list.py`, `dict.py`, `boolean.py`, `null.py`, `void.py`, `module.py`, `filehandle.py`), `function/` (`base.py`, `function.py`, `buildin.py`, `stdlib.py`) |
| `src/error/` | Error types & formatting | `error.py`, `message/` (`illegalchar.py`, `expectedchar.py`, `invalidsyntax.py`, `rt.py`) |
| `src/run/` | Execution pipeline & runners | `run.py`, `runtime.py`, `context.py`, `source.py`, `typecheck.py`, `test_runner.py`, `async_runtime.py` |
| `src/stdlib/` | Built-in standard modules | `system.py`, `files.py`, `color.py`, `paths.py`, `time.py`, `math.py`, `json.py`, `http.py`, `txt.py`, `string.py`, `regex.py`, `log.py` |
| `src/linter/` | Static analysis & lint rules | `runner.py`, `rules.py`, `config.py`, `context.py`, `reporter.py`, `fixer.py` |
| `src/var/` | Constants, tokens, keywords | `token.py`, `keyword.py`, `constant.py`, `flags.py`, `ansi.py`, `builtin.py` |
| `tests/` | Native tests & Python test scripts | `*.test.omi`, `run_*.py` |
| `docs/` | Comprehensive documentation | `Architecture.md`, `Documentation.md`, `LanguageSpec.md`, `Linter.md`, `Modules.md`, `Tests.md` |

---

## 6. Language Syntax & Core Semantics

### Variables & Constants
- Variables: `var<Type> name = expr` or uninitialized `var<Type> name`.
- Typed Arrays: `var[Type] name = [...]` or bounded `var<Type>(max_size) name = [...]`.
- Constants: `const<Type> name = expr` (must be initialized; cannot be reassigned or mutated).

### Types & Type System
- Built-in Types: `int`, `float`, `number`, `bool`, `string`, `array`, `dict`, `null`, `void`, `every`, `call`, `future<T>`.
- Type Checking: Enabled by default. Disable in a file using `@use notypes`.
- Unions: `int | string`.
- Nullable: `int?` (desugars to `int | null`).
- `void`: Return type for functions returning no value (bare `return`).
- `null`: Explicit null value and its type.
- `every`: Any type accepted.
- User Types:
  - Structured Dict: `type User = { name<string>, age<int?>, nested: { id<int> } }`
  - Union Alias: `type Status = "ok" | "error"`
  - Enum: `enum Result<T, E> = { Ok(T), Err(E) }`
  - Trait: `trait Printable = { print_info<func> }`

### Operators & Expressions
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `^` (power).
- Comparison: `==`, `!=`, `<`, `>`, `<=`, `>=`.
- Logical: `and`, `or`, `is`, `isnt`.
- Membership: `elem in collection` (arrays, strings, dicts).
- Ternary: `value_if_true ~ condition ~ value_if_false`.
- Null Coalescing: `left ?? fallback` (evaluates right if left is `Null` or `Void`).
- Compound Assignment: `+=`, `-=`, `*=`, `/=`, `%=`.
- Increment / Decrement: Prefix (`++x`, `--x`) returns new value; postfix (`x++`, `x--`) returns old value. Works on identifiers and subscript elements `arr[i]++`, `dict["k"]++`.
- Slicing: `collection[start:end]` or `collection[start:end:step]`.

### Control Flow
- Conditionals:
  ```omi
  if condition:
      ...
  elif other_condition:
      ...
  else:
      ...
  end
  ```
- Loops:
  - Step loop: `for i = 0 to 10 step 2: ... end`
  - Iterator loop: `for item in items: ... end`
  - While loop: `while condition: ... end`
  - Loop jump: `break`, `continue`.
- Defer Statement: `defer expr` (executes on block exit, LIFO order).
- Error Handling:
  ```omi
  try:
      throw "error message"
  catch err:
      println(err.type)
      println(err.msg)
      println(err.trace)
  final:
      println("cleanup")
  end
  ```
- Pattern Matching:
  ```omi
  match expr:
      case 1:
          ...
      case Result.Ok(val):
          ...
      case _:
          ...
  end
  ```

### Functions
- Long form: `func<ReturnType> name(arg1<Type>, arg2<Type> = default): ... end`
- Short form: `func<ReturnType> name(args) -> expr`
- Named & Positional Arguments: `name(1, arg2=2)` (positional must precede named).

### Directives & Imports
- Directives begin with `@` and execute before main interpretation:
  - `@use <flag>`: `notypes`, `eval`, `debug`, `noecho`, `noasync`, `module`, `nolint`, `json`, `fix`, `failfast`, `level`, `rules`, `config`, `save`.
  - `@import "omi:<name>" as <alias>`: Import standard library module.
  - `@import "<relative_path>" as <alias>`: Import user `.omi` module (imported file must have `@use module`).
  - `@set <Target> as <Alias>`: Preprocessor replacement (e.g. `@set models.User as User`).

### Async & Futures
- Async function: `async func<ReturnType> name(args): ... end`
- Schedule async call: `var<future<T>> fut = async name(args)` (returns `FutureValue`).
- Await: `var<T> res = async fut` (unwraps future; valid only inside `async func`, `async test`, or async groups).
- Async groups: `async group_name(timeout: 5.0): ... end`.
- Cancel task: `cancel(fut)` or `cancel(group_name)`.
- Mode `@use noasync`: Runs async calls synchronously with warnings.

---

## 7. Standard Library Reference (`omi:...`)

| Module | Key Functions & Constants |
|--------|---------------------------|
| `omi:system` | `args()`, `argv()`, `exec(cmd)`, `exit(code)`, `getenv(name)`, `setenv(name, val)`, `platform()`, `cpu_count()` |
| `omi:files` | `read(p)`, `write(p, data)`, `append(p, data)`, `exists(p)`, `remove(p)`, `mkdir(p)`, `rmdir(p)`, `list(p)`, `copy(src, dst)`, `move(src, dst)`, `open(p, m)`, `close(h)`, `read_handle(h, n)`, `write_handle(h, data)` |
| `omi:paths` | `join(...)`, `abs(p)`, `dir(p)`, `base(p)`, `ext(p)`, `name(p)`, `exists(p)`, `is_file(p)`, `is_dir(p)` |
| `omi:time` | `now()`, `timestamp()`, `sleep(secs)`, `format(ts, fmt)`, `parse(str, fmt)`, `timezone()` |
| `omi:math` | `pi`, `e`, `inf`, `nan`, `sin(x)`, `cos(x)`, `tan(x)`, `sqrt(x)`, `abs(x)`, `floor(x)`, `ceil(x)`, `round(x, n)`, `random()`, `randint(min, max)` |
| `omi:json` | `parse(str)`, `stringify(val, indent)`, `read(p)`, `write(p, val, indent)`, `append(p, val)`, `exists(p)` |
| `omi:http` | `get(url, h)`, `post(url, body, h)`, `put(url, body, h)`, `patch(url, body, h)`, `delete(url, h)`, `request(opts)`, `download(url, dst)`, `upload(url, p)` |
| `omi:txt` | `read(p)`, `write(p, txt)`, `append(p, txt)`, `lines(p)`, `write_lines(p, arr)`, `size(p)`, `exists(p)`, `backup(p)` |
| `omi:string` | `split(s, sep)`, `join(arr, sep)`, `replace(s, old, new)`, `trim(s)`, `ltrim(s)`, `rtrim(s)`, `upper(s)`, `lower(s)`, `pad_left(s, n, c)`, `pad_right(s, n, c)`, `starts_with(s, p)`, `ends_with(s, p)`, `contains(s, sub)` |
| `omi:regex` | `test(pat, s)`, `match(pat, s)`, `find_all(pat, s)`, `replace(pat, repl, s)`, `split(pat, s)` |
| `omi:color` | `red(s)`, `green(s)`, `blue(s)`, `yellow(s)`, `cyan(s)`, `magenta(s)`, `bold(s)`, `rgb(r, g, b, s)`, `disable()`, `enable()` |
| `omi:log` | `debug(msg)`, `info(msg)`, `warn(msg)`, `error(msg)`, `set_level(lvl)`, `set_file(p)`, `set_json(bool)` |

---

## 8. Native Test System (`.test.omi`)

Test structure:
```omi
suite "Suite Name":
    before:
        // setup once per suite
    end

    before_each:
        // setup before each test
    end

    test "sync test description":
        expect 1 + 1 == 2
        expect true ~ "assertion failure message"
    end

    async test "async test description":
        var<future<int>> fut = async some_async_op()
        var<int> res = async fut
        expect res > 0
    end

    skip test "skipped test description":
        expect false
    end

    after_each:
        // cleanup after each test
    end

    after:
        // cleanup once per suite
    end
end
```
- Run tests: `python shell.py test <target> [--failfast] [--json] [--save[=path]] [--nocolors]`
- Directives allowed in `.test.omi`: `@use json`, `@use failfast`, `@use save`, `@use save as "path.json"`.

---

## 9. Linter Subsystem

- Config file: `.omilint` (INI format with sections `[general]`, `[rules]`, `[auto-fix]`).
- Severities: `error`, `warning`, `style`, `security`.
- Rule Categories:
  - Error: `undefined-var`, `type-mismatch`, `const-reassign`, `missing-return`, `invalid-import`, `duplicate-param`, `unreachable-code`.
  - Warning: `unused-var`, `unused-import`, `prefer-const`, `no-shadow`, `prefer-nullable`, `division-by-zero-risk`.
  - Style: `naming-convention`, `max-line-length`, `trailing-whitespace`, `spacing-operators`, `empty-lines`.
  - Security: `eval-usage`, `unsafe-import`, `hardcoded-secret`.
- Auto-fix: Invoked with `--fix` or `@use fix`.
- Standalone: `python shell.py lint <target>` (exit codes: 0 = clean, 1 = errors, 2 = warnings/style/security).

---

## 10. Runtime Internals & Common Extension Points

- **Adding a new AST node**:
  1. Define node in `src/nodes/<category>/<nodename>.py` inheriting from `Node` (storing `pos_start`, `pos_end`).
  2. Export in appropriate `__init__.py`.
  3. Add parsing method/branch in `src/main/parser/parser.py`.
  4. Add `visit_<NodeName>(self, node, context)` in `src/main/interpret.py`.
  5. Add lint visitor handlers if static checks are affected in `src/linter/rules.py`.
- **Adding a new Value type**:
  1. Define class in `src/values/types/<typename>.py` inheriting from `Value` (`src/values/value.py`).
  2. Implement operators (`added_to`, `subbed_by`, `multed_by`, `dved_by`, `get_comparison_eq`, etc.).
  3. Register type in `src/run/typecheck.py` type map.
- **Adding a Standard Library Module**:
  1. Create module in `src/stdlib/<name>.py` exporting `create_<name>_module(context)` returning a `Module` value populated with `StdlibFunction` entries.
  2. Register in `BUILTIN_MODULES` in `src/var/builtin.py`.