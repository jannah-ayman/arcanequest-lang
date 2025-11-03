import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from scanner import scan_source, tokens_to_pretty_lines
from parser import parse

class ArcaneQuestIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("ArcaneQuest Scanner + Parser")
        self._build_ui()

    def _build_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        tk.Label(top_frame, text="ArcaneQuest Source (.aq):").pack(anchor="w")
        self.input_text = scrolledtext.ScrolledText(top_frame, height=20, wrap=tk.NONE, font=("Consolas", 11))
        self.input_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="Load .aq File", command=self.load_file).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(btn_frame, text="Scan", command=self.on_scan).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(btn_frame, text="Parse", command=self.on_parse).pack(side=tk.LEFT, padx=4, pady=4)
        tk.Button(btn_frame, text="Clear", command=self.on_clear).pack(side=tk.LEFT, padx=4, pady=4)

        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(bottom_frame, text="Scanner Output:").pack(anchor="w")
        self.scan_output = scrolledtext.ScrolledText(bottom_frame, height=10, wrap=tk.NONE, font=("Consolas", 11))
        self.scan_output.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        tk.Label(bottom_frame, text="Parser Output / Parse Tree:").pack(anchor="w")
        self.parse_output = scrolledtext.ScrolledText(bottom_frame, height=12, wrap=tk.NONE, font=("Consolas", 11))
        self.parse_output.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def load_file(self):
        path = filedialog.askopenfilename(title="Open .aq file", filetypes=[("ArcaneQuest files", "*.aq"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            self.input_text.delete("1.0", tk.END)
            self.input_text.insert("1.0", text)
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}")

    def on_scan(self):
        source = self.input_text.get("1.0", tk.END)
        tokens = scan_source(source)
        pretty = tokens_to_pretty_lines(tokens)
        self.scan_output.config(state=tk.NORMAL)
        self.scan_output.delete("1.0", tk.END)
        self.scan_output.insert("1.0", pretty)
        self.scan_output.config(state=tk.DISABLED)

    def on_parse(self):
        source = self.input_text.get("1.0", tk.END)
        tokens = scan_source(source)
        pretty = tokens_to_pretty_lines(tokens)
        self.scan_output.config(state=tk.NORMAL)
        self.scan_output.delete("1.0", tk.END)
        self.scan_output.insert("1.0", pretty)
        self.scan_output.config(state=tk.DISABLED)

        root_node, errors = parse(tokens)
        tree_str = root_node.pretty()
        if errors:
            header = f"Parsing failed: {len(errors)} error(s)\n"
            err_lines = [f"Line {lineno}: {msg}" for lineno, msg in errors]
            result = header + "\n".join(err_lines) + "\n\nPartial parse tree:\n" + tree_str
        else:
            result = "Parsing successful!\n\nParse tree:\n" + tree_str
        self.parse_output.config(state=tk.NORMAL)
        self.parse_output.delete("1.0", tk.END)
        self.parse_output.insert("1.0", result)
        self.parse_output.config(state=tk.DISABLED)

    def on_clear(self):
        self.input_text.delete("1.0", tk.END)
        self.scan_output.config(state=tk.NORMAL)
        self.scan_output.delete("1.0", tk.END)
        self.scan_output.config(state=tk.DISABLED)
        self.parse_output.config(state=tk.NORMAL)
        self.parse_output.delete("1.0", tk.END)
        self.parse_output.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = ArcaneQuestIDE(root)
    root.geometry("800x800")
    root.mainloop()