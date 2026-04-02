<p align="center">
  <img src="logo.png" alt="OmiLang Logo" width="300">
</p>

<h1 align="center">OmiLang</h1>

<p align="center">
  An interpreted programming language built with Python
</p>

<p align="center">
  Omi — is a fork of <a href="https://github.com/keenigithub/glowlang">GlowLang</a>
</p>
<p align="center">
  <a href="docs/Documentation.md">Documentation</a> ·
  <a href="docs/Modules.md">Modules</a> ·
  <a href="docs/Architecture.md">Architecture</a> ·
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

## Example

<!-- js highlights OmiLang syntax better than plain text -->

```js
func factorial(n)
  if n <= 1: return 1
  return n * factorial(n - 1)
end

// Factorial from 1 to 6
for i = 1 to 6:
  print(factorial(i))
end
```

```js
@import "system" as sys

func greet(name)
  print("Hello, " + name + "!")
end

greet(sys.username())
```