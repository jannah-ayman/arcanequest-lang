import customtkinter as ctk
from tkinter import filedialog, messagebox
from scanner import scan_source, tokens_to_pretty_lines
from parser import parse


class LineNumberedText(ctk.CTkFrame):
    """Text widget with line numbers on the left side."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent")
        
        # Extract custom parameters
        text_height = kwargs.pop('height', 25)
        text_font = kwargs.pop('font', ("Consolas", 14))
        
        # Create line number display
        self.line_numbers = ctk.CTkTextbox(
            self,
            width=50,
            font=("Consolas", 14),
            fg_color="#1a1a1a",
            text_color="#4a4a4a",
            activate_scrollbars=False,
            state="disabled"
        )
        self.line_numbers.pack(side="left", fill="y", padx=(0, 2))
        
        # Create main text widget
        self.text = ctk.CTkTextbox(
            self,
            height=text_height,
            font=text_font,
            fg_color="#0d1117",
            text_color="#e6edf3",
            border_width=0,
            corner_radius=8,
            wrap="none"
        )
        self.text.pack(side="left", fill="both", expand=True)
        
        # Bind events to update line numbers
        self.text._textbox.bind('<KeyRelease>', self._on_change)
        self.text._textbox.bind('<MouseWheel>', self._on_change)
        self.text._textbox.bind('<Button-1>', self._on_change)
        self.text._textbox.bind('<<Modified>>', self._on_change)
        
        # Initial line numbers
        self._update_line_numbers()
    
    def _on_change(self, event=None):
        """Handle any change event."""
        self.after(10, self._update_line_numbers)
    
    def _update_line_numbers(self):
        """Update the line numbers displayed."""
        # Get content from main text widget
        content = self.text.get("1.0", "end-1c")
        line_count = content.count('\n') + 1
        
        # Generate line numbers
        line_numbers = "\n".join(str(i) for i in range(1, line_count + 1))
        
        # Update line number widget
        self.line_numbers.configure(state="normal")
        current_lines = self.line_numbers.get("1.0", "end-1c")
        if current_lines != line_numbers:
            self.line_numbers.delete("1.0", "end")
            self.line_numbers.insert("1.0", line_numbers)
        self.line_numbers.configure(state="disabled")
        
        # Sync scrolling
        first_visible = self.text._textbox.yview()[0]
        self.line_numbers._textbox.yview_moveto(first_visible)
    
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
        self.root.title("⚔️ ArcaneQuest IDE - Fantasy RPG Language")
        
        # Set theme and color
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self._build_ui()

    def _build_ui(self):
        # Configure grid weights for responsive layout
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Left panel (editor)
        left_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        
        # Editor header
        editor_header = ctk.CTkLabel(
            left_frame,
            text="📝 Code Editor",
            font=("Segoe UI", 18, "bold"),
            text_color="#58a6ff",
            anchor="w"
        )
        editor_header.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Source code editor
        self.input_text = LineNumberedText(
            left_frame,
            height=400,
            font=("Consolas", 14)
        )
        self.input_text.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        # Button bar
        btn_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Buttons with fantasy RPG theme
        self.load_btn = ctk.CTkButton(
            btn_frame,
            text="📂 Load Quest",
            command=self.load_file,
            font=("Segoe UI", 13, "bold"),
            fg_color="#238636",
            hover_color="#2ea043",
            corner_radius=8,
            height=40
        )
        self.load_btn.grid(row=0, column=0, padx=3, sticky="ew")
        
        self.scan_btn = ctk.CTkButton(
            btn_frame,
            text="🔍 Scan Runes",
            command=self.on_scan,
            font=("Segoe UI", 13, "bold"),
            fg_color="#1f6feb",
            hover_color="#388bfd",
            corner_radius=8,
            height=40
        )
        self.scan_btn.grid(row=0, column=1, padx=3, sticky="ew")
        
        self.parse_btn = ctk.CTkButton(
            btn_frame,
            text="🌳 Parse Spell",
            command=self.on_parse,
            font=("Segoe UI", 13, "bold"),
            fg_color="#8957e5",
            hover_color="#a371f7",
            corner_radius=8,
            height=40
        )
        self.parse_btn.grid(row=0, column=2, padx=3, sticky="ew")
        
        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="🗑️ Clear Scroll",
            command=self.on_clear,
            font=("Segoe UI", 13, "bold"),
            fg_color="#da3633",
            hover_color="#f85149",
            corner_radius=8,
            height=40
        )
        self.clear_btn.grid(row=0, column=3, padx=3, sticky="ew")
        
        # Right panel (outputs)
        right_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_rowconfigure(3, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)
        
        # Scanner output section
        scan_header = ctk.CTkLabel(
            right_frame,
            text="🔍 Token Runes",
            font=("Segoe UI", 18, "bold"),
            text_color="#58a6ff",
            anchor="w"
        )
        scan_header.grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        self.scan_output = ctk.CTkTextbox(
            right_frame,
            font=("Consolas", 12),
            fg_color="#0d1117",
            text_color="#c9d1d9",
            border_width=1,
            border_color="#30363d",
            corner_radius=8,
            wrap="none",
            state="disabled"
        )
        self.scan_output.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        
        # Parser output section
        parse_header = ctk.CTkLabel(
            right_frame,
            text="🌳 Spell Tree",
            font=("Segoe UI", 18, "bold"),
            text_color="#58a6ff",
            anchor="w"
        )
        parse_header.grid(row=2, column=0, sticky="w", pady=(0, 10))
        
        self.parse_output = ctk.CTkTextbox(
            right_frame,
            font=("Consolas", 12),
            fg_color="#0d1117",
            text_color="#c9d1d9",
            border_width=1,
            border_color="#30363d",
            corner_radius=8,
            wrap="none",
            state="disabled"
        )
        self.parse_output.grid(row=3, column=0, sticky="nsew")

    def load_file(self):
        """Load an ArcaneQuest (.aq) file."""
        path = filedialog.askopenfilename(
            title="Open ArcaneQuest File",
            filetypes=[("ArcaneQuest files", "*.aq"), ("All files", "*.*")]
        )
        if not path:
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", text)
        except Exception as e:
            messagebox.showerror("Error", f"Could not read quest file: {e}")

    def on_scan(self):
        """Scan the source code for tokens."""
        source = self.input_text.get("1.0", "end")
        
        try:
            tokens = scan_source(source)
            pretty = tokens_to_pretty_lines(tokens)
            self._display_output(self.scan_output, pretty)
        except Exception as e:
            error_msg = f"❌ Scanner Error:\n{str(e)}"
            self._display_output(self.scan_output, error_msg)

    def on_parse(self):
        """Parse the source code and build AST."""
        source = self.input_text.get("1.0", "end")
        
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
                        if any(keyword in msg for keyword in [
                            "Semantic", "Type mismatch", "Undeclared",
                            "must be boolean", "Cannot determine type"
                        ]):
                            semantic_errors.append((lineno, msg))
                        else:
                            parse_errors.append((lineno, msg))
                    else:
                        parse_errors.append(error)
                
                # Build error message with fantasy theme
                error_header = f"⚠️  {len(errors)} spell error(s) detected!\n"
                
                if parse_errors:
                    error_header += f"   • {len(parse_errors)} Syntax error(s)\n"
                if semantic_errors:
                    error_header += f"   • {len(semantic_errors)} Logic error(s)\n"
                
                error_lines = []
                
                if parse_errors:
                    error_lines.append("\n━━━ SYNTAX ERRORS ━━━")
                    for lineno, msg in parse_errors:
                        error_lines.append(f"Line {lineno}: {msg}")
                
                if semantic_errors:
                    error_lines.append("\n━━━ LOGIC ERRORS ━━━")
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
                result = f"✅ Quest compiled successfully!\n\nParse tree:\n\n{tree_str}"
            
            self._display_output(self.parse_output, result)
            
        except Exception as e:
            import traceback
            error_msg = f"❌ Unexpected Magic Failure:\n{str(e)}\n\n{traceback.format_exc()}"
            self._display_output(self.parse_output, error_msg)

    def on_clear(self):
        """Clear all text areas."""
        self.input_text.delete("1.0", "end")
        self._display_output(self.scan_output, "")
        self._display_output(self.parse_output, "")

    def _display_output(self, widget, text):
        """Display text in a disabled textbox."""
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")


def main():
    root = ctk.CTk()
    app = ArcaneQuestIDE(root)
    root.geometry("1400x700")
    root.minsize(1200, 600)
    root.mainloop()


if __name__ == "__main__":
    main()