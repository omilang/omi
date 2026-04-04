<p align="center">
  <img src="logo.png" alt="OmiLang Logo" width="300">
</p>

<h1 align="center">Omi Programming Language</h1>

<p align="center">
  An interpreted programming language built with Python
</p>

<p align="center">
  Fork of <a href="https://github.com/keenigithub/glowlang">GlowLang</a>
</p>
<p align="center">
  <a href="https://github.com/OmiLang/docs">Documentation</a> ·
  <a href="https://github.com/OmiLang/Omi/discussions">Discussions</a> ·
  <a href="https://github.com/OmiLang/VSCode-Extension">VS Code Extension</a>
</p>

---

## Quick Start

> Requires [Python](https://www.python.org/downloads/) >= 3.11

```bash
git clone https://github.com/OmiLang/Omi.git
cd Omi
python shell.py
```

Run a file:

```
OmiShell >>> run example.omi
```

or

```
python shell.py run example.omi
```

## Example

<!-- js highlights OmiLang syntax better than plain text -->

```js
func<int> factorial(n<int>):
  if n <= 1: return 1
  return n * factorial(n - 1)
end

// Factorial from 1 to 6
for i = 1 to 6:
  print(factorial(i))
end
```

```js
@import "omi/system" as sys
@set sys.username as user

func<null> greet(name<string>):
  print("Hello, " + name + "!")
  return null
end

var<string> name = user()

greet(name)
```