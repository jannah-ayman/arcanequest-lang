# ⚔️ ArcaneQuest Programming Language

ArcaneQuest is a fantasy-themed programming language with a custom scanner, parser, and IDE. It features gaming-inspired keywords and syntax while maintaining familiar programming constructs.

## Features

- **Fantasy-themed syntax** with keywords like `quest`, `summon`, `attack`, `scout`
- **Custom scanner and parser** implementation
- **Interactive IDE** with syntax validation
- **Indentation-based scoping** (Python-style)
- **Support for functions, classes, loops, conditionals, and exception handling**

## Installation

### Prerequisites
- Python 3.7 or higher
- tkinter (usually comes with Python)

### Setup
1. Clone or download this repository
2. Ensure all three files are in the same directory:
   - `scanner.py` - Lexical analyzer
   - `parser.py` - Syntax parser
   - `gui.py` - IDE interface

3. Run the IDE:
```bash
python gui.py
```

## 🎯 Language Syntax

### Keywords & Their Meanings

| ArcaneQuest Keyword | Traditional Equivalent | Purpose |
|---------------------|------------------------|---------|
| `summon` | `import` | Import modules |
| `quest` | `def` | Define function |
| `reward` | `return` | Return value |
| `attack` | `print` | Output/print |
| `scout` | `input` | Get user input |
| `spot` | `if` | Conditional if |
| `counter` | `elif` | Else-if |
| `dodge` | `else` | Else clause |
| `replay` | `while` | While loop |
| `farm` | `for` | For loop |
| `guild` | `class` | Define class |
| `case` | `case` | Match case |
| `embark` | `try` | Try block |
| `gameOver` | `except` | Exception handler |
| `savePoint` | `finally` | Finally block |
| `skipEncounter` | `continue` | Continue loop |
| `escapeDungeon` | `break` | Break loop |

### Data Types
- `potion` - int type
- `elixir` - float type
- `fate` - boolean type
- `scroll` - string type

### Operators
- Arithmetic: `+`, `-`, `*`, `/`
- Comparison: `<`, `>`, `<=`, `>=`, `==`, `!=`
- Logical: `and`, `or`, `not`
- Assignment: `=`, `+=`, `-=`, `*=`, `/=`

### Comments
Use `-->` for single-line comments:
```arcanequest
--> This is a comment
```

## 📝 Code Examples

### Hello World
```arcanequest
attack("Hello, World!")
```

### Import Modules
```arcanequest
summon random, sys
```

### Function Definition
```arcanequest
quest greet(name):
    attack("Hello,", name)
    reward "Welcome!"
```

### Variables and Input
```arcanequest
name = scout("Enter your name: ")
attack("Hello,", name)
```

### Conditional Statements
```arcanequest
spot (health > 50):
    attack("You are healthy!")
counter (health > 20):
    attack("You are wounded!")
dodge:
    attack("Critical condition!")
```

### Loops
```arcanequest
--> While loop
replay (count < 10):
    attack(count)
    count += 1

--> For loop
farm item in inventory:
    attack("Found:", item)
```

### Pattern Matching
```arcanequest
ambush player_action:
    case "attack":
        attack("You attack!")
    case "defend":
        attack("You defend!")
    case _:
        attack("Unknown action")
```

### Classes
```arcanequest
guild Hero:
    quest __init__(name):
        attack("Hero created:", name)
```

### Exception Handling
```arcanequest
embark:
    risky_operation()
gameOver ValueError:
    attack("Invalid value!")
gameOver:
    attack("Unknown error!")
savePoint:
    attack("Cleanup complete")
```

### Function Calls
```arcanequest
scroll("message")
sys.exit(0)
player.take_damage(10)
```

## 🔧 IDE Usage

### Interface Components

1. **Source Editor** (Left Panel)
   - Write your ArcaneQuest code here
   - Supports `.aq` file extensions

2. **Scanner Output** (Right Top)
   - Shows tokenized output
   - Displays token types and line numbers

3. **Parser Output** (Right Bottom)
   - Shows the Abstract Syntax Tree (AST)
   - Displays parsing errors if any

### Buttons

- **Load** - Open an `.aq` file
- **Scan** - Tokenize the source code
- **Parse** - Parse and validate syntax
- **Clear** - Clear all panels

## ⚠️ Syntax Rules

### Indentation
- **Consistent indentation is required**
- First indent sets the standard (e.g., 4 spaces)
- All subsequent indents must match exactly

## 🐛 Error Messages

The parser provides detailed error messages:

- **Line numbers** for easy debugging
- **Clear descriptions** of what went wrong
- **Partial parse tree** even when errors occur

Example error output:
```
⚠️ Parsing failed: 2 error(s)
Line 3: Expected ',' after module name
Line 5: Invalid statement: bare identifier 'test' cannot stand alone
```

## 📂 File Structure

```
arcanequest/
│
├── scanner.py       # Lexical analyzer
├── parser.py        # Syntax parser
├── gui.py           # IDE application
└── README.md        # This file
```

## 🔮 Advanced Features

### Operator Precedence
```
1. or               (lowest)
2. and
3. not
4. ==, !=, <, >, <=, >=
5. +, -
6. *, /            (highest)
```

### Attribute Access
```arcanequest
player.health
sys.exit
math.sqrt(16)
```

### Nested Structures
```arcanequest
quest complex_function(x, y):
    spot (x > 0):
        replay (y < 10):
            attack(x, y)
            y += 1
    reward x + y
```

## 👥 Authors & Contributors

- Jannah Ayman (@jannah-ayman)
- Rawan Sotohy (@Rawan-Sotohy)
- Nancy Saad (@nancyabdelbaryy)

## 📜 License

This project is for educational purposes.

---

**Happy Questing! ⚔️🛡️✨**