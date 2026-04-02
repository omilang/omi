# OmiLang Modules

> Reference for built-in modules

---

## Navigation

- [Documentation](Documentation.md) - syntax, types, functions, imports
- [Modules (this page)](Modules.md) - built-in modules
- [Architecture](Architecture.md) - project structure and interpreter internals

---

## Contents

- [How to Import a Module](#how-to-import-a-module)
- [system](#system)
- [files](#files)
- [paths](#paths)
- [time](#time)
- [math](#math)

---

## How to Import a Module

Built-in modules are imported the same way as user files, using `@import`:

```py
@import "system" as sys
```

After import, all module functions are available through the alias (`sys` in this example).

---

## system

Module for OS interaction: command execution, environment variables, platform info, and process control.

```py
@import "system" as sys
```

| Function | Description |
|---------|----------|
| `sys.exec(command)` | Runs a shell command and returns output |
| `sys.env(name)` | Gets an environment variable |
| `sys.set_env(name, value)` | Sets an environment variable |
| `sys.platform()` | Returns OS name: `"Windows"`, `"Linux"`, `"Darwin"` |
| `sys.username()` | Current username |
| `sys.cwd()` | Current working directory |
| `sys.exit(code)` | Exits script with a status code |

```py
@import "system" as sys
print(sys.platform())
print(sys.username())
print(sys.cwd())
var out = sys.exec("echo hello")
print(out)
sys.exit(0)
```

---

## files

Module for file system operations: create/remove files and directories, copy, move, list.

```py
@import "files" as fs
```

| Function | Description |
|---------|----------|
| `fs.cwd()` | Current working directory |
| `fs.mkdir(path, parents)` | Creates directory. `parents=true` creates nested dirs |
| `fs.rm(path)` | Removes a file |
| `fs.rmdir(path)` | Removes a directory recursively |
| `fs.list(path)` | Returns directory entries |
| `fs.cp(src, dst)` | Copies file or directory |
| `fs.mv(src, dst)` | Moves / renames |

```py
@import "files" as fs

print(fs.cwd())
fs.mkdir("out/logs", true)
fs.cp("main.omi", "out/main.omi")
var entries = fs.list(".")
print(entries)
fs.rm("out/main.omi")
fs.rmdir("out")
```

---

## paths

Module for file and directory path utilities.

```py
@import "paths" as p
```

| Function | Description |
|---------|----------|
| `p.join(parts)` | Joins path parts from a list of strings |
| `p.abs(path)` | Converts relative path to absolute |
| `p.exists(path)` | `1` if file/dir exists, `0` otherwise |
| `p.ext(path)` | File extension (including dot, e.g. `".py"`) |
| `p.name(path)` | File name from path |

```py
@import "paths" as p

var full = p.join(["src", "stdlib", "files.py"])
print(full)

var absolute = p.abs(".")
print(absolute)

var ex = p.exists("main.omi")
if is ex:
  print("main.omi exists")
end

print(p.ext("main.omi"))   // .omi
print(p.name("src/run/run.py"))  // run.py
```

---

## time

Module for time operations: current time, formatting, parsing, sleeping.

```py
@import "time" as t
```

| Function | Description |
|---------|----------|
| `t.now()` | Unix timestamp of current moment |
| `t.format(timestamp, fmt)` | Formats timestamp using pattern |
| `t.parse(string, fmt)` | Parses string to Unix timestamp |
| `t.sleep(seconds)` | Pauses execution for seconds |
| `t.timezone()` | Timezone offset in hours |

**Formatting codes** use Python `strftime` codes:

| Code | Description | Example |
|------|----------|--------|
| `%Y` | Year (4 digits) | `2026` |
| `%m` | Month | `04` |
| `%d` | Day | `02` |
| `%H` | Hour (24h) | `21` |
| `%M` | Minutes | `45` |
| `%S` | Seconds | `00` |

```py
@import "time" as t

var ts = t.now()
print(t.format(ts, "%Y-%m-%d %H:%M:%S"))

var ts2 = t.parse("2026-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
print(ts2)

print(t.timezone())
t.sleep(1)
```

---

## math

Module for mathematical operations. Includes constants and functions.

```py
@import "math" as m
```

### Constants

| Constant | Value |
|-----------|----------|
| `math.pi` | 3.141592653589793 |
| `math.e` | 2.718281828459045 |
| `math.inf` | Infinity |

### Functions

| Function | Description |
|---------|----------|
| `m.abs(n)` | Absolute value |
| `m.round(n)` | Round to nearest integer |
| `m.floor(n)` | Round down |
| `m.ceil(n)` | Round up |
| `m.sqrt(n)` | Square root |
| `m.log(n, null)` | Natural logarithm |
| `m.log(n, base)` | Logarithm with custom base |
| `m.exp(n)` | Exponential (`e^n`) |
| `m.min(lst)` | Minimum from list of numbers |
| `m.max(lst)` | Maximum from list of numbers |
| `m.random()` | Random float in `[0.0, 1.0]` |
| `m.randint(a, b)` | Random integer in `[a, b]` |
| `m.randfloat(a, b, digits)` | Random float with precision |
| `m.choice(lst)` | Random item from list |

```py
@import "math" as m

print(m.pi)
print(m.sqrt(2))
print(m.log(m.e, null))
print(m.log(100, 10))
print(m.randint(1, 6))
print(m.choice(["rock", "paper", "scissors"]))

var nums = [5, 3, 9, 1]
print(m.min(nums))
print(m.max(nums))
```
