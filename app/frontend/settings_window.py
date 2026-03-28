import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from app.backend.config import save_settings, load_default_settings, __version__
from app.frontend.help_window import HelpWindow
from screeninfo import get_monitors
from app.backend.startup_manager import add_to_startup, remove_from_startup, is_in_startup

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("537x536+79+73")
        self.resizable(False, False)
        self.configure(bg="#2b2b2b")

        self.settings = settings
        self.load_window_position()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configure dark theme styles
        self.setup_dark_theme()
        
        self.create_widgets()

    def setup_dark_theme(self):
        """Configure dark theme for all widgets"""
        style = ttk.Style(self)
        style.theme_use("default")
        
        # Configure dark theme colors
        dark_bg = "#2b2b2b"
        dark_fg = "white"
        field_bg = "white"  # White background for input fields
        field_fg = "black"  # Black text for input fields
        selected_bg = "#0078D7"
        
        # Frame styling
        style.configure("Dark.TFrame", background=dark_bg)
        
        # Label styling
        style.configure("Dark.TLabel", background=dark_bg, foreground=dark_fg, font=('Segoe UI', 9))
        
        # Entry styling (white background, black text)
        style.configure("Dark.TEntry", 
                       background=field_bg, 
                       foreground=field_fg, 
                       fieldbackground=field_bg,
                       bordercolor="#cccccc",
                       lightcolor="#cccccc",
                       darkcolor="#cccccc",
                       insertcolor=field_fg)
        style.map("Dark.TEntry",
                 focuscolor=[("!focus", "#cccccc")],
                 bordercolor=[("focus", selected_bg)])
        
        # Button styling
        style.configure("Dark.TButton",
                       background="#3c3c3c",
                       foreground=dark_fg,
                       bordercolor=dark_bg,
                       lightcolor=dark_bg,
                       darkcolor=dark_bg)
        style.map("Dark.TButton",
                 background=[("active", selected_bg), ("pressed", "#005a9e")],
                 foreground=[("active", "white"), ("pressed", "white")])
        
        # Checkbutton styling
        style.configure("Dark.TCheckbutton",
                       background=dark_bg,
                       foreground=dark_fg,
                       focuscolor=dark_bg,
                       bordercolor=dark_bg)
        style.map("Dark.TCheckbutton",
                 background=[("active", dark_bg)],
                 foreground=[("active", dark_fg)])
        
        # Combobox styling (white background, black text)
        style.configure("Dark.TCombobox",
                       background=field_bg,
                       foreground=field_fg,
                       fieldbackground=field_bg,
                       bordercolor="#cccccc",
                       arrowcolor=field_fg,
                       lightcolor="#cccccc",
                       darkcolor="#cccccc")
        style.map("Dark.TCombobox",
                 fieldbackground=[("readonly", field_bg)],
                 selectbackground=[("readonly", field_bg)],
                 selectforeground=[("readonly", field_fg)])
        
        # Scale styling (white background like input fields)
        style.configure("TScale",
                       background=dark_bg,
                       troughcolor="white")

    def create_widgets(self):
        # Notebook (tabs)
        style = ttk.Style(self)
        style.configure("Dark.TNotebook", background="#2b2b2b", borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background="#3c3c3c", foreground="white", padding=[10, 5])
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", "#2b2b2b")],
                  foreground=[("selected", "white")])

        notebook = ttk.Notebook(self, style="Dark.TNotebook")
        notebook.pack(padx=10, pady=(10, 0), fill="both", expand=True)

        # === General Tab ===
        general_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(general_frame, text="General")

        self.keep_old_videos_var = tk.BooleanVar(value=self.settings.get("keep_old_videos", False))
        ttk.Checkbutton(general_frame, text="Keep old videos", variable=self.keep_old_videos_var, style="Dark.TCheckbutton").pack(anchor="w", pady=5, padx=10)

        folder_frame = ttk.Frame(general_frame, style="Dark.TFrame")
        folder_frame.pack(fill="x", pady=5, padx=10)
        ttk.Label(folder_frame, text="Video folder:", style="Dark.TLabel").pack(side="left")
        self.video_folder_var = tk.StringVar(value=self.settings.get("video_folder", "data/videos"))
        ttk.Entry(folder_frame, textvariable=self.video_folder_var, width=45, style="Dark.TEntry").pack(side="left", padx=5)
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder, style="Dark.TButton").pack(side="left")

        quality_frame = ttk.Frame(general_frame, style="Dark.TFrame")
        quality_frame.pack(fill="x", pady=5, padx=10)
        ttk.Label(quality_frame, text="Default quality:", style="Dark.TLabel").pack(side="left")
        self.quality_var = tk.StringVar(value=self.settings.get("default_quality", "1080p"))
        ttk.Combobox(quality_frame, textvariable=self.quality_var, values=["max", "4k", "2k", "1080p", "720p", "480p", "mp3"], width=10, state="readonly", style="Dark.TCombobox").pack(side="left", padx=5)

        self.enable_auto_download_var = tk.BooleanVar(value=self.settings.get("enable_auto_download", False))
        ttk.Checkbutton(general_frame, text="Enable Automatic Downloads", variable=self.enable_auto_download_var, style="Dark.TCheckbutton").pack(anchor="w", pady=5, padx=10)

        self.enable_notifications_var = tk.BooleanVar(value=self.settings.get("enable_notifications", True))
        ttk.Checkbutton(general_frame, text="Enable Notifications", variable=self.enable_notifications_var, style="Dark.TCheckbutton").pack(anchor="w", pady=5, padx=10)

        actual_startup_enabled = is_in_startup()
        self.settings["start_with_system"] = actual_startup_enabled
        self.start_with_system_var = tk.BooleanVar(value=actual_startup_enabled)
        self.start_with_system_var.trace_add("write", lambda *_: self._update_auto_install_state())
        ttk.Checkbutton(general_frame, text="Start with System (minimized to tray)", variable=self.start_with_system_var, style="Dark.TCheckbutton").pack(anchor="w", pady=5, padx=10)

        self.check_for_updates_var = tk.BooleanVar(value=self.settings.get("check_for_updates", True))
        self.check_for_updates_var.trace_add("write", lambda *_: self._update_auto_install_state())
        ttk.Checkbutton(general_frame, text="Check for updates on startup", variable=self.check_for_updates_var, style="Dark.TCheckbutton").pack(anchor="w", pady=5, padx=10)

        # Auto-install with visual tree indicator showing dependency
        auto_install_frame = ttk.Frame(general_frame, style="Dark.TFrame")
        auto_install_frame.pack(anchor="w", pady=(0, 5), padx=10)
        self.auto_install_tree_label = tk.Label(
            auto_install_frame, text="  └ ", fg="#666666", bg="#2b2b2b", font=("Consolas", 10)
        )
        self.auto_install_tree_label.pack(side="left")
        self.auto_install_updates_var = tk.BooleanVar(value=self.settings.get("auto_install_updates", False))
        self.auto_install_check = ttk.Checkbutton(
            auto_install_frame, text="Auto-install updates (when minimized to tray)",
            variable=self.auto_install_updates_var, style="Dark.TCheckbutton"
        )
        self.auto_install_check.pack(side="left")
        self._update_auto_install_state()

        # === Player Tab ===
        player_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(player_frame, text="Player")

        self.use_mpv_var = tk.BooleanVar(value=self.settings.get("use_mpv", False))
        ttk.Checkbutton(player_frame, text="Use MPV Player", variable=self.use_mpv_var, command=self.toggle_mpv_path_entry, style="Dark.TCheckbutton").pack(anchor="w", pady=5, padx=10)

        self.mpv_path_frame = ttk.Frame(player_frame, style="Dark.TFrame")
        self.mpv_path_frame.pack(fill="x", pady=5, padx=20)
        ttk.Label(self.mpv_path_frame, text="MPV Path:", style="Dark.TLabel").pack(side="left")
        self.mpv_path_var = tk.StringVar(value=self.settings.get("mpv_path", ""))
        self.mpv_path_entry = ttk.Entry(self.mpv_path_frame, textvariable=self.mpv_path_var, width=20, style="Dark.TEntry")
        self.mpv_path_entry.pack(side="left", expand=True, fill="x", padx=5)
        ttk.Button(self.mpv_path_frame, text="Browse", command=self.browse_mpv_path, style="Dark.TButton").pack(side="left")
        self.toggle_mpv_path_entry()

        self.mpv_fullscreen_var = tk.BooleanVar(value=self.settings.get("mpv_fullscreen", False))
        ttk.Checkbutton(player_frame, text="MPV Fullscreen", variable=self.mpv_fullscreen_var, style="Dark.TCheckbutton").pack(anchor="w", pady=5, padx=10)

        volume_frame = ttk.Frame(player_frame, style="Dark.TFrame")
        volume_frame.pack(fill="x", pady=5, padx=10)
        ttk.Label(volume_frame, text="Volume (0-130):", style="Dark.TLabel").pack(side="left")
        self.mpv_volume_var = tk.IntVar(value=self.settings.get("mpv_volume", 100))
        self.mpv_volume_var.trace_add("write", self._validate_mpv_volume)
        ttk.Scale(volume_frame, from_=0, to=130, orient="horizontal", variable=self.mpv_volume_var).pack(side="left", expand=True, fill="x", padx=5)
        ttk.Entry(volume_frame, textvariable=self.mpv_volume_var, width=5, style="Dark.TEntry").pack(side="left")

        monitor_frame = ttk.Frame(player_frame, style="Dark.TFrame")
        monitor_frame.pack(fill="x", pady=5, padx=10)
        ttk.Label(monitor_frame, text="Monitor:", style="Dark.TLabel").pack(side="left")
        self.mpv_screen_var = tk.StringVar(value=self.settings.get("mpv_screen", "Default"))
        self.monitor_options = ["Default"] + [str(i) for i, _ in enumerate(get_monitors())]
        ttk.Combobox(monitor_frame, textvariable=self.mpv_screen_var, values=self.monitor_options, width=10, state="readonly", style="Dark.TCombobox").pack(side="left", padx=5)

        custom_args_frame = ttk.Frame(player_frame, style="Dark.TFrame")
        custom_args_frame.pack(fill="x", pady=5, padx=10)
        ttk.Label(custom_args_frame, text="Custom Arguments:", style="Dark.TLabel").pack(side="left")
        self.mpv_custom_args_var = tk.StringVar(value=self.settings.get("mpv_custom_args", ""))
        ttk.Entry(custom_args_frame, textvariable=self.mpv_custom_args_var, width=35, style="Dark.TEntry").pack(side="left", expand=True, fill="x", padx=5)

        # === Advanced Tab ===
        advanced_frame = ttk.Frame(notebook, style="Dark.TFrame")
        notebook.add(advanced_frame, text="Advanced")

        ffmpeg_frame = ttk.Frame(advanced_frame, style="Dark.TFrame")
        ffmpeg_frame.pack(fill="x", pady=5, padx=10)
        ttk.Label(ffmpeg_frame, text="FFmpeg Path:", style="Dark.TLabel").pack(side="left")
        self.ffmpeg_path_var = tk.StringVar(value=self.settings.get("ffmpeg_path", ""))
        self.ffmpeg_path_entry = ttk.Entry(ffmpeg_frame, textvariable=self.ffmpeg_path_var, width=42, style="Dark.TEntry")
        self.ffmpeg_path_entry.pack(side="left", padx=5)
        ttk.Button(ffmpeg_frame, text="Browse", command=self.browse_ffmpeg_path, style="Dark.TButton").pack(side="left")

        warning_label = ttk.Label(advanced_frame, text="Warning: Only change FFmpeg path if you know what you're doing.",
                  foreground="red", wraplength=480, justify="left", style="Dark.TLabel")
        warning_label.configure(foreground="red")
        warning_label.pack(anchor="w", pady=(0, 10), padx=10)

        ttk.Button(advanced_frame, text="Rollback to Previous Version", command=self._show_rollback_dialog, style="Dark.TButton").pack(anchor="w", pady=10, padx=10)

        # === Bottom Buttons (outside tabs) ===
        button_frame = ttk.Frame(self, style="Dark.TFrame")
        button_frame.pack(fill="x", padx=10, pady=10)

        ttk.Button(button_frame, text="Save", command=self.save_settings, style="Dark.TButton").pack(side="right", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.on_closing, style="Dark.TButton").pack(side="right")
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_to_defaults, style="Dark.TButton").pack(side="left", padx=5)
        ttk.Button(button_frame, text="?", command=self.open_help, style="Dark.TButton", width=3).pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.video_folder_var.set(folder_selected)

    def browse_mpv_path(self):
        file_selected = filedialog.askopenfilename()
        if file_selected:
            self.mpv_path_var.set(file_selected)

    def browse_ffmpeg_path(self):
        file_selected = filedialog.askopenfilename()
        if file_selected:
            self.ffmpeg_path_var.set(file_selected)

    def toggle_mpv_path_entry(self):
        state = "normal" if self.use_mpv_var.get() else "disabled"
        self.mpv_path_entry.config(state=state)

    def _update_auto_install_state(self):
        """Grey out auto-install checkbox when its dependencies are disabled."""
        can_auto_install = self.start_with_system_var.get() and self.check_for_updates_var.get()
        state = "normal" if can_auto_install else "disabled"
        self.auto_install_check.config(state=state)
        self.auto_install_tree_label.config(fg="#666666" if can_auto_install else "#444444")
        if not can_auto_install:
            self.auto_install_updates_var.set(False)

    def load_window_position(self):
        geometry = self.settings.get("settings_window_geometry")
        if geometry:
            self.geometry(geometry)

    def on_closing(self):
        self.settings["settings_window_geometry"] = self.geometry()
        save_settings(self.settings)
        self.destroy()

    def open_help(self):
        """Open the settings help window"""
        help_win = HelpWindow(self, "Settings Guide", "docs/settings_help.md")
        help_win.focus_set()

    def save_settings(self):
        self.settings["keep_old_videos"] = self.keep_old_videos_var.get()
        self.settings["video_folder"] = self.video_folder_var.get()
        self.settings["default_quality"] = self.quality_var.get()
        self.settings["enable_auto_download"] = self.enable_auto_download_var.get()
        self.settings["enable_notifications"] = self.enable_notifications_var.get()
        
        # Handle startup with system setting
        new_startup_value = self.start_with_system_var.get()
        old_startup_value = self.settings.get("start_with_system", False)
        
        if new_startup_value != old_startup_value:
            if new_startup_value:
                add_to_startup()
            else:
                remove_from_startup()
        
        self.settings["start_with_system"] = new_startup_value
        self.settings["check_for_updates"] = self.check_for_updates_var.get()
        self.settings["auto_install_updates"] = self.auto_install_updates_var.get()
        self.settings["use_mpv"] = self.use_mpv_var.get()
        self.settings["mpv_path"] = self.mpv_path_var.get()
        self.settings["ffmpeg_path"] = self.ffmpeg_path_var.get()
        self.settings["mpv_fullscreen"] = self.mpv_fullscreen_var.get()
        self.settings["mpv_volume"] = self.mpv_volume_var.get()
        self.settings["mpv_screen"] = self.mpv_screen_var.get()
        self.settings["mpv_custom_args"] = self.mpv_custom_args_var.get()
        self.settings["settings_window_geometry"] = self.geometry()

        save_settings(self.settings)

        self.destroy()

    def _validate_mpv_volume(self, *args):
        try:
            current_volume = self.mpv_volume_var.get()
            if current_volume > 130:
                self.mpv_volume_var.set(130)
        except tk.TclError: # Handle cases where input is not an integer
            pass

    def reset_to_defaults(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset all settings to their default values? This cannot be undone."):
            default_settings = load_default_settings()
            self.settings = default_settings
            self.update_ui_from_settings()
            self.save_settings()

    def update_ui_from_settings(self):
        self.keep_old_videos_var.set(self.settings.get("keep_old_videos", False))
        self.video_folder_var.set(self.settings.get("video_folder", "data/videos"))
        self.quality_var.set(self.settings.get("default_quality", "1080p"))
        self.enable_auto_download_var.set(self.settings.get("enable_auto_download", False))
        self.enable_notifications_var.set(self.settings.get("enable_notifications", True))
        self.check_for_updates_var.set(self.settings.get("check_for_updates", True))
        self.auto_install_updates_var.set(self.settings.get("auto_install_updates", False))
        self.use_mpv_var.set(self.settings.get("use_mpv", False))
        self.mpv_path_var.set(self.settings.get("mpv_path", ""))
        self.mpv_fullscreen_var.set(self.settings.get("mpv_fullscreen", False))
        self.mpv_volume_var.set(self.settings.get("mpv_volume", 100))
        self.mpv_screen_var.set(self.settings.get("mpv_screen", "Default"))
        self.mpv_custom_args_var.set(self.settings.get("mpv_custom_args", ""))
        self.ffmpeg_path_var.set(self.settings.get("ffmpeg_path", ""))

    def _show_rollback_dialog(self):
        """Show a dialog to select a previous version to rollback to."""
        from app.backend.updater import get_available_versions, get_asset_download_url
        from app.backend.config import get_base_path, UPDATE_DIR

        dialog = tk.Toplevel(self)
        dialog.title("Rollback to Previous Version")
        dialog.configure(bg="#2b2b2b")
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 250) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(
            dialog, text=f"Current version: v{__version__}",
            fg="white", bg="#2b2b2b", font=("Segoe UI", 10, "bold")
        ).pack(pady=(15, 5))

        tk.Label(
            dialog, text="Loading available versions...",
            fg="#cccccc", bg="#2b2b2b", font=("Segoe UI", 9)
        ).pack(pady=(0, 10))

        listbox_frame = tk.Frame(dialog, bg="#2b2b2b")
        listbox_frame.pack(fill="both", expand=True, padx=20)

        listbox = tk.Listbox(
            listbox_frame, bg="#3c3c3c", fg="white", selectbackground="#0078D7",
            font=("Segoe UI", 10), borderwidth=0, highlightthickness=0
        )
        listbox.pack(fill="both", expand=True)

        btn_frame = tk.Frame(dialog, bg="#2b2b2b")
        btn_frame.pack(pady=(10, 15))

        rollback_btn = ttk.Button(btn_frame, text="Rollback", state="disabled", width=12)
        rollback_btn.pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, width=10).pack(side="left", padx=5)

        # Store versions data for selection
        versions_data = []

        def on_versions_loaded(versions):
            if not versions:
                listbox.insert(tk.END, "No other versions available")
                return

            versions_data.clear()
            versions_data.extend(versions)
            listbox.delete(0, tk.END)
            for version, _ in versions:
                listbox.insert(tk.END, f"  v{version}")
            rollback_btn.config(state="normal")

        def on_select_and_rollback():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a version to rollback to.", parent=dialog)
                return

            version, assets = versions_data[selection[0]]
            confirmed = messagebox.askyesno(
                "Confirm Rollback",
                f"Are you sure you want to rollback to v{version}?\n\n"
                "Your settings and downloaded videos will be preserved.\n"
                "The app will close and restart on the selected version.",
                parent=dialog
            )
            if not confirmed:
                return

            asset_url = get_asset_download_url(assets, version)
            if not asset_url:
                messagebox.showerror("Rollback Failed", "No download available for this version on your platform.", parent=dialog)
                return

            dialog.destroy()
            self.destroy()

            # Trigger the rollback via the parent GUI's update mechanism
            parent = self.master
            if hasattr(parent, '_start_update'):
                parent._pending_update = None
                parent._start_update(version, "", assets)

        rollback_btn.config(command=on_select_and_rollback)

        # Load versions in background
        def load_versions():
            versions = get_available_versions()
            dialog.after(0, lambda: on_versions_loaded(versions))

        threading.Thread(target=load_versions, daemon=True).start()