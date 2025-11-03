import re
import tkinter as tk
from tkinter import filedialog, scrolledtext

TOKENS = {
    "attack": "print",
    "scout": "input",
    "spot": "if",
    "dodge": "else",
    "counter": "elif",
    "ambush": "match",
    "quest": "def",
    "reward": "return",
    "farm": "for",
    "replay": "while",
    "guild": "class",
    "spawn": "__init__",
    "embark": "try",
    "gameOver": "except",
    "savePoint": "finally",
    "summon": "import",
    "skipEncounter": "continue",
    "escapeDungeon": "break",
    "this": "self",
    "case": "case",
    "potion": "int",
    "elixir": "float",
    "scroll": "str",
    "fate": "bool",
    "true": "True",
    "false": "False",
    "_": "_"
}

# Operators
OPERATORS = {
    "and": "and",
    "or": "or",
    "not": "not",
    "+": "plus",
    "-": "minus",
    "*": "multiply",
    "/": "divide",
    "%": "modulus",
    "**": "power",
    "==": "equal",
    "!=": "not_equal",
    "<": "less_than",
    ">": "greater_than",
    "<=": "less_equal",
    ">=": "greater_equal",
    "=": "assign",
}

# Token specification
token_specification = [
    ('comment', r'-->.*'),
    ('multiline_string', r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')'),
    ('string', r'"([^"\\]|\\.)*"|\'([^\'\\]|\\.)*\''), 
    ('number', r'-?[0-9]+(\.[0-9]+)?'),
    ('operator', r'\b(?:and|or|not)\b|<=|>=|==|!=|\*\*|[+\-*/%<>]'),
    ('assign', r'='), 
    ('lparen', r'\('), 
    ('rparen', r'\)'), 
    ('colon', r':'), 
    ('comma', r','),
    ('identifier', r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*'),
    ('skip', r'[ \t]+'),
    ('token_mismatch', r'.'),
]

# Build regex
tok_regex = '|'.join(f'(?P<{name}>{regex})' for name, regex in token_specification)
token_re = re.compile(tok_regex)

# Tokenizer
def tokenize_with_indents(code):
    lines = code.splitlines()
    tokens = []
    indent_stack = [0]

    for line in lines:
        if not line.strip():
            continue

        indent_level = len(line) - len(line.lstrip(' '))
        content = line.lstrip(' ')

        while indent_level > indent_stack[-1]:
            indent_stack.append(indent_level)
            tokens.append(("INDENT", "indent"))
        while indent_level < indent_stack[-1]:
            indent_stack.pop()
            tokens.append(("DEDENT", "dedent"))

        pos = 0
        while pos < len(content):
            match = token_re.match(content, pos)
            if not match:
                break
            kind, value = match.lastgroup, match.group()
            pos = match.end()

            if kind == 'skip':
                continue
            elif kind == 'comment':
                tokens.append((value, "comment"))
                break
            elif kind == 'identifier':
                tokens.append((value, TOKENS.get(value, "identifier")))
            elif kind == 'operator':
                tokens.append((value, OPERATORS.get(value, "operator")))
            else:
                tokens.append((value, kind))

    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(("DEDENT", "dedent"))

    return tokens


# GUI
class ArcaneQuestGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ArcaneQuest Scanner")
        self.root.geometry("900x700")
        self.root.configure(bg="#0a0a0a")

        text_cfg = dict(wrap=tk.WORD, width=100, font=("Consolas", 11), insertbackground="white")
        self.text_area = scrolledtext.ScrolledText(root, height=15, bg="#1e1e1e", fg="#d4d4d4", **text_cfg)
        self.output_area = scrolledtext.ScrolledText(root, height=25, bg="#000000", fg="#00ff00", **text_cfg)

        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        frame = tk.Frame(root, bg="#0a0a0a")
        frame.pack(pady=5)
        for text, cmd, bg, font in [
            ("Open .aq File", self.open_file, "#2d5e2d", ("Arial", 10)),
            ("Scan Code", self.run_scanner, "#0066cc", ("Arial", 10, "bold"))
        ]:
            tk.Button(frame, text=text, command=cmd, bg=bg, fg="white", font=font).pack(side=tk.LEFT, padx=5)

        self.output_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.setup_tags()

    def setup_tags(self):
        tags = [
            ("keyword", "#ffd700"),
            ("string", "#98fb98"),
            ("number", "#22bb0e"),
            ("operator", "#ff99cc"),
            ("indent", "#87cefa"),
            ("comment", "#808080"),
            ("token_mismatch", "#ff0000"),
            ("default", "#f7f7f7"),
            ("header", "#00ffff", {"font": ("Consolas", 11, "bold")}),
        ]
        for tag, color, *extra in tags:
            self.output_area.tag_config(tag, foreground=color, **(extra[0] if extra else {}))

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("ArcaneQuest Files", "*.aq")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert(tk.END, f.read())

    def run_scanner(self):
        code = self.text_area.get("1.0", tk.END)
        try:
            tokens = tokenize_with_indents(code)
            self.output_area.delete("1.0", tk.END)
            self.output_area.insert(tk.END, "ArcaneQuest Scanner Output:\n\n", "header")

            for value, meaning in tokens:
                if meaning in TOKENS.values() and meaning != "identifier":
                    tag = "keyword"
                elif meaning in OPERATORS.values():
                    tag = "operator"
                elif meaning == "dedent":
                    tag = "indent"
                elif meaning in {"string", "number", "indent", "comment", "token_mismatch"}:
                    tag = meaning
                else:
                    tag = "default"

                self.output_area.insert(tk.END, f"{value:<25} → {meaning}\n", tag)

        except Exception as e:
            self.output_area.delete("1.0", tk.END)
            self.output_area.insert(tk.END, f"ERROR: {e}", "token_mismatch")


# MAIN ENTRY
if __name__ == "__main__":
    root = tk.Tk()
    ArcaneQuestGUI(root)
    root.mainloop()