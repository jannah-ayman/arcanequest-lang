import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from scanner import scan_source, tokens_to_pretty_lines
from parser import parse


class LineNumberedText(tk.Frame):
    """Text widget with line numbers on the left side."""
    
    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, bg="#1a1a1a")
        
        # Extract text widget specific kwargs
        text_kwargs = {}
        for key in ['height', 'wrap', 'font', 'bg', 'fg', 'insertbackground', 
                    'selectbackground', 'relief', 'borderwidth']:
            if key in kwargs:
                text_kwargs[key] = kwargs.pop(key)
        
        # Create line number canvas (thinner width)
        self.line_numbers = tk.Canvas(
            self, 
            width=40,  # Reduced from 50
            bg="#181818", 
            highlightthickness=0,
            bd=0
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Create text widget with scrollbar
        self.text = tk.Text(self, **text_kwargs)
        self.scrollbar = tk.Scrollbar(self, command=self.text.yview)
        
        self.text.configure(yscrollcommand=self._on_scroll)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind events to update line numbers
        self.text.bind('<KeyRelease>', self._on_change)
        self.text.bind('<MouseWheel>', self._on_change)
        self.text.bind('<Button-1>', self._on_change)
        self.text.bind('<ButtonRelease-1>', self._on_change)
        
        # Schedule periodic updates
        self._schedule_update()
    
    def _schedule_update(self):
        """Schedule periodic line number updates."""
        self._update_line_numbers()
        self.after(100, self._schedule_update)
    
    def _on_scroll(self, *args):
        """Handle scrollbar updates."""
        self.scrollbar.set(*args)
        self._update_line_numbers()
    
    def _on_change(self, event=None):
        """Handle any change event."""
        self._update_line_numbers()
    
    def _update_line_numbers(self, event=None):
        """Update the line numbers displayed."""
        self.line_numbers.delete('all')
        
        # Get the line number at the top of the visible area
        first_visible = self.text.index('@0,0')
        last_visible = self.text.index(f'@0,{self.text.winfo_height()}')
        
        first_line = int(first_visible.split('.')[0])
        last_line = int(last_visible.split('.')[0])
        
        # Get font info
        font_family = 'Consolas'
        font_size = 9
        
        # Draw line numbers
        for line_num in range(first_line, last_line + 2):
            dline_info = self.text.dlineinfo(f'{line_num}.0')
            if dline_info:
                y = dline_info[1] + dline_info[3] // 2  # Center vertically
                self.line_numbers.create_text(
                    35,  # Adjusted for thinner canvas
                    y, 
                    anchor='e',
                    text=str(line_num),
                    fill='#4a4a4a',  # Slightly lighter gray
                    font=(font_family, font_size)
                )
    
    def get(self, *args, **kwargs):
        """Proxy get method to text widget."""
        return self.text.get(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Proxy delete method to text widget."""
        self.text.delete(*args, **kwargs)
    
    def insert(self, *args, **kwargs):
        """Proxy insert method to text widget."""
        self.text.insert(*args, **kwargs)


class ArcaneQuestIDE:
    
    def __init__(self, root):
        self.root = root
        self.root.title("ArcaneQuest IDE")
        self.root.configure(bg="#0d1117")  # Modern dark background
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Modern button styling
        style.configure("TButton",
                        font=("Segoe UI", 9, "bold"),
                        foreground="white",
                        padding=8,
                        borderwidth=0)

        # Label styling
        style.configure("TLabel",
                        background="#0d1117",
                        foreground="#c9d1d9",
                        font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        # Main container with modern padding
        main_frame = tk.Frame(self.root, bg="#0d1117")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # Left panel (editor)
        left_frame = tk.Frame(main_frame, bg="#0d1117")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        # Modern header with icon
        header_frame = tk.Frame(left_frame, bg="#0d1117")
        header_frame.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(
            header_frame, 
            text="📝 Editor", 
            bg="#0d1117",
            fg="#58a6ff",
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)

        # Source code editor with modern styling
        editor_container = tk.Frame(left_frame, bg="#161b22", relief=tk.FLAT)
        editor_container.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        
        self.input_text = LineNumberedText(
            editor_container,
            height=25,
            wrap=tk.NONE,
            font=("Consolas", 10),
            bg="#0d1117",
            fg="#e6edf3",
            insertbackground="#58a6ff",
            selectbackground="#1f6feb",
            relief="flat",
            borderwidth=8
        )
        self.input_text.pack(fill=tk.BOTH, expand=True)

        # Modern button bar
        btn_frame = tk.Frame(left_frame, bg="#0d1117")
        btn_frame.pack(fill=tk.X)

        # Modern button colors
        buttons = [
            ("📂 Load", self.load_file, "#238636", "#2ea043"),
            ("🔍 Scan", self.on_scan, "#1f6feb", "#388bfd"),
            ("🌳 Parse", self.on_parse, "#8957e5", "#a371f7"),
            ("🗑️  Clear", self.on_clear, "#da3633", "#f85149"),
        ]

        for text, cmd, bg, hover_bg in buttons:
            btn = tk.Button(
                btn_frame,
                text=text,
                command=cmd,
                font=("Segoe UI", 9, "bold"),
                bg=bg,
                fg="white",
                activebackground=hover_bg,
                activeforeground="white",
                relief="flat",
                cursor="hand2",
                padx=16,
                pady=8,
                borderwidth=0
            )
            btn.pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
            
            # Hover effects
            btn.bind("<Enter>", lambda e, b=btn, c=hover_bg: b.config(bg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=bg: b.config(bg=c))

        # Right panel (output)
        right_frame = tk.Frame(main_frame, bg="#0d1117")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Scanner output section
        scan_header = tk.Frame(right_frame, bg="#0d1117")
        scan_header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            scan_header, 
            text="🔍 Tokens", 
            fg="#58a6ff",
            bg="#0d1117", 
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)
        
        scan_container = tk.Frame(right_frame, bg="#161b22")
        scan_container.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        
        self.scan_output = scrolledtext.ScrolledText(
            scan_container, 
            height=10, 
            wrap=tk.NONE, 
            font=("Consolas", 9),
            bg="#0d1117", 
            fg="#c9d1d9", 
            insertbackground="#58a6ff",
            selectbackground="#1f6feb", 
            relief="flat", 
            borderwidth=8,
            state=tk.DISABLED
        )
        self.scan_output.pack(fill=tk.BOTH, expand=True)

        # Parser output section
        parse_header = tk.Frame(right_frame, bg="#0d1117")
        parse_header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            parse_header, 
            text="🌳 Parse Tree", 
            fg="#58a6ff",
            bg="#0d1117", 
            font=("Segoe UI", 11, "bold")
        ).pack(side=tk.LEFT)
        
        parse_container = tk.Frame(right_frame, bg="#161b22")
        parse_container.pack(fill=tk.BOTH, expand=True)
        
        self.parse_output = scrolledtext.ScrolledText(
            parse_container, 
            height=12, 
            wrap=tk.NONE, 
            font=("Consolas", 9),
            bg="#0d1117", 
            fg="#c9d1d9", 
            insertbackground="#58a6ff",
            selectbackground="#1f6feb", 
            relief="flat", 
            borderwidth=8,
            state=tk.DISABLED
        )
        self.parse_output.pack(fill=tk.BOTH, expand=True)

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
            error_msg = f"❌ Scanner Error:\n{str(e)}"
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
                # Separate parse errors from semantic errors
                parse_errors = []
                semantic_errors = []
                
                for error in errors:
                    if isinstance(error, tuple) and len(error) == 2:
                        lineno, msg = error
                        if "Semantic" in msg or "Type mismatch" in msg or \
                           "Undeclared" in msg or "must be boolean" in msg or \
                           "Cannot determine type" in msg:
                            semantic_errors.append((lineno, msg))
                        else:
                            parse_errors.append((lineno, msg))
                    else:
                        parse_errors.append(error)
                
                # Build error message
                error_header = f"⚠️  Found {len(errors)} error(s)\n"
                
                if parse_errors:
                    error_header += f"   • {len(parse_errors)} Parse error(s)\n"
                if semantic_errors:
                    error_header += f"   • {len(semantic_errors)} Semantic error(s)\n"
                
                error_lines = []
                
                if parse_errors:
                    error_lines.append("\n━━━ PARSE ERRORS ━━━")
                    for lineno, msg in parse_errors:
                        error_lines.append(f"Line {lineno}: {msg}")
                
                if semantic_errors:
                    error_lines.append("\n━━━ SEMANTIC ERRORS ━━━")
                    for lineno, msg in semantic_errors:
                        error_lines.append(f"Line {lineno}: {msg}")
                
                separator = "─" * 60
                result = (f"{error_header}"
                         f"{chr(10).join(error_lines)}\n\n"
                         f"{separator}\n"
                         f"Parse Tree:\n"
                         f"{separator}\n"
                         f"{tree_str}")
            else:
                result = f"✅ Success!\n\nParse tree with type annotations:\n\n{tree_str}"
            
            self._display_output(self.parse_output, result)
            
        except Exception as e:
            import traceback
            error_msg = f"❌ Unexpected Error:\n{str(e)}\n\n{traceback.format_exc()}"
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
    root.geometry("1300x600")
    root.minsize(1100, 600)
    root.mainloop()


if __name__ == "__main__":
    main()