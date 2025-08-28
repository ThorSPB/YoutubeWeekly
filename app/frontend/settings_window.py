import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from app.backend.config import save_settings, load_default_settings
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
        # Frame for better organization
        main_frame = ttk.Frame(self, style="Dark.TFrame")
        main_frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Keep old videos
        self.keep_old_videos_var = tk.BooleanVar(value=self.settings.get("keep_old_videos", False))
        keep_videos_check = ttk.Checkbutton(main_frame, text="Keep old videos", variable=self.keep_old_videos_var, style="Dark.TCheckbutton")
        keep_videos_check.pack(anchor="w", pady=5)

        # Video folder
        folder_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        folder_frame.pack(fill="x", pady=5)
        
        ttk.Label(folder_frame, text="Video folder:", style="Dark.TLabel").pack(side="left")
        entry_width = 26 if os.name == "posix" else 30  # Adjust for macOS (posix)
        self.video_folder_var = tk.StringVar(value=self.settings.get("video_folder", "data/videos"))
        folder_entry = ttk.Entry(folder_frame, textvariable=self.video_folder_var, width=57, style="Dark.TEntry")
        folder_entry.pack(side="left", padx=5)
        
        browse_button = ttk.Button(folder_frame, text="Browse", command=self.browse_folder, style="Dark.TButton")
        browse_button.pack(side="left")

        # Default quality
        quality_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        quality_frame.pack(fill="x", pady=5)

        ttk.Label(quality_frame, text="Default quality:", style="Dark.TLabel").pack(side="left")
        self.quality_var = tk.StringVar(value=self.settings.get("default_quality", "1080p"))
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var, values=["1080p", "720p", "480p", "mp3"], width=10, state="readonly", style="Dark.TCombobox")
        quality_combo.pack(side="left", padx=5)

        # Automatic Downloads setting
        self.enable_auto_download_var = tk.BooleanVar(value=self.settings.get("enable_auto_download", False))
        auto_download_check = ttk.Checkbutton(main_frame, text="Enable Automatic Downloads", variable=self.enable_auto_download_var, style="Dark.TCheckbutton")
        auto_download_check.pack(anchor="w", pady=5)

        # Notifications setting
        self.enable_notifications_var = tk.BooleanVar(value=self.settings.get("enable_notifications", True))
        notifications_check = ttk.Checkbutton(main_frame, text="Enable Notifications", variable=self.enable_notifications_var, style="Dark.TCheckbutton")
        notifications_check.pack(anchor="w", pady=5)

        # Start with system setting
        # Check actual Windows registry status and sync with settings
        actual_startup_enabled = is_in_startup()
        self.settings["start_with_system"] = actual_startup_enabled
        self.start_with_system_var = tk.BooleanVar(value=actual_startup_enabled)
        start_with_system_check = ttk.Checkbutton(main_frame, text="Start with System (minimized to tray)", variable=self.start_with_system_var, style="Dark.TCheckbutton")
        start_with_system_check.pack(anchor="w", pady=5)

        # MPV Player setting
        self.use_mpv_var = tk.BooleanVar(value=self.settings.get("use_mpv", False))
        mpv_check = ttk.Checkbutton(main_frame, text="Use MPV Player", variable=self.use_mpv_var, command=self.toggle_mpv_path_entry, style="Dark.TCheckbutton")
        mpv_check.pack(anchor="w", pady=5)

        # MPV Path
        self.mpv_path_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        self.mpv_path_frame.pack(fill="x", pady=5, padx=15)
        
        ttk.Label(self.mpv_path_frame, text="MPV Path:", style="Dark.TLabel").pack(side="left")
        self.mpv_path_var = tk.StringVar(value=self.settings.get("mpv_path", ""))
        self.mpv_path_entry = ttk.Entry(self.mpv_path_frame, textvariable=self.mpv_path_var, width=20, style="Dark.TEntry")
        self.mpv_path_entry.pack(side="left", expand=True, fill="x", padx=5)
        
        mpv_browse_button = ttk.Button(self.mpv_path_frame, text="Browse", command=self.browse_mpv_path, style="Dark.TButton")
        mpv_browse_button.pack(side="left")

        self.toggle_mpv_path_entry() # Set initial state

        # MPV Fullscreen setting
        self.mpv_fullscreen_var = tk.BooleanVar(value=self.settings.get("mpv_fullscreen", False))
        mpv_fullscreen_check = ttk.Checkbutton(main_frame, text="MPV Fullscreen", variable=self.mpv_fullscreen_var, style="Dark.TCheckbutton")
        mpv_fullscreen_check.pack(anchor="w", pady=5)

        # MPV Volume setting
        volume_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        volume_frame.pack(fill="x", pady=5)
        ttk.Label(volume_frame, text="MPV Volume (0-200):", style="Dark.TLabel").pack(side="left")
        self.mpv_volume_var = tk.IntVar(value=self.settings.get("mpv_volume", 100))
        self.mpv_volume_var.trace_add("write", self._validate_mpv_volume)
        mpv_volume_slider = ttk.Scale(volume_frame, from_=0, to=130, orient="horizontal", variable=self.mpv_volume_var)
        mpv_volume_slider.pack(side="left", expand=True, fill="x", padx=5)
        mpv_volume_entry = ttk.Entry(volume_frame, textvariable=self.mpv_volume_var, width=5, style="Dark.TEntry")
        mpv_volume_entry.pack(side="left")

        # MPV Monitor selection
        monitor_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        monitor_frame.pack(fill="x", pady=5)
        ttk.Label(monitor_frame, text="MPV Monitor:", style="Dark.TLabel").pack(side="left")
        self.mpv_screen_var = tk.StringVar(value=self.settings.get("mpv_screen", "Default"))
        self.monitor_options = ["Default"] + [str(i) for i, _ in enumerate(get_monitors())]
        mpv_screen_combo = ttk.Combobox(monitor_frame, textvariable=self.mpv_screen_var, values=self.monitor_options, width=10, state="readonly", style="Dark.TCombobox")
        mpv_screen_combo.pack(side="left", padx=5)

        # MPV Custom Arguments
        custom_args_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        custom_args_frame.pack(fill="x", pady=5)
        ttk.Label(custom_args_frame, text="MPV Custom Arguments:", style="Dark.TLabel").pack(side="left")
        self.mpv_custom_args_var = tk.StringVar(value=self.settings.get("mpv_custom_args", ""))
        mpv_custom_args_entry = ttk.Entry(custom_args_frame, textvariable=self.mpv_custom_args_var, width=40, style="Dark.TEntry")
        mpv_custom_args_entry.pack(side="left", expand=True, fill="x", padx=5)

        # FFmpeg Path (moved to bottom)
        self.ffmpeg_path_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        self.ffmpeg_path_frame.pack(fill="x", pady=5)
        
        ttk.Label(self.ffmpeg_path_frame, text="FFmpeg Path:", style="Dark.TLabel").pack(side="left")
        self.ffmpeg_path_var = tk.StringVar(value=self.settings.get("ffmpeg_path", ""))
        self.ffmpeg_path_entry = ttk.Entry(self.ffmpeg_path_frame, textvariable=self.ffmpeg_path_var, width=40, style="Dark.TEntry")
        self.ffmpeg_path_entry.pack(side="left", padx=5)
        
        ffmpeg_browse_button = ttk.Button(self.ffmpeg_path_frame, text="Browse", command=self.browse_ffmpeg_path, style="Dark.TButton")
        ffmpeg_browse_button.pack(side="left")

        # Warning for FFmpeg (moved to bottom with FFmpeg setting)
        warning_label = ttk.Label(main_frame, text="Warning: Only change FFmpeg path if you know what you're doing. Incorrect path will break downloads. Clicking \"Reset to Defaults\" will restore the original path.",
                  foreground="red", wraplength=400, justify="left", style="Dark.TLabel")
        warning_label.configure(foreground="red")  # Override the style for warning color
        warning_label.pack(anchor="w", pady=(0, 10))

        # Buttons
        button_frame = ttk.Frame(main_frame, style="Dark.TFrame")
        button_frame.pack(side="bottom", fill="x", pady=10)

        save_button = ttk.Button(button_frame, text="Save", command=self.save_settings, style="Dark.TButton")
        save_button.pack(side="right", padx=5)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.on_closing, style="Dark.TButton")
        cancel_button.pack(side="right")

        reset_button = ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_to_defaults, style="Dark.TButton")
        reset_button.pack(side="left", padx=5)

        # Help button
        help_button = ttk.Button(button_frame, text="?", command=self.open_help, style="Dark.TButton", width=3)
        help_button.pack(side="left", padx=(0, 10))

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
        self.use_mpv_var.set(self.settings.get("use_mpv", False))
        self.mpv_path_var.set(self.settings.get("mpv_path", ""))
        self.mpv_fullscreen_var.set(self.settings.get("mpv_fullscreen", False))
        self.mpv_volume_var.set(self.settings.get("mpv_volume", 100))
        self.mpv_screen_var.set(self.settings.get("mpv_screen", "Default"))
        self.mpv_custom_args_var.set(self.settings.get("mpv_custom_args", ""))
        self.ffmpeg_path_var.set(self.settings.get("ffmpeg_path", ""))