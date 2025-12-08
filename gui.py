import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from scanner import scan_source, tokens_to_pretty_lines
from parser import parse


class ArcaneQuestIDE:
    
    def __init__(self, root):
        self.root = root
        self.root.title("ArcaneQuest IDE — Scanner + Parser")
        self.root.configure(bg="#1a1a1a")  # Dark theme background
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Button styling
        style.configure("TButton",
                        font=("Segoe UI", 9, "bold"),
                        foreground="white",
                        padding=6)
        style.map("TButton",
                  relief=[("pressed", "groove")])

        # Label styling
        style.configure("TLabel",
                        background="#1a1a1a",
                        foreground="#e0e0e0",
                        font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        main_frame = tk.Frame(self.root, bg="#1a1a1a")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        left_frame = tk.Frame(main_frame, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # Section title
        tk.Label(left_frame, text="📂 Source (.aq):", bg="#1a1a1a",
                 fg="#4FC3F7", font=("Consolas", 10, "bold")).pack(anchor="w")

        # Source code text editor
        self.input_text = scrolledtext.ScrolledText(
            left_frame, height=25, wrap=tk.NONE, font=("Consolas", 10),
            bg="#202020", fg="#f5f5f5", insertbackground="white",
            selectbackground="#404040", relief="flat", borderwidth=6
        )
        self.input_text.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        # Action buttons
        btn_frame = tk.Frame(left_frame, bg="#1a1a1a")
        btn_frame.pack(fill=tk.X)

        # Button configuration: (text, command, color)
        buttons = [
            ("Load", self.load_file, "#4FC3F7"),   # Blue - file operation
            ("Scan", self.on_scan, "#81C784"),     # Green - tokenization
            ("Parse", self.on_parse, "#BA68C8"),   # Purple - parsing
            ("Clear", self.on_clear, "#E57373"),   # Red - reset
        ]

        for text, cmd, color in buttons:
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

        right_frame = tk.Frame(main_frame, bg="#1a1a1a")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Scanner output section
        tk.Label(right_frame, text="🔍 Scanner Output:", fg="#81C784",
                 bg="#1a1a1a", font=("Consolas", 10, "bold")).pack(anchor="w")
        self.scan_output = scrolledtext.ScrolledText(
            right_frame, height=10, wrap=tk.NONE, font=("Consolas", 10),
            bg="#202020", fg="#dcdcdc", insertbackground="white",
            selectbackground="#404040", relief="flat", borderwidth=6
        )
        self.scan_output.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        # Parser output section
        tk.Label(right_frame, text="🌳 Parser / Parse Tree:", fg="#BA68C8",
                 bg="#1a1a1a", font=("Consolas", 10, "bold")).pack(anchor="w")
        self.parse_output = scrolledtext.ScrolledText(
            right_frame, height=12, wrap=tk.NONE, font=("Consolas", 10),
            bg="#202020", fg="#dcdcdc", insertbackground="white",
            selectbackground="#404040", relief="flat", borderwidth=6
        )
        self.parse_output.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

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
        
        try:
            tokens = scan_source(source)
            pretty = tokens_to_pretty_lines(tokens)
            self._display_output(self.scan_output, pretty)
        except Exception as e:
            error_msg = f"Scanner Error:\n{str(e)}"
            self._display_output(self.scan_output, error_msg)

    def on_parse(self):
        source = self.input_text.get("1.0", tk.END)
        
        try:
            # Run scanner
            tokens = scan_source(source)
            pretty = tokens_to_pretty_lines(tokens)
            self._display_output(self.scan_output, pretty)
            
            # Run parser
            root_node, errors = parse(tokens)
            tree_str = root_node.pretty()
            
            if errors:
                # Display errors with partial parse tree
                header = f"‼️Parsing failed: {len(errors)} error(s)\n"
                err_lines = [f"Line {lineno}: {msg}" for lineno, msg in errors]
                separator = "=" * 60
                result = (f"{header}\n"
                         f"{chr(10).join(err_lines)}\n\n"
                         f"{separator}\n"
                         f"Partial parse tree:\n"
                         f"{separator}\n"
                         f"{tree_str}")
            else:
                # Success - display parse tree
                result = f"✔️Parsing successful!\n\nParse tree:\n{tree_str}"
            
            self._display_output(self.parse_output, result)
            
        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected Error:\n{str(e)}"
            self._display_output(self.parse_output, error_msg)

    def on_clear(self):
        self.input_text.delete("1.0", tk.END)
        self._display_output(self.scan_output, "")
        self._display_output(self.parse_output, "")

    def _display_output(self, widget, text):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = ArcaneQuestIDE(root)
    root.geometry("1350x640")  # Default window size
    root.minsize(1000, 540)    # Minimum window size
    root.mainloop()

if __name__ == "__main__":
    main()