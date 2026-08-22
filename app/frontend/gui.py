import os
import sys
import logging
import shutil
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
from plyer import notification
from PIL import Image
import pystray

from app.i18n import t, set_language, get_language
from app.backend.config import load_channels, load_settings, save_settings
from app.backend.downloader import (
    find_video_url, download_video, get_next_saturday, delete_old_videos,
    format_romanian_date, get_recent_sabbaths, is_partial_download,
    list_playable_files, folder_snapshot, newly_downloaded_file,
    purge_partial_downloads,
)
from app.backend.progress import DownloadProgress, PROGRESS_PLAN_STATUS
from app.backend.changelog import load_changelog, notes_since, all_notes
from datetime import datetime
from app.frontend.settings_window import SettingsWindow
from app.frontend.file_viewer import FileViewer
from app.frontend.help_window import HelpWindow
from app.frontend.feedback_window import FeedbackWindow
from app.frontend.player_utils import play_video
from app.backend.auto_downloader import run_automatic_checks, get_current_sabbath_date
from app.backend.overrides import (
    clear_channel_videos,
    download_override,
    fetch_overrides,
    get_override,
    is_stale,
    should_poll,
)
from app.backend.updater import check_for_updates, get_asset_download_url, get_platform_asset_name, download_update
from app.backend.config import get_base_path, UPDATE_DIR, __version__
from app.backend.startup_manager import is_in_startup, add_to_startup, remove_from_startup
from app.backend.logger import setup_logger
from app.backend.telemetry import send_telemetry_ping

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

class YoutubeWeeklyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        # Created first: background threads and _perform_quit both rely on it.
        self._shutdown = threading.Event()
        self._set_app_icon()
        self.configure(bg="#2b2b2b")

        self.settings, self.startup_warnings = load_settings()
        set_language(self.settings.get("language", "en"))

        # Initialize logging
        log_folder = self.settings.get("log_folder", "data/logs")
        setup_logger(log_folder)

        # Clean up any leftover update artifacts and detect post-update
        self._just_updated = self._cleanup_update_artifacts()

        # Which version last ran, so the release notes can cover everything the
        # user skipped. The ".updated" marker only says *that* an update
        # happened, never what it came from - and someone jumping 1.4.0 to
        # 1.5.1 never saw the 1.5.0 notes at all.
        self._previous_version = self.settings.get("last_run_version")
        self._record_this_version()
        # Set when notes are owed but the window isn't up yet; shown the first
        # time the user actually opens it.
        self._pending_changelog = False

        # Synchronize startup registration with the user's stored intent.
        # When enabled, re-register unconditionally so the registry value
        # points at the current install — an existing entry from a previous
        # version may still reference a folder that no longer exists after
        # an update.
        if self.settings.get("start_with_system", False):
            add_to_startup()
        elif is_in_startup():
            remove_from_startup()

        if self.startup_warnings:
            messagebox.showwarning(t("dlg_config_warnings"), "\n".join(self.startup_warnings))

        self.quality_options = ["max", "4k", "2k", "1080p", "720p", "480p", "mp3"]
        self.channel_quality_vars = {}
        self.channel_date_vars = {}
        self.open_file_viewers = {}
        self._feedback_win = None
        self._progress = DownloadProgress()
        self.downloading_channels = set()
        self.tray_icon = None
        self._pending_update = None  # (version, url, assets) if update available

        # Initialize and run tray icon from the start
        image = Image.open(resource_path("assets/icon4.ico"))
        menu = (pystray.MenuItem(t("tray_show"), self.show_window, default=True),
                pystray.MenuItem(t("tray_quit"), self.quit_application))
        self.tray_icon = pystray.Icon("YoutubeWeekly", image, t("app_title"), menu)
        self.tray_icon.run_detached()

        style = ttk.Style()
        style.theme_use("default")
        # Standardize font across OS
        default_font = ("Segoe UI", 10) if os.name == "nt" else ("Helvetica Neue", 11)
        style.configure(".", font=default_font)
        style.configure("TButton", background="#444444", foreground="white")
        style.map("TButton", background=[("active", "#555555")])
        style.configure("Dark.TFrame", background="#2b2b2b")

        self.title(t("app_title"))
        saved_geometry = self.settings.get("main_window_geometry")
        if saved_geometry:
            self.geometry(saved_geometry)
        else:
            self.geometry("515x285+689+414")  # Default size
            self.center_window()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Unmap>", self.minimize_to_tray)
        self.base_path = self.settings.get("video_folder", "data/videos")

        # Load channels configuration
        raw = load_channels()
        self.channels = [
            {
                "name": ch_data.get("name", key),
                "url": ch_data["url"],
                "date_format": ch_data.get("date_format", "%d.%m.%Y"),
                "folder": ch_data.get("folder", key)
            }
            for key, ch_data in raw.items()
        ]

        self.recent_sabbaths_per_channel = {
            ch["name"]: ["automat"] + get_recent_sabbaths(date_format="%d.%m.%Y")
            for ch in self.channels
        }

        # Header with settings button
        header_frame = ttk.Frame(self, style="Dark.TFrame")
        header_frame.pack(fill="x", padx=10, pady=(5, 0))

        self._header_label = tk.Label(
            header_frame,
            text=t("app_title"),
            font=(default_font[0], 14, 'bold'),
            fg="white",
            bg="#2b2b2b"
        )
        self._header_label.pack(side="left")

        ttk.Button(header_frame, text="⚙", command=self.open_settings, width=3).pack(side="right")

        # Feedback button with notification badge
        self.feedback_btn_frame = tk.Frame(header_frame, bg="#2b2b2b")
        self.feedback_btn_frame.pack(side="right", padx=(0, 5))
        ttk.Button(self.feedback_btn_frame, text="💬", command=self.open_feedback, width=3).pack()
        self.feedback_badge = tk.Label(self.feedback_btn_frame, text="", fg="white", bg="#da3633",
                                        font=("Segoe UI", 7, "bold"), padx=3, pady=0)
        # Badge initially hidden, shown when there are unread replies
        self._check_feedback_badge()

        # Status label with wrapping - fixed height to prevent layout shifts
        self.status_var = tk.StringVar()
        if self._just_updated:
            self.status_var.set(t("status_update_complete", version=__version__))
        else:
            self.status_var.set(t("status_ready"))
        self.status_label = tk.Label(
            self,
            textvariable=self.status_var,
            fg="#ffffff",
            bg="#2b2b2b",
            anchor="nw",  # North-west anchor for multi-line text
            justify="left",
            wraplength=self.winfo_width(),
            font=default_font,
            height=2  # Reserve space for 2 lines of text
        )
        self.status_label.pack(pady=(5, 15), padx=20, fill="x")

        # Main content frame for channel buttons and others section
        content_frame = ttk.Frame(self, style="Dark.TFrame")
        content_frame.pack(pady=(0, 15), padx=20, fill="x", expand=True)

        # One download button + quality selector per channel
        self._channel_download_btns = {}
        for channel in self.channels:
            row = ttk.Frame(content_frame, style="Dark.TFrame")
            row.pack(pady=3, anchor="w", fill="x")

            var = tk.StringVar(value=self.settings.get("default_quality", "1080p"))
            self.channel_quality_vars[channel["name"]] = var

            combo = ttk.Combobox(row, textvariable=var, values=self.quality_options, width=6, state="readonly", justify="center")
            combo.pack(side="left", padx=(0, 5))

            self.channel_date_vars[channel["name"]] = tk.StringVar(value="automat")

            date_combo = ttk.Combobox(
                row,
                textvariable=self.channel_date_vars[channel["name"]],
                values=self.recent_sabbaths_per_channel[channel["name"]],
                width=8,
                state="readonly",
                justify="center"
            )
            date_combo.pack(side="left", padx=(0, 5))

            btn = ttk.Button(
                row,
                text=t("btn_download_channel", name=channel['name']),
                command=lambda ch=channel: self.download_for_channel(ch),
                width=34
            )
            btn.pack(side="left")
            self._channel_download_btns[channel["name"]] = btn

            play_btn = ttk.Button(
                row,
                text="▶",
                command=lambda ch=channel: self.play_latest(ch),
                width=3
            )
            play_btn.pack(side="left", padx=(5, 0))

            folder_btn = ttk.Button(
                row,
                text="📂",
                command=lambda ch=channel: self.open_channel_folder(ch),
                width=3
            )
            folder_btn.pack(side="left", padx=(5, 0))

        # Others link entry and button frame
        others_frame = ttk.Frame(content_frame)
        others_frame.configure(style="Dark.TFrame")
        others_frame.pack(pady=(5, 0), anchor="w", fill="x")

        self.others_quality_var = tk.StringVar(value=self.settings.get("default_quality", "1080p"))
        others_combo = ttk.Combobox(
            others_frame,
            textvariable=self.others_quality_var,
            values=self.quality_options,
            width=6,
            state="readonly",
            justify="center"
        )
        others_combo.pack(side="left", padx=(0, 5))

        self.others_link_var = tk.StringVar()
        self._others_entry = ttk.Entry(
            others_frame,
            textvariable=self.others_link_var,
            width=35,
        )
        self._others_placeholder = t("placeholder_paste_link")
        self._others_entry.insert(0, self._others_placeholder)
        self._others_entry.bind("<FocusIn>", lambda e: self._others_entry.delete(0, "end") if self._others_entry.get() == self._others_placeholder else None)
        self._others_entry.pack(side="left", padx=(0, 8))

        self._others_btn = ttk.Button(
            others_frame,
            text=t("btn_download"),
            command=self.download_others,
            width=12
        )
        self._others_btn.pack(side="left")

        play_others_btn = ttk.Button(
            others_frame,
            text="▶",
            command=self.play_others,
            width=3
        )
        play_others_btn.pack(side="left", padx=(5, 0))

        folder_others_btn = ttk.Button(
            others_frame,
            text="📂",
            command=self.open_others_folder,
            width=3
        )
        folder_others_btn.pack(side="left", padx=(5, 0))

        # Progress bar - always reserve space to prevent layout shifts
        # Configure thinner progress bar styles
        style.configure("Thin.Horizontal.TProgressbar", thickness=2)  # Make it thinner
        style.configure("Invisible.Horizontal.TProgressbar", background="#2b2b2b", troughcolor="#2b2b2b", borderwidth=0, lightcolor="#2b2b2b", darkcolor="#2b2b2b", thickness=8)
        
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate", style="Invisible.Horizontal.TProgressbar")
        self.progress_bar.pack(pady=(5, 5), padx=20, fill="x")

        # Bottom frame with version, quit, and help
        bottom_frame = ttk.Frame(self, style="Dark.TFrame")
        bottom_frame.pack(pady=(5, 15), padx=20, fill="x")

        # Update check button + version label (bottom left)
        ttk.Button(bottom_frame, text="\u21bb", command=self._check_for_updates_manual, width=3).pack(side="left")
        tk.Label(
            bottom_frame, text=f"v{__version__}",
            fg="#666666", bg="#2b2b2b", font=("Segoe UI", 8)
        ).pack(side="left", padx=(2, 0))

        # Help button (bottom right)
        ttk.Button(bottom_frame, text="?", command=self.open_help, width=3).pack(side="right")

        # Quit button (centered)
        self._quit_btn = ttk.Button(bottom_frame, text=t("btn_quit"), command=self.on_closing, width=10)
        self._quit_btn.pack(expand=True)

        self.resizable(False, False)
        self.bind("<Configure>", self._on_resize)

        # IMPORTANT: Move the automatic checks and update check to AFTER all UI initialization
        # This ensures self.progress_hook exists when it's passed to the threads
        
        # Run automatic checks in a separate thread
        self._run_auto_checks()

        # Watch for video overrides published by the server
        threading.Thread(target=self._override_watch_loop, daemon=True).start()

        # Check for updates in a separate thread (if enabled)
        if self.settings.get("check_for_updates", True):
            threading.Thread(target=self._check_for_updates_thread, daemon=True).start()

        # Show the release notes for anything the user hasn't seen. Starting
        # hidden in the tray, they'd land behind nothing at all - hold them
        # until the window is opened.
        if self._changelog_is_due():
            if "--start-minimized" in sys.argv:
                self._pending_changelog = True
            else:
                self.after(500, self._show_changelog)

    def _run_auto_checks(self):
        """Kick off the automatic download check on a worker thread."""
        threading.Thread(
            target=run_automatic_checks,
            args=(self.settings, self.channels, self._send_notification, self.progress_hook, self.show_window),
            kwargs={
                'status_callback': lambda msg: self.after(0, lambda: self._set_status(msg)),
                'reset_progress_callback': lambda: self.after(0, self._reset_download_progress),
            },
            daemon=True
        ).start()

    def _override_watch_loop(self):
        """Notice overrides published after this session's first check.

        Without this, an app left running in the tray would never learn that the
        operator corrected this Sabbath's video — the startup check is the only
        thing that ever looks.

        Kept deliberately quiet on the network: the manifest is a conditional
        GET (an unchanged poll is a bodyless 304), the cadence is fast only on
        Friday and Saturday, and a telemetry ping we were sending anyway can
        flag staleness for free — which short-circuits the wait.
        """
        last_poll = time.time()  # the startup check already fetched the manifest

        while not self._shutdown.wait(60):
            now = time.time()
            if not (is_stale() or should_poll(last_poll, now)):
                continue

            last_poll = now
            try:
                _overrides, changed = fetch_overrides()
            except Exception:
                continue

            if changed:
                # run_automatic_checks decides what the change actually means:
                # a force override replaces this Sabbath's video, a fallback
                # only fills a gap.
                self._run_auto_checks()

    def _set_app_icon(self):
        """Put the app icon on this window and every window it spawns.

        `iconbitmap` only dresses the window it is called on, which is why
        Settings, the folder viewers and the help windows all showed Tk's
        default feather. `iconphoto(True, ...)` sets the default for toplevels
        created afterwards, so they inherit it without each one repeating this.
        """
        icon_path = resource_path("assets/icon4.ico")
        try:
            self.iconbitmap(icon_path)
        except Exception:
            pass  # .ico is Windows-friendly; other platforms use the photo below
        try:
            from PIL import ImageTk
            self._icon_image = ImageTk.PhotoImage(Image.open(icon_path))
            self.iconphoto(True, self._icon_image)
        except Exception as e:
            logging.info(f"Could not set the default window icon: {e}")

    def _window_is_hidden(self):
        """True when the app is sitting in the tray rather than on screen.

        Must be read on the main thread, so callers capture it before handing
        work to a worker.
        """
        try:
            return self.state() in ("withdrawn", "iconic")
        except Exception:
            # No window to ask (very early, or already destroyed): fall back to
            # how we were launched.
            return "--start-minimized" in sys.argv

    def _record_this_version(self):
        """Remember the running version, so the next launch can diff against it."""
        if __version__ == "dev":
            return
        if self.settings.get("last_run_version") == __version__:
            return
        self.settings["last_run_version"] = __version__
        try:
            save_settings(self.settings)
        except Exception as e:
            logging.info(f"Could not record the running version: {e}")

    def _changelog_is_due(self):
        """Should we show release notes this launch?

        Yes when the version moved since the last run - that covers an in-app
        update, a manual reinstall over the top, and a rollback. Also yes right
        after an in-app update even if we can't tell what came before, since the
        marker proves something changed. A first-ever run shows nothing: there
        is no "what's new" for a brand-new install.
        """
        if __version__ == "dev":
            return False
        if self._previous_version and self._previous_version != __version__:
            return True
        return bool(self._just_updated) and not self._previous_version

    def _changelog_markdown(self):
        """The notes this user hasn't seen, as markdown. Empty if none."""
        content = load_changelog(get_language())
        if not content:
            return ""
        return notes_since(content, self._previous_version, __version__)

    def _show_changelog(self):
        """Show every release note new to this user, not just the latest one."""
        body = self._changelog_markdown()
        if not body:
            body = f"## v{__version__}\n\n{t('dlg_updated_fallback')}"

        if self._previous_version and self._previous_version != __version__:
            title = t("dlg_whats_new_since", previous=self._previous_version)
        else:
            title = t("dlg_whats_new", version=__version__)

        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.configure(bg="#2b2b2b")
        dialog.geometry("480x380")
        dialog.transient(self)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 480) // 2
        y = self.winfo_y() + (self.winfo_height() - 380) // 2
        dialog.geometry(f"+{x}+{y}")

        from app.frontend.help_window import HelpWindow
        formatted = HelpWindow.format_markdown(None, body)

        from tkinter import scrolledtext
        text = scrolledtext.ScrolledText(
            dialog, wrap="word", bg="#2b2b2b", fg="white",
            font=("Segoe UI", 10), borderwidth=0, highlightthickness=0,
            padx=15, pady=10
        )
        text.pack(fill="both", expand=True)
        text.insert("1.0", formatted)
        text.config(state="disabled")

        ttk.Button(dialog, text=t("btn_got_it"), command=dialog.destroy, width=10).pack(pady=(5, 15))

    def show_release_notes(self):
        """Open the full release-note history in a scrollable reader."""
        from app.frontend.help_window import HelpWindow
        content = load_changelog(get_language())
        body = all_notes(content) if content else t("changelog_not_found")
        win = HelpWindow(self, t("changelog_title"), "CHANGELOG.md", content=body)
        win.focus_set()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def load_window_position(self):
        geometry = self.settings.get("main_window_geometry")
        if geometry:
            self.geometry(geometry)

    def on_closing(self):
        self.settings["main_window_geometry"] = self.geometry()
        save_settings(self.settings)
        self.quit_application()

    def minimize_to_tray(self, event):
        if self.state() == 'iconic':
            self.hide_to_tray()

    def hide_to_tray(self):
        for viewer in list(self.open_file_viewers.values()):
            if viewer.winfo_exists():
                viewer.on_closing()
        self.withdraw()
        # Tray icon is now initialized in __init__ and runs continuously

    def show_window(self):
        self.deiconify()
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)
        self.focus_force()

        # Notes held back because we started in the tray.
        if self._pending_changelog:
            self._pending_changelog = False
            self.after(300, self._show_changelog)

        # If there's a pending update, show the dialog
        if self._pending_update:
            version, url, assets = self._pending_update
            self._pending_update = None
            self.after(300, lambda: self._show_update_dialog(version, url, assets))

    def show_from_tray(self, icon=None, item=None):
        self.bring_to_foreground()

    def bring_to_foreground(self):
        print("bring_to_foreground called!")
        
        def show_and_focus():
            if self.state() == 'iconic' or self.state() == 'withdrawn':
                self.deiconify()
            
            # Force the window to the top
            self.lift()
            self.attributes('-topmost', True)
            self.focus_force()
            
            # Remove topmost after a brief moment so it doesn't stay always on top
            self.after(100, lambda: self.attributes('-topmost', False))
            
            # Try additional focusing methods for different OS
            try:
                if sys.platform == "win32":
                    # Windows specific - try to bring window to front
                    import ctypes
                    from ctypes import wintypes
                    
                    def get_hwnd(window):
                        # Get the window handle
                        window.update()
                        return window.winfo_id()
                    
                    hwnd = get_hwnd(self)
                    # Show window and bring to foreground
                    ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception as e:
                print(f"Error with platform-specific focusing: {e}")
        
        # Schedule on main thread
        self.after(0, show_and_focus)

    def quit_application(self, icon=None, item=None):
        # Ensure operations are performed on the main Tkinter thread
        self.after(0, self._perform_quit)

    def _perform_quit(self):
        self._shutdown.set()  # stop the override watcher
        if self.tray_icon is not None and self.tray_icon.visible:
            self.tray_icon.stop()
        self.destroy()

    def open_settings(self):
        settings_win = SettingsWindow(self, self.settings)
        settings_win.transient(self)
        settings_win.grab_set()
        settings_win.focus_set()
        self.wait_window(settings_win)
        self.settings, _ = load_settings() # Reload settings
        new_lang = self.settings.get("language", "en")
        if new_lang != get_language():
            set_language(new_lang)
            self._refresh_language()
        self.base_path = self.settings.get("video_folder", "data/videos")
        # Update quality dropdowns with new default
        default_quality = self.settings.get("default_quality", "1080p")
        for var in self.channel_quality_vars.values():
            var.set(default_quality)
        self.others_quality_var.set(default_quality)

    def _refresh_language(self):
        """Update all static UI text after a language change."""
        self.title(t("app_title"))
        self._header_label.config(text=t("app_title"))
        for name, btn in self._channel_download_btns.items():
            btn.config(text=t("btn_download_channel", name=name))
        self._others_btn.config(text=t("btn_download"))
        self._quit_btn.config(text=t("btn_quit"))
        # Refresh status message if it's the default ready message
        old_placeholder = self._others_placeholder
        self._others_placeholder = t("placeholder_paste_link")
        if self._others_entry.get() == old_placeholder:
            self._others_entry.delete(0, "end")
            self._others_entry.insert(0, self._others_placeholder)
        # Reset status to translated ready message
        self._set_status(t("status_ready"))

    def open_feedback(self):
        if hasattr(self, '_feedback_win') and self._feedback_win and self._feedback_win.winfo_exists():
            self._feedback_win.destroy()
            self._feedback_win = None
            self._check_feedback_badge()
            return
        self._feedback_win = FeedbackWindow(self, self.settings)
        self._feedback_win.transient(self)
        self._feedback_win.protocol("WM_DELETE_WINDOW", self._on_feedback_close)

    def _on_feedback_close(self):
        if self._feedback_win and self._feedback_win.winfo_exists():
            self._feedback_win.destroy()
        self._feedback_win = None
        self._check_feedback_badge()

    def _check_feedback_badge(self):
        """Check for unread developer replies and show/hide badge."""
        def _check():
            try:
                from app.backend.feedback import load_local_feedback
                threads = load_local_feedback()
                unread = sum(1 for t in threads if t.get("status") == "replied")
                self.after(0, lambda: self._update_badge(unread))
            except Exception as e:
                print(f"[Feedback] Badge check failed: {e}")
        threading.Thread(target=_check, daemon=True).start()

    def _update_badge(self, count):
        if count > 0:
            self.feedback_badge.config(text=str(count))
            self.feedback_badge.place(relx=1.0, rely=0.0, anchor="ne", x=2, y=-2)
        else:
            self.feedback_badge.place_forget()

    def open_help(self):
        """Open the main help window"""
        help_win = HelpWindow(self, t("help_user_title"), "docs/main_help.md")
        help_win.focus_set()


    def _on_resize(self, event):
        if event.widget == self:
            new_wrap = max(300, event.width - 40)
            self.status_label.config(wraplength=new_wrap)

    def _set_status(self, text, severity=None):
        if severity == "success":
            color = "green"
        elif severity == "warning":
            color = "yellow"
        elif severity == "error":
            color = "red"
        else:
            color = "#ffffff"
        self.status_label.config(fg=color)
        self.status_var.set(text)
        self.update_idletasks()

    def _send_notification(self, title, message, on_click=None):
        if self.settings.get("enable_notifications", True):
            try:
                # Get the icon path - try multiple approaches for compiled app
                icon_path = None
                icon_candidates = [
                    resource_path("assets/icon4.ico"),
                    os.path.join(os.path.dirname(__file__), "assets", "icon4.ico"),
                ]
                
                # If running as compiled app, also try the temp directory
                if getattr(sys, 'frozen', False):
                    icon_candidates.extend([
                        os.path.join(sys._MEIPASS, "assets", "icon4.ico"),
                        os.path.join(sys._MEIPASS, "app", "frontend", "assets", "icon4.ico"),
                    ])
                
                for candidate in icon_candidates:
                    if os.path.exists(candidate):
                        icon_path = candidate
                        break
                
                notification.notify(
                    title=title,
                    message=message,
                    app_name="YoutubeWeekly",
                    timeout=10,
                    app_icon=icon_path
                )

            except Exception as e:
                print(f"Error sending notification: {e}")

    def download_for_channel(self, channel):
        """Launch the download check in a background thread."""
        channel_name = channel["name"]
        if channel_name in self.downloading_channels:
            self._set_status(t("status_download_in_progress", name=channel_name))
            return

        self.downloading_channels.add(channel_name)
        self._reset_download_progress()
        try:
            threading.Thread(
                target=self._worker_download,
                args=(channel,),
                daemon=True
            ).start()
        except Exception as e:
            self._set_status(t("status_error_starting", error=e), severity="error")
            if channel_name in self.downloading_channels:
                self.downloading_channels.remove(channel_name)

    def download_others(self):
        """Download video from the link in the others entry to data/videos/other."""
        if "others" in self.downloading_channels:
            self._set_status(t("status_others_in_progress"))
            return

        self.downloading_channels.add("others")
        self._reset_download_progress()
        link = self.others_link_var.get().strip()
        if not link:
            self._set_status(t("status_enter_link"), severity="warning")
            self.downloading_channels.remove("others")
            return

        self._set_status(t("status_starting_download"))
        try:
            threading.Thread(
                target=self._worker_download_others,
                args=(link,),
                daemon=True
            ).start()
        except Exception as e:
            self._set_status(t("status_error_starting", error=e), severity="error")
            self.downloading_channels.remove("others")

    def play_others(self):
        """Play the latest video in the 'other' folder."""
        threading.Thread(
            target=self._worker_play_others,
            daemon=True
        ).start()

    def open_others_folder(self):
        other_folder = os.path.join(self.base_path, "other")
        if other_folder in self.open_file_viewers and self.open_file_viewers[other_folder].winfo_exists():
            self.open_file_viewers[other_folder].on_closing()
        else:
            file_viewer_win = FileViewer(self, self.settings, "Others", other_folder, self._on_file_viewer_close, display_name=t("lbl_others_section"))
            self.open_file_viewers[other_folder] = file_viewer_win

    def _worker_download_others(self, link):
        folder = os.path.join(self.base_path, "other")
        try:
            os.makedirs(folder, exist_ok=True)
            purge_partial_downloads(folder)
            error = download_video(link, folder, self.others_quality_var.get(), progress_hook=self.progress_hook)
            if error:
                self._reset_download_progress()
                self._set_status(t("status_error_downloading", error=error), severity="error")
                self._send_notification(t("notif_download_error"), t("notif_failed_link", link=link, error=error), on_click=self.bring_to_foreground)
                messagebox.showerror(
                    t("dlg_download_error"),
                    t("dlg_download_failed", error=error)
                )
            else:
                self._finish_download_progress()
                self._send_notification(t("notif_download_complete"), t("notif_finished_link", link=link), on_click=self.bring_to_foreground)
                send_telemetry_ping(self.settings, 1, session_type="others", others_quality=self.others_quality_var.get())
        except Exception as e:
            self._reset_download_progress()
            self._set_status(t("status_error_downloading", error=e), severity="error")
            self._send_notification(t("notif_download_error"), t("notif_failed_link", link=link, error=e), on_click=self.bring_to_foreground)
            messagebox.showerror(
                t("dlg_download_error"),
                t("dlg_download_failed", error=e)
            )
        finally:
            if "others" in self.downloading_channels:
                self.downloading_channels.remove("others")

    def _worker_play_others(self):
        """Worker function to find and play the latest video in the 'other' folder."""
        other_folder = os.path.join(self.base_path, "other")
        others_label = t("lbl_others_section")
        self._set_status(t("status_searching_latest", name=others_label))

        if not os.path.exists(other_folder):
            self._set_status(t("status_no_videos_yet", name=others_label), severity="warning")
            return

        files = [os.path.join(other_folder, f) for f in list_playable_files(other_folder)]
        if not files:
            self._set_status(t("status_no_videos_found", name=others_label), severity="error")
            return

        latest_file = max(files, key=os.path.getctime)

        self._set_status(t("status_playing", filename=os.path.basename(latest_file)))
        script_path = resource_path("app/player/scripts/delayed-fullscreen.lua")
        error = play_video(self.settings, latest_file, script_path)
        if error:
            self._set_status(t("status_play_error", error=error), severity="error")
            messagebox.showerror(t("dlg_playback_error"), t("dlg_playback_failed", error=error))
        else:
            self._set_status(t("status_launched_player", name=others_label))

    def _worker_download(self, channel):
        """Worker function that runs off the main UI thread."""
        name = channel["name"]
        try:
            fmt = channel["date_format"]

            # Step 1: Find next Saturday's date or use selected date
            self._set_status(t("status_finding_video", name=name))
            selected_date = self.channel_date_vars.get(name, tk.StringVar()).get()
            if selected_date and selected_date != "automat":
                try:
                    date_obj = datetime.strptime(selected_date, "%d.%m.%Y").date()
                    next_sat = date_obj.strftime(fmt)
                except Exception as e:
                    self._set_status(t("status_date_parse_error", error=e), severity="error")
                    return
            else:
                next_sat = get_next_saturday(date_format=fmt)

            # Step 2: An override for this Sabbath, if the operator set one.
            # Overrides only ever apply to the current Sabbath, so a manual
            # download of an older date ignores them entirely.
            try:
                iso_date = datetime.strptime(next_sat, fmt).date().isoformat()
            except ValueError:
                iso_date = None

            override = None
            if iso_date and iso_date == get_current_sabbath_date():
                override, _changed = fetch_overrides()
                override = get_override(channel["folder"], iso_date, override)

            forced = override if (override and override.get("force")) else None

            # Step 3: Locate the video URL (skipped when a force override wins)
            url, match_info = (None, None)
            if not forced:
                url, match_info = find_video_url(channel["url"], next_sat, date_format=fmt)
                if not url and not override:
                    self._set_status(t("status_no_video_found", name=name, date=next_sat), severity="error")
                    self._send_notification(t("notif_video_not_found"), t("status_no_video_found", name=name, date=next_sat), on_click=self.bring_to_foreground)
                    return

            # Nothing found by search, but a fallback override is available
            source_override = forced or (override if not url else None)

            # If fuzzy match, ask user to confirm (must run dialog on main thread)
            if match_info and match_info["type"] == "fuzzy":
                result = [None]
                event = threading.Event()

                def ask_on_main_thread():
                    result[0] = messagebox.askyesno(
                        t("dlg_possible_match"),
                        t("dlg_possible_match_msg", name=name, date=next_sat, title=match_info['title'], reason=match_info['reason'])
                    )
                    event.set()

                self.after(0, ask_on_main_thread)
                event.wait()

                if not result[0]:
                    self._set_status(t("status_download_cancelled", name=name))
                    return

            # Prepare channel-specific folder
            channel_folder = os.path.join(self.base_path, channel["folder"])
            os.makedirs(channel_folder, exist_ok=True)

            keep_old = self.settings.get("keep_old_videos", False)
            numeric = next_sat.lower()
            date_obj = datetime.strptime(next_sat, fmt).date()
            romanian = format_romanian_date(date_obj).lower()

            # Step 4: Check if that exact video is already downloaded.
            # A force override deliberately replaces it, so it skips this.
            if not forced:
                existing = [
                    f for f in os.listdir(channel_folder)
                    if (numeric in f.lower() or romanian in f.lower())
                    and not is_partial_download(f)
                ]
                if existing:
                    existing_titles = ", ".join(existing)
                    self._set_status(
                        t("status_already_exists", name=name, titles=existing_titles), severity="warning"
                    )
                    return

            # Step 5: Download into channel folder. Whatever this replaces is
            # cleared *afterwards* - see Step 6. Clearing first is what left the
            # folder empty when a download failed: last week's video already
            # gone, and nothing arriving to take its place.
            quality_pref = self.channel_quality_vars.get(name, tk.StringVar()).get()
            if source_override:
                self._set_status(t("status_downloading_override", name=name))
            else:
                self._set_status(t("status_downloading", name=name, quality=quality_pref))
            try:
                # A partial from an earlier failure both blocks this retry and
                # shows up as playable.
                purge_partial_downloads(channel_folder)
                before = folder_snapshot(channel_folder)

                if source_override:
                    error = download_override(
                        source_override, channel_folder, quality_pref,
                        progress_hook=self.progress_hook, protect=keep_old,
                    )
                else:
                    error = download_video(url, channel_folder, quality_pref, protect=keep_old, progress_hook=self.progress_hook)
                if error:
                    self._reset_download_progress()
                    self._set_status(t("status_error_downloading_name", name=name, error=error), severity="error")
                    self._send_notification(t("notif_download_error"), t("notif_failed_name", name=name, error=error), on_click=self.bring_to_foreground)
                    messagebox.showerror(
                        t("dlg_download_error"),
                        t("dlg_download_failed_name", name=name, error=error)
                    )
                else:
                    # Step 6: now that the new video is safely here, drop what it
                    # replaces - never the file we just fetched. If nothing new
                    # appeared, the wanted video was already on disk: leave it.
                    produced = newly_downloaded_file(channel_folder, before)
                    if produced:
                        if forced:
                            clear_channel_videos(
                                channel_folder,
                                [numeric, romanian] if keep_old else None,
                                exclude=[produced],
                            )
                        elif not selected_date or selected_date == "automat":
                            delete_old_videos(channel_folder, keep_old=keep_old,
                                              keep=[produced])

                    self._finish_download_progress()
                    self._send_notification(t("notif_download_complete"), t("notif_finished_downloading", name=name), on_click=self.bring_to_foreground)
                    send_telemetry_ping(self.settings, 1, session_type="manual")
            except Exception as e:
                self._reset_download_progress()
                self._set_status(t("status_error_downloading_name", name=name, error=e), severity="error")
                self._send_notification(t("notif_download_error"), t("notif_failed_name", name=name, error=e), on_click=self.bring_to_foreground)
                messagebox.showerror(
                    t("dlg_download_error"),
                    t("dlg_download_failed_name", name=name, error=e)
                )
        finally:
            if name in self.downloading_channels:
                self.downloading_channels.remove(name)

    def play_latest(self, channel):
        """Play the latest video for a given channel."""
        threading.Thread(
            target=self._worker_play,
            args=(channel,),
            daemon=True
        ).start()

    def open_channel_folder(self, channel):
        channel_folder = os.path.join(self.base_path, channel["folder"])
        if channel_folder in self.open_file_viewers and self.open_file_viewers[channel_folder].winfo_exists():
            self.open_file_viewers[channel_folder].on_closing()
        else:
            file_viewer_win = FileViewer(self, self.settings, channel["name"], channel_folder, self._on_file_viewer_close)
            self.open_file_viewers[channel_folder] = file_viewer_win

    def _on_file_viewer_close(self, folder_path):
        if folder_path in self.open_file_viewers:
            del self.open_file_viewers[folder_path]

    def _worker_play(self, channel):
        """Worker function to find and play the latest video."""
        channel_folder = os.path.join(self.base_path, channel["folder"])
        self._set_status(t("status_searching_latest", name=channel['name']))

        if not os.path.exists(channel_folder):
            self._set_status(t("status_no_videos_yet", name=channel['name']), severity="warning")
            return

        files = [os.path.join(channel_folder, f) for f in list_playable_files(channel_folder)]
        if not files:
            self._set_status(t("status_no_videos_found", name=channel['name']), severity="error")
            return

        latest_file = max(files, key=os.path.getctime)

        self._set_status(t("status_playing", filename=os.path.basename(latest_file)))
        script_path = resource_path("app/player/scripts/delayed-fullscreen.lua")
        error = play_video(self.settings, latest_file, script_path)
        if error:
            self._set_status(t("status_play_error", error=error), severity="error")
            messagebox.showerror(t("dlg_playback_error"), t("dlg_playback_failed", error=error))
        else:
            self._set_status(t("status_launched_player", name=channel['name']))

    def open_folder_in_explorer(self, folder_path):
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror(t("dlg_error"), t("dlg_folder_error", error=e))

    

    def _reset_download_progress(self):
        """Clear progress state and hide the bar, ready for the next download.

        Also the recovery path after a failure: the bar used to be left frozen
        wherever it stopped, so a failed download looked like a hung one.
        """
        self._progress.reset()
        self.after(0, lambda: self.progress_bar.configure(
            style="Invisible.Horizontal.TProgressbar", value=0))

    def _render_progress(self, percent):
        def apply():
            self._set_status(t("status_downloading_percent", percent=f"{percent:.1f}"))
            self.progress_bar.configure(value=percent)
        self.after(0, apply)

    def _finish_download_progress(self):
        """Fill the bar, say so, and put it away.

        The status line is set straight from the calling worker thread, as every
        other terminal message in these workers is; only the widget updates are
        marshalled onto the main thread.
        """
        self._set_status(t("status_download_complete"), severity="success")

        def apply():
            self.progress_bar.configure(value=100)
            self.after(2000, lambda: self.progress_bar.configure(
                style="Invisible.Horizontal.TProgressbar"))
        self.after(0, apply)

    def progress_hook(self, d):
        """Feed a download event to the progress model and render the result.

        Deliberately thin: the arithmetic lives in DownloadProgress so it can be
        tested without a display.
        """
        # Space for the bar is already reserved; make it visible once bytes move.
        self.after(0, lambda: self.progress_bar.configure(
            style="Thin.Horizontal.TProgressbar"))

        status = d.get("status")

        if status == PROGRESS_PLAN_STATUS:
            self._progress.plan(streams=d.get("streams"),
                                total_bytes=d.get("total_bytes"))
            return

        if status == "downloading":
            percent = self._progress.downloading(
                d.get("filename"),
                d.get("downloaded_bytes"),
                d.get("total_bytes") or d.get("total_bytes_estimate"),
                d.get("info_dict"),
            )
            self._render_progress(percent)

        elif status == "finished":
            self._progress.finished_stream(
                d.get("filename"),
                d.get("total_bytes") or d.get("total_bytes_estimate"),
            )
            if self._progress.complete:
                self._finish_download_progress()
            else:
                self._render_progress(self._progress.percent)

    def _cleanup_update_artifacts(self):
        """Remove leftover .bak/.old files and old update ZIPs.

        Returns True if the app was just updated (marker file found).
        """
        just_updated = False

        def _try_delete(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except OSError:
                pass

        if getattr(sys, 'frozen', False):
            base = get_base_path()
            marker = os.path.join(base, ".updated")
            if os.path.exists(marker):
                just_updated = True
                _try_delete(marker)
            if os.path.exists(base):
                for item in os.listdir(base):
                    if item.endswith('.bak') or item.endswith('.old'):
                        _try_delete(os.path.join(base, item))

        if os.path.exists(UPDATE_DIR):
            for item in os.listdir(UPDATE_DIR):
                _try_delete(os.path.join(UPDATE_DIR, item))

        return just_updated

    def _get_bootstrap_path(self):
        """Return path to the update bootstrap executable."""
        base = get_base_path()
        if sys.platform == "win32":
            return os.path.join(base, "update_bootstrap.exe")
        return os.path.join(base, "update_bootstrap")

    def _check_for_updates_thread(self):
        is_new_version, latest_version, download_url, assets = check_for_updates()
        if not is_new_version:
            return

        self._pending_update = (latest_version, download_url, assets)
        is_minimized = "--start-minimized" in sys.argv
        auto_install = self.settings.get("auto_install_updates", False)

        if auto_install:
            # Auto-update at startup: show progress if the window is visible,
            # stay silent if we came up in the tray - and in that case come back
            # to the tray too, rather than stealing the screen unprompted.
            self._send_notification(t("notif_update_detected"), t("notif_installing_auto", version=latest_version))
            self.after(0, lambda: self._start_update(
                latest_version, download_url, assets,
                silent=is_minimized, relaunch_minimized=is_minimized))
        elif is_minimized:
            # Minimized but not auto-install: notify, show dialog when user opens GUI
            self._send_notification(t("notif_update_available"), t("notif_update_available_msg", version=latest_version))
        else:
            # Normal launch: show dialog immediately
            self.after(0, lambda: self._show_update_dialog(latest_version, download_url, assets))

    def _check_for_updates_manual(self):
        """Manually triggered update check (from refresh button)."""
        self._set_status(t("status_checking_updates"))
        threading.Thread(target=self._manual_update_check_thread, daemon=True).start()

    def _manual_update_check_thread(self):
        is_new_version, latest_version, download_url, assets = check_for_updates()
        if is_new_version:
            self._pending_update = (latest_version, download_url, assets)
            self.after(0, lambda: self._show_update_dialog(latest_version, download_url, assets))
        else:
            self.after(0, lambda: self._set_status(t("status_latest_version"), severity="success"))

    def _show_update_dialog(self, version, release_url, assets):
        """Show a dark-themed update dialog."""
        dialog = tk.Toplevel(self)
        dialog.title(t("dlg_update_available"))
        dialog.configure(bg="#2b2b2b")
        dialog.geometry("400x160")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 160) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(
            dialog, text=t("dlg_version_available", version=version),
            fg="white", bg="#2b2b2b", font=("Segoe UI", 12, "bold")
        ).pack(pady=(20, 5))

        tk.Label(
            dialog, text=t("dlg_update_question"),
            fg="#cccccc", bg="#2b2b2b", font=("Segoe UI", 10)
        ).pack(pady=(0, 20))

        btn_frame = tk.Frame(dialog, bg="#2b2b2b")
        btn_frame.pack()

        def on_update():
            dialog.destroy()
            self._start_update(version, release_url, assets)

        ttk.Button(btn_frame, text=t("dlg_update_now"), command=on_update, width=14).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=t("dlg_later"), command=dialog.destroy, width=10).pack(side="left", padx=5)

    def _start_update(self, version, release_url, assets, silent=False,
                      relaunch_minimized=None):
        """Begin the update process: download ZIP and launch bootstrap.

        `relaunch_minimized` decides where the *new* instance comes back. It is
        read from the window's current state, not from `--start-minimized` in
        argv: an app launched into the tray at boot keeps that flag for its
        whole life, so updating from the foreground hours later used to relaunch
        into the tray and look like nothing happened.
        """
        if relaunch_minimized is None:
            relaunch_minimized = self._window_is_hidden()
        # Check if bootstrap exists (v1.0.4 won't have it)
        bootstrap_path = self._get_bootstrap_path()
        if not getattr(sys, 'frozen', False) or not os.path.exists(bootstrap_path):
            webbrowser.open(release_url)
            messagebox.showinfo(
                t("dlg_manual_update"),
                t("dlg_manual_update_msg", version=version)
            )
            return

        # Check write permissions
        base = get_base_path()
        probe = os.path.join(base, ".update_probe")
        try:
            with open(probe, "w") as f:
                f.write("test")
            os.remove(probe)
        except OSError:
            messagebox.showerror(
                t("dlg_update_failed"),
                t("dlg_update_no_write", path=base)
            )
            return

        # Find the asset download URL
        asset_url = get_asset_download_url(assets, version)
        if not asset_url:
            webbrowser.open(release_url)
            messagebox.showinfo(
                t("dlg_manual_download"),
                t("dlg_manual_download_msg")
            )
            return

        # Download in background thread
        if not silent:
            self._set_status(t("status_downloading_update", version=version))
        threading.Thread(
            target=self._download_and_apply_update,
            args=(asset_url, version, bootstrap_path, silent, relaunch_minimized),
            daemon=True
        ).start()

    def _download_and_apply_update(self, asset_url, version, bootstrap_path,
                                   silent=False, relaunch_minimized=None):
        """Download the update ZIP and launch the bootstrap."""
        zip_name = get_platform_asset_name(version)
        zip_path = os.path.join(UPDATE_DIR, zip_name)

        def on_progress(percent):
            if not silent:
                def update():
                    self.progress_bar.configure(style="Thin.Horizontal.TProgressbar")
                    self.progress_bar.configure(value=percent)
                    self._set_status(t("status_downloading_update_percent", percent=f"{percent:.0f}"))
                self.after(0, update)

        try:
            download_update(asset_url, zip_path, progress_callback=on_progress)
        except Exception as e:
            if silent:
                self._send_notification(t("notif_update_failed"), t("notif_auto_update_failed", error=e))
            else:
                self.after(0, lambda: self._set_status(t("status_update_download_failed", error=e), severity="error"))
                self.after(0, lambda: messagebox.showerror(t("dlg_update_failed"), t("dlg_update_download_failed", error=e)))
            return

        # Launch bootstrap and exit
        base = get_base_path()
        exe_name = os.path.basename(sys.executable)
        if relaunch_minimized is None:
            relaunch_minimized = "--start-minimized" in sys.argv

        if not silent:
            self.after(0, lambda: self._set_status(t("status_installing_update")))

        bootstrap_cmd = [bootstrap_path, "--zip", zip_path, "--target", base, "--exe", exe_name, "--pid", str(os.getpid())]
        if relaunch_minimized:
            bootstrap_cmd.append("--minimized")

        try:
            subprocess.Popen(bootstrap_cmd, cwd=base)
        except OSError as e:
            if silent:
                self._send_notification(t("notif_update_failed"), t("notif_updater_failed", error=e))
            else:
                self.after(0, lambda: self._set_status(t("status_updater_launch_failed", error=e), severity="error"))
                self.after(0, lambda: messagebox.showerror(t("dlg_update_failed"), t("dlg_updater_failed", error=e)))
            return

        # Exit the app — bootstrap will take over
        # Use os._exit to ensure the process actually terminates,
        # since quit_application relies on the Tkinter event loop
        # which may not process in time for the bootstrap's PID wait.
        def force_exit():
            try:
                self.settings["main_window_geometry"] = self.geometry()
                from app.backend.config import save_settings
                save_settings(self.settings)
            except Exception:
                pass
            if self.tray_icon and self.tray_icon.visible:
                self.tray_icon.stop()
            os._exit(0)

        self.after(500, force_exit)

if __name__ == "__main__":
    import socket

    # Set the correct working directory to the project root
    if getattr(sys, 'frozen', False):
        application_path = os.path.dirname(sys.executable)
        os.chdir(application_path)
    else:
        application_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        os.chdir(application_path)

    # Use a socket to ensure single instance
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind to a specific port
        s.bind(("127.0.0.1", 65432))
    except OSError:
        # If the port is already in use, another instance is running.
        # Send a message to the running instance to show itself.
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect(("127.0.0.1", 65432))
                client_socket.sendall(b'show')
        except ConnectionRefusedError:
            # This can happen if the lock file is stale and the server is not running
            messagebox.showerror(t("dlg_error"), t("dlg_instance_error"))
        sys.exit()


    app = YoutubeWeeklyGUI()

    def ipc_server():
        with s:
            s.listen()
            while True:
                conn, addr = s.accept()
                with conn:
                    data = conn.recv(1024)
                    if data == b'show':
                        app.show_from_tray(None, None)

    threading.Thread(target=ipc_server, daemon=True).start()

    # Start minimized if --start-minimized is passed
    if "--start-minimized" in sys.argv:
        app.hide_to_tray()

    app.mainloop()
