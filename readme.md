# 🧙‍♂️ ArcaneQuest Scanner

**ArcaneQuest Scanner** is a Python-based GUI tool that scans and tokenizes a custom RPG-inspired programming language called **ArcaneQuest**.
It highlights and identifies tokens (keywords, strings, numbers, etc.) in `.aq` files using a custom lexer built with **regular expressions** and **Tkinter**.

---

## ⚔️ Features

* GUI interface built with **Tkinter**
* Tokenizes custom **ArcaneQuest language** keywords (e.g., `attack` → `print`, `quest` → `def`)
* Detects and displays:
  * Strings, numbers, operators, comments
  * Indentation (`INDENT` / `DEDENT`)
  * Mismatched tokens
* Syntax-highlighted output in a scrollable text box
* Load `.aq` files directly into the app

---

## Installation

1. Make sure you have **Python 3.8+** installed.
2. Clone or download this repository.
3. Install any missing dependencies (Tkinter is included with most Python distributions):

   ```bash
   pip install tk
   ```
4. Run the program:

   ```bash
   python arcanequest_scanner.py
   ```

---

## How It Works

* **`TOKENS`**: Defines all custom keywords and their Python equivalents.
* **Regex-based tokenizer**: Breaks code into components like identifiers, numbers, operators, etc.
* **Indentation tracking**: Handles Python-like blocks using `INDENT` and `DEDENT`.
* **GUI (ArcaneQuestGUI)**:

  * Left panel: Enter or open `.aq` code.
  * Right panel: Displays tokenized output with color highlighting.

---

## File Types

* `.aq` → ArcaneQuest source file

---