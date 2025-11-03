import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from scanner import scan_source, tokens_to_pretty_lines
from parser import parse


class ArcaneQuestIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("⚔️ ArcaneQuest IDE — Scanner + Parser")
        self.root.configure(bg="#1a1a1a")  # dark gray background
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Default button style
        style.configure("TButton",
                        font=("Segoe UI", 9, "bold"),
                        foreground="white",
                        padding=6)
        style.map("TButton",
                  relief=[("pressed", "groove")])

        style.configure("TLabel",
                        background="#1a1a1a",
                        foreground="#e0e0e0",
                        font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        # ---------- MAIN SPLIT FRAME ----------
        main_frame = tk.Frame(self.root, bg="#1a1a1a")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ---------- LEFT PANEL (Source) ----------
        left_frame = tk.Frame(main_frame, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Section title — blue
        tk.Label(left_frame, text="🧾 Source (.aq):", bg="#1a1a1a",
                 fg="#4FC3F7", font=("Consolas", 10, "bold")).pack(anchor="w")

        self.input_text = scrolledtext.ScrolledText(
            left_frame, height=25, wrap=tk.NONE, font=("Consolas", 10),
            bg="#202020", fg="#f5f5f5", insertbackground="white",
            selectbackground="#404040", relief="flat", borderwidth=6
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        # Buttons — match title color
        btn_frame = tk.Frame(left_frame, bg="#1a1a1a")
        btn_frame.pack(fill=tk.X)

        button_colors = {
            "Load": "#4FC3F7",   # blue
            "Scan": "#81C784",   # green
            "Parse": "#BA68C8",  # purple
            "Clear": "#E57373",  # red (neutral action)
        }

        for text, cmd in [
            ("Load", self.load_file),
            ("Scan", self.on_scan),
            ("Parse", self.on_parse),
            ("Clear", self.on_clear),
        ]:
            color = button_colors[text]
            btn = tk.Button(
                btn_frame,
                text=text,
                command=cmd,
                font=("Segoe UI", 9, "bold"),
                bg=color,
                fg="black",
                activebackground="#ffffff",
                activeforeground="black",
                relief="flat",
                padx=10,
                pady=4
            )
            btn.pack(side=tk.LEFT, padx=4, pady=4, fill=tk.X, expand=True)

        # ---------- RIGHT PANEL (Scanner + Parser outputs) ----------
        right_frame = tk.Frame(main_frame, bg="#1a1a1a")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Scanner output — green title
        tk.Label(right_frame, text="🔎 Scanner Output:", fg="#81C784",
                 bg="#1a1a1a", font=("Consolas", 10, "bold")).pack(anchor="w")
        self.scan_output = scrolledtext.ScrolledText(
            right_frame, height=10, wrap=tk.NONE, font=("Consolas", 10),
            bg="#202020", fg="#dcdcdc", insertbackground="white",
            selectbackground="#404040", relief="flat", borderwidth=6
        )
        self.scan_output.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        # Parser output — purple title
        tk.Label(right_frame, text="🌳 Parser / Parse Tree:", fg="#BA68C8",
                 bg="#1a1a1a", font=("Consolas", 10, "bold")).pack(anchor="w")
        self.parse_output = scrolledtext.ScrolledText(
            right_frame, height=12, wrap=tk.NONE, font=("Consolas", 10),
            bg="#202020", fg="#dcdcdc", insertbackground="white",
            selectbackground="#404040", relief="flat", borderwidth=6
        )
        self.parse_output.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

    # ---------- BUTTON CALLBACKS ----------
    def load_file(self):
        path = filedialog.askopenfilename(
            title="Open ArcaneQuest File",
            filetypes=[("ArcaneQuest files", "*.aq"), ("All files", "*.*")]
        )
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
        self._display_output(self.scan_output, pretty)

    def on_parse(self):
        source = self.input_text.get("1.0", tk.END)
        tokens = scan_source(source)
        pretty = tokens_to_pretty_lines(tokens)
        self._display_output(self.scan_output, pretty)

        root_node, errors = parse(tokens)
        tree_str = root_node.pretty()
        if errors:
            header = f"⚠️ Parsing failed: {len(errors)} error(s)\n"
            err_lines = [f"Line {lineno}: {msg}" for lineno, msg in errors]
            result = header + "\n".join(err_lines) + "\n\n" + "="*60 + "\nPartial parse tree:\n" + "="*60 + "\n" + tree_str
        else:
            result = "✅ Parsing successful!\n\nParse tree:\n" + tree_str
        self._display_output(self.parse_output, result)

    def on_clear(self):
        self.input_text.delete("1.0", tk.END)
        self._display_output(self.scan_output, "")
        self._display_output(self.parse_output, "")

    # ---------- HELPER ----------
    def _display_output(self, widget, text):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = ArcaneQuestIDE(root)
    root.geometry("1350x640")  # balanced width
    root.minsize(1000, 540)
    root.mainloop()