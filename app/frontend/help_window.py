import os
import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
from app.i18n import t, get_language

class HelpWindow(tk.Toplevel):
    def __init__(self, parent, title, help_file_path, on_close_callback=None,
                 content=None):
        """`content` renders markdown directly, for text that isn't a doc file
        on disk - the release-notes reader assembles its own."""
        super().__init__(parent)
        self._content = content
        
        self.title(t("help_title", title=title))
        self.geometry("700x500")
        self.configure(bg="#2b2b2b")
        self.on_close_callback = on_close_callback
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set icon if available
        try:
            if hasattr(parent, 'iconbitmap'):
                # Try to get the icon from parent
                icon_path = self.resource_path("assets/icon4.ico")
                if os.path.exists(icon_path):
                    self.iconbitmap(icon_path)
        except:
            pass
        
        self.create_widgets(help_file_path)
        self.center_window()
    
    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_path, relative_path)
    
    def create_widgets(self, help_file_path):
        # Main frame
        main_frame = tk.Frame(self, bg="#2b2b2b")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Text widget with scrollbar
        self.text_widget = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            width=80,
            height=25,
            font=("Consolas", 10) if os.name == "nt" else ("Monaco", 10),
            bg="white",
            fg="black",
            insertbackground="black",
            selectbackground="#0078D7",
            selectforeground="white",
            state=tk.DISABLED
        )
        self.text_widget.pack(fill="both", expand=True)
        
        # Load and display help content
        if self._content is not None:
            self.show_content(self._content)
        else:
            self.load_help_content(help_file_path)
        
        # Close button frame
        button_frame = tk.Frame(main_frame, bg="#2b2b2b")
        button_frame.pack(fill="x", pady=(10, 0))
        
        close_button = tk.Button(
            button_frame,
            text=t("help_close"),
            command=self.on_closing,
            bg="#444444",
            fg="white",
            font=("Segoe UI", 9) if os.name == "nt" else ("Helvetica Neue", 10),
            relief="flat",
            padx=20,
            pady=5,
            cursor="hand2"
        )
        close_button.pack(side="right")
    
    def show_content(self, content):
        """Render markdown straight into the text widget."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(1.0, self.format_markdown(content))
        self.text_widget.config(state=tk.DISABLED)

    def load_help_content(self, help_file_path):
        """Load and display the help content from markdown file"""
        try:
            # Build language-specific filename (e.g., main_help_ro.md)
            lang = get_language()
            base_name = os.path.basename(help_file_path)
            if lang != "en":
                name, ext = os.path.splitext(base_name)
                localized_name = f"{name}_{lang}{ext}"
            else:
                localized_name = None

            # Try localized file first, then fall back to default
            possible_paths = []
            if localized_name:
                possible_paths.extend([
                    os.path.join(os.path.dirname(help_file_path), localized_name),
                    self.resource_path(os.path.join("docs", localized_name)),
                    os.path.join("docs", localized_name),
                    os.path.join(os.path.dirname(__file__), "..", "..", "docs", localized_name),
                ])
            possible_paths.extend([
                help_file_path,
                self.resource_path(help_file_path),
                os.path.join("docs", base_name),
                os.path.join(os.path.dirname(__file__), "..", "..", "docs", base_name),
            ])
            
            content = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as file:
                        content = file.read()
                    break
            
            if content is None:
                content = t("help_not_found") + "\n\n" + "\n".join(possible_paths)
            
            # Simple markdown-to-text conversion
            formatted_content = self.format_markdown(content)
            
            # Enable text widget, insert content, then disable
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, formatted_content)
            self.text_widget.config(state=tk.DISABLED)
            
        except Exception as e:
            error_content = t("help_load_error", error=str(e))
            self.text_widget.config(state=tk.NORMAL)
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, error_content)
            self.text_widget.config(state=tk.DISABLED)
    
    def format_markdown(self, content):
        """Simple markdown formatting for display in text widget"""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            # Handle headers
            if line.startswith('# '):
                formatted_lines.append('=' * 60)
                formatted_lines.append(line[2:].upper())
                formatted_lines.append('=' * 60)
            elif line.startswith('## '):
                formatted_lines.append('')
                formatted_lines.append('-' * 40)
                formatted_lines.append(line[3:])
                formatted_lines.append('-' * 40)
            elif line.startswith('### '):
                formatted_lines.append('')
                formatted_lines.append(f"» {line[4:]}")
                formatted_lines.append('')
            # Bullets are checked before bold: the release notes are all
            # "- **Thing**: text", which the bold branch used to swallow whole,
            # losing the bullet and the indent.
            elif line.strip().startswith('- '):
                formatted_lines.append(f"  • {line.strip()[2:].replace('**', '')}")
            # Handle bold text
            elif '**' in line:
                formatted_line = line.replace('**', '')
                formatted_lines.append(formatted_line)
            # Handle numbered lists
            elif line.strip() and line.strip()[0].isdigit() and '. ' in line:
                formatted_lines.append(f"  {line.strip()}")
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def on_closing(self):
        """Handle window closing"""
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()