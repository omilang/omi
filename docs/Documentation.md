# OmiLang Documentation

> Complete guide to the OmiLang programming language

---

## Navigation

- [Documentation (this page)](Documentation.md) - syntax, types, functions, imports
- [Modules](Modules.md) - built-in modules (`system`, `files`, `paths`, `time`, `math`)
- [Architecture](Architecture.md) - project layout and interpreter internals

---

## Contents

- [Basics](#basics)
  - [Comments](#comments)
  - [Variables](#variables)
  - [Data Types](#data-types)
  - [Built-in Constants](#built-in-constants)
- [Operators](#operators)
  - [Arithmetic Operators](#arithmetic-operators)
  - [Comparison Operators](#comparison-operators)
  - [Logical Operators](#logical-operators)
- [Conditions](#conditions)
  - [if / elif / else](#if--elif--else)
  - [Single-line Form](#single-line-form)
- [Loops](#loops)
  - [for](#for-loop)
  - [while](#while-loop)
  - [break and continue](#break-and-continue)
- [Functions](#functions)
  - [Function Declaration](#function-declaration)
  - [Arrow Functions](#arrow-functions)
  - [return](#return)
- [Lists](#lists)
- [Strings](#strings)
- [Built-in Functions](#built-in-functions)
- [Imports](#imports)
  - [File Imports](#file-imports)
  - [Built-in Module Imports](#built-in-module-imports)
- [eval](#eval)
- [Interactive Shell](#interactive-shell)

---

## Basics

### Comments

Single-line comments start with `//`:

```js
// This is a comment
var x = 10 // This is also a comment
```

### Variables

Variables are declared with the `var` keyword:

```js
var name = "OmiLang"
var age = 1
var pi_approx = 3.14
```

Reassignment also uses `var`:

```js
var x = 10
var x = x + 5
```

### Data Types

| Type | Example | Description |
|-----|--------|----------|
| Integer | `42` | Whole numbers |
| Float | `3.14` | Floating-point numbers |
| String | `"hello"` | Text data in double quotes |
| List | `[1, 2, 3]` | Ordered collection of elements |

### Built-in Constants

| Constant | Value | Description |
|-----------|----------|----------|
| `null` | `0` | Empty value |
| `true` | `1` | Boolean true |
| `false` | `0` | Boolean false |

---

## Operators

### Arithmetic Operators

| Operator | Description | Example |
|----------|----------|--------|
| `+` | Addition | `2 + 3` -> `5` |
| `-` | Subtraction | `5 - 2` -> `3` |
| `*` | Multiplication | `3 * 4` -> `12` |
| `/` | Division | `10 / 3` -> `3.333...` |
| `^` | Exponentiation | `2 ^ 8` -> `256` |

Parentheses are supported to override precedence:

```js
var result = (2 + 3) * 4  // 20
```

### Comparison Operators

| Operator | Description |
|----------|----------|
| `==` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `>` | Greater than |
| `<=` | Less than or equal |
| `>=` | Greater than or equal |

### Logical Operators

| Operator | Description |
|----------|----------|
| `and` | Logical AND |
| `or` | Logical OR |
| `is` | True (value is not 0 / false) |
| `isnt` | False (value is 0 / false) |

```js
if x > 0 and x < 100:
  print("x is in range 0..100")
end

var exists = true
if is exists:
  print("exists")
end

if isnt exists:
  print("does not exist")
end
```

---

## Conditions

### if / elif / else

Conditional blocks use `:` after the condition and are closed with `end`:

```js
var score = 85

if score >= 90:
  print("Excellent")
elif score >= 70:
  print("Good")
else
  print("Can be better")
end
```

> **Important:** `if` and `elif` require `:`, while `else` does not.

### Single-line Form

For simple cases, you can use one line:

```js
if x > 0: print("positive")
```

---

## Loops

### for loop

The `for` loop iterates from a start value to an end value:

```js
for i = 0 to 5:
  print(i)
end
```

Output: `0`, `1`, `2`, `3`, `4`

With custom step:

```js
for i = 0 to 10 step 2:
  print(i)
end
```

Output: `0`, `2`, `4`, `6`, `8`

### while loop

```js
var i = 1
while i <= 5:
  print(i)
  var i = i + 1
end
```

### break and continue

- `break` stops the loop
- `continue` jumps to the next iteration

```js
for i = 0 to 10:
  if i == 5: break
  if i == 3: continue
  print(i)
end
```

Output: `0`, `1`, `2`, `4`

---

## Functions

### Function Declaration

Functions are declared with `func` and closed with `end`:

```js
func greet(name)
  print("Hello, " + name + "!")
end

greet("World")
```

### Arrow Functions

Use `->` for compact functions:

```js
func add(a, b) -> a + b
print(add(2, 3))  // 5
```

Arrow functions return the expression result automatically. `end` is not required.

### return

Use `return` in regular functions to return a value:

```js
func factorial(n)
  var result = 1
  while n > 1:
    var result = result * n
    var n = n - 1
  end
  return result
end

print(factorial(5))  // 120
```

If `return` is omitted, the function returns `null`.

---

## Lists

Lists are created with square brackets:

```js
var fruits = ["apple", "banana", "orange"]
var numbers = [1, 2, 3, 4, 5]
var mixed = [1, "two", 3]
var empty = []
```

List operations:

```js
var list = [1, 2, 3]

append(list, 4)         // [1, 2, 3, 4]
pop(list, 0)            // removes item at index 0
var size = len(list)    // list length

var a = [1, 2]
var b = [3, 4]
extend(a, b)            // a = [1, 2, 3, 4]
```

List concatenation with `+`:

```js
var result = [1, 2] + [3, 4]  // [1, 2, 3, 4]
```

List repetition by number:

```js
var result = [0] * 5  // [0, 0, 0, 0, 0]
```

---

## Strings

Strings use double quotes:

```js
var greeting = "Hello, World!"
```

Concatenation:

```js
var full = "Hello, " + "World!"
```

Repetition:

```js
var line = "-" * 20  // "--------------------"
```

Escape sequences:

| Sequence | Result |
|-------------------|-----------|
| `\n` | New line |
| `\t` | Tab |
| `\\` | Backslash |
| `\"` | Double quote |

---

## Built-in Functions

### Input / Output

| Function | Description |
|---------|----------|
| `print(value)` | Prints a value to the console |
| `input()` | Reads a string from stdin |
| `input_int()` | Reads an integer from stdin |

### Type Checks

| Function | Description |
|---------|----------|
| `is_num(value)` | Whether argument is a number |
| `is_str(value)` | Whether argument is a string |
| `is_list(value)` | Whether argument is a list |
| `is_func(value)` | Whether argument is a function |

They return `1` (true) or `0` (false).

### List Utilities

| Function | Description |
|---------|----------|
| `append(list, value)` | Appends an element to a list |
| `pop(list, index)` | Removes and returns element by index |
| `extend(listA, listB)` | Appends all elements from listB to listA |
| `len(list)` | Returns list length |

### Other

| Function | Description |
|---------|----------|
| `clear()` / `cls()` | Clears the console |
| `eval(code)` | Executes a string as OmiLang code |

---

## Imports

### File Imports

To import code from another file, use the `@import` directive:

```py
@import "utils" as u
u.my_function()
```

- Module path is provided without extension; the interpreter resolves `.omi`
- `as` and alias are required
- Path is resolved relative to the current file
- All module values are accessed via dot notation

**Example:**

File `math_utils.omi`:
```py
func square(x) -> x ^ 2
func cube(x) -> x ^ 3
var version = "1.0"
```

File `main.omi`:
```py
@import "math_utils" as math
print(math.square(5))   // 25
print(math.cube(3))     // 27
print(math.version)     // 1.0
```

### Built-in Module Imports

Built-in modules are imported the same way. If the name matches a built-in module, it is loaded without file lookup:

```py
@import "system" as sys
print(sys.platform())
```

Built-in modules list: see [Modules](Modules.md).

Available built-in modules:

| Module | Description |
|--------|----------|
| `system` | OS interaction, commands, environment variables |
| `files` | File system operations |
| `paths` | Path helpers |
| `time` | Time, formatting, delays |
| `math` | Math functions and constants |

---

## eval

The `eval` function executes a string as OmiLang code:

```py
var code = "print(2 + 2)"
eval(code)  // 4

var result = eval("10 * 5")
print(result)  // 50
```

---

## Interactive Shell

Start shell:

```bash
python shell.py
```

Start with debug output (shows returned values):

```bash
python shell.py --debug
```

Run file from shell:

```
OmiShell >>> run main.omi
```

Usage examples:

```
OmiShell >>> var x = 10
OmiShell >>> print(x * 2)
20
OmiShell >>> func double(n) -> n * 2
OmiShell >>> print(double(7))
14
```
