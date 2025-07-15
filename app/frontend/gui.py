import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import shlex
import time
import sys
from plyer import notification
import json

from app.backend.config import load_channels, load_settings, save_settings
from app.backend.downloader import find_video_url, download_video, get_next_saturday, delete_old_videos, format_romanian_date, get_recent_sabbaths
from datetime import datetime
from app.frontend.settings_window import SettingsWindow
from app.frontend.file_viewer import FileViewer
from app.backend.auto_downloader import run_automatic_checks

class YoutubeWeeklyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configure(bg="#2b2b2b")

        self.settings, self.startup_warnings = load_settings()

        if self.startup_warnings:
            messagebox.showwarning("Configuration Warnings", "\n".join(self.startup_warnings))

        self.quality_options = ["1080p", "720p", "480p", "mp3"]
        self.channel_quality_vars = {}
        self.channel_date_vars = {}
        self.open_file_viewers = {}

        style = ttk.Style()
        style.theme_use("default")
        # Standardize font across OS
        default_font = ("Segoe UI", 10) if os.name == "nt" else ("Helvetica Neue", 11)
        style.configure(".", font=default_font)
        style.configure("TButton", background="#444444", foreground="white")
        style.map("TButton", background=[("active", "#555555")])
        style.configure("Dark.TFrame", background="#2b2b2b")

        self.title("YoutubeWeekly Downloader")
        self.geometry("515x260")
        self.load_window_position()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
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

        # Run automatic checks in a separate thread
        threading.Thread(
            target=run_automatic_checks,
            args=(self.settings, self.channels, self._send_notification),
            daemon=True
        ).start()

        self.recent_sabbaths_per_channel = {
            ch["name"]: ["automat"] + get_recent_sabbaths(date_format="%d.%m.%Y")
            for ch in self.channels
        }

        # Header with settings button
        header_frame = ttk.Frame(self, style="Dark.TFrame")
        header_frame.pack(fill="x", padx=10, pady=(5, 0))

        tk.Label(
            header_frame,
            text="YoutubeWeekly Downloader",
            font=(default_font[0], 14, 'bold'),
            fg="white",
            bg="#2b2b2b"
        ).pack(side="left")

        ttk.Button(header_frame, text="⚙", command=self.open_settings, width=3).pack(side="right")

        # Status label with wrapping
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            self,
            textvariable=self.status_var,
            fg="#ffffff",
            bg="#2b2b2b",
            anchor="w",
            justify="left",
            wraplength=self.winfo_width(),
            font=default_font
        )
        self.status_label.pack(pady=(5, 15), padx=20, fill="x")

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.configure(style="Dark.TFrame")
        btn_frame.pack(pady=(0, 15), padx=20, fill="x")

        # One download button + quality selector per channel
        for channel in self.channels:
            row = ttk.Frame(btn_frame, style="Dark.TFrame")
            row.pack(pady=3, anchor="w")

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
                text=f"Download {channel['name']}",
                command=lambda ch=channel: self.download_for_channel(ch),
                width=26
            )
            btn.pack(side="left")

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
        others_frame = ttk.Frame(self)
        others_frame.configure(style="Dark.TFrame")
        others_frame.pack(pady=(0, 15), padx=20, anchor="w")

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
        others_entry = ttk.Entry(
            others_frame,
            textvariable=self.others_link_var,
            width=24,
        )
        others_entry.insert(0, "Paste YouTube link...")
        others_entry.bind("<FocusIn>", lambda e: others_entry.delete(0, "end") if others_entry.get() == "Paste YouTube link..." else None)
        others_entry.pack(side="left", padx=(0, 9))

        others_btn = ttk.Button(
            others_frame,
            text="Download",
            command=self.download_others,
            width=11
        )
        others_btn.pack(side="left")

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

        # Quit button
        ttk.Button(self, text="Quit", command=self.on_closing, width=10).pack(pady=(0, 15))


        self.resizable(False, False)

        self.bind("<Configure>", self._on_resize)

    def load_window_position(self):
        geometry = self.settings.get("main_window_geometry")
        if geometry:
            self.geometry(geometry)

    def on_closing(self):
        self.settings["main_window_geometry"] = self.geometry()
        save_settings(self.settings)
        self.destroy()

    def open_settings(self):
        settings_win = SettingsWindow(self)
        settings_win.transient(self)
        settings_win.grab_set()
        settings_win.focus_set()
        self.wait_window(settings_win)
        self.settings, _ = load_settings() # Reload settings
        self.base_path = self.settings.get("video_folder", "data/videos")
        # Update quality dropdowns with new default
        default_quality = self.settings.get("default_quality", "1080p")
        for var in self.channel_quality_vars.values():
            var.set(default_quality)
        self.others_quality_var.set(default_quality)


    def _on_resize(self, event):
        if event.widget == self:
            new_wrap = max(300, event.width - 40)
            self.status_label.config(wraplength=new_wrap)

    def _set_status(self, text):
        if "already exists" in text.lower():
            color = "yellow"
        elif "no video found" in text.lower():
            color = "red"
        elif "download complete" in text.lower():
            color = "green"
        elif "error" in text.lower():
            color = "red"
        else:
            color = "#ffffff"
        self.status_label.config(fg=color)
        self.status_var.set(text)
        self.update_idletasks()

    def _send_notification(self, title, message):
        if self.settings.get("enable_notifications", True):
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="YoutubeWeekly Downloader",
                    timeout=10
                )
            except Exception as e:
                print(f"Error sending notification: {e}")

    def download_for_channel(self, channel):
        """Launch the download check in a background thread."""
        threading.Thread(
            target=self._worker_download,
            args=(channel,),
            daemon=True
        ).start()

    def download_others(self):
        """Download video from the link in the others entry to data/videos/other."""
        link = self.others_link_var.get().strip()
        if not link:
            self._set_status("Please enter a YouTube link.")
            return

        self._set_status("Starting download...")
        threading.Thread(
            target=self._worker_download_others,
            args=(link,),
            daemon=True
        ).start()

    def play_others(self):
        """Play the latest video in the 'other' folder."""
        threading.Thread(
            target=self._worker_play_others,
            daemon=True
        ).start()

    def open_others_folder(self):
        other_folder = os.path.join(self.base_path, "other")
        if other_folder in self.open_file_viewers and self.open_file_viewers[other_folder].winfo_exists():
            self.open_file_viewers[other_folder].lift()
            self.open_file_viewers[other_folder].focus_set()
        else:
            file_viewer_win = FileViewer(self, self.settings, "Others", other_folder, self._on_file_viewer_close)
            file_viewer_win.transient(self)
            file_viewer_win.focus_set()
            self.open_file_viewers[other_folder] = file_viewer_win

    def _worker_download_others(self, link):
        folder = os.path.join(self.base_path, "other")
        try:
            download_video(link, folder, self.others_quality_var.get())
            self._set_status("Download complete.")
            self._send_notification("Download Complete", f"Finished downloading video from link: {link}")
        except Exception as e:
            self._set_status("Error downloading.")
            self._send_notification("Download Error", f"Failed to download video from link: {link}")
            messagebox.showerror(
                "Download Error",
                f"Failed to download video:\n{e}"
            )

    def _worker_play_others(self):
        """Worker function to find and play the latest video in the 'other' folder."""
        other_folder = os.path.join(self.base_path, "other")
        self._set_status("Searching for latest video in Others...")

        if not os.path.exists(other_folder):
            self._set_status("No videos downloaded for Others yet.")
            return

        files = [os.path.join(other_folder, f) for f in os.listdir(other_folder)]
        if not files:
            self._set_status("No videos found for Others.")
            return

        latest_file = max(files, key=os.path.getctime)

        try:
            self._set_status(f"Playing {os.path.basename(latest_file)}...")
            if self.settings.get("use_mpv", False) and self.settings.get("mpv_path"): # Use MPV if enabled
                mpv_path = self.settings.get("mpv_path")
                mpv_args = [mpv_path, latest_file]
                if self.settings.get("mpv_fullscreen", False):
                    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "player", "scripts", "delayed-fullscreen.lua"))
                    mpv_args.append(f"--script={script_path}")
                if self.settings.get("mpv_volume") is not None:
                    mpv_args.append(f"--volume={self.settings.get("mpv_volume")}")
                if self.settings.get("mpv_screen") != "Default":
                    mpv_args.append(f"--screen={self.settings.get("mpv_screen")}")
                custom_args = self.settings.get("mpv_custom_args", "").strip()
                if custom_args:
                    mpv_args.extend(shlex.split(custom_args))

                if os.name == 'nt': # Windows
                    process = subprocess.Popen(mpv_args, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                else: # macOS, Linux
                    process = subprocess.Popen(mpv_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    error_message = stderr.decode().strip() if stderr else "Unknown MPV error."
                    messagebox.showerror("MPV Playback Error", f"MPV exited with an error:\n{error_message}")
            else: # Fallback to default system player
                if os.name == 'nt': # Windows
                    os.startfile(latest_file)
                elif os.name == 'posix': # macOS, Linux
                    subprocess.call(['open', latest_file] if sys.platform == 'darwin' else ['xdg-open', latest_file])
            self._set_status("Launched video player for Others.")
        except Exception as e:
            self._set_status(f"Error playing video: {e}")
            messagebox.showerror("Playback Error", f"Could not play video:\n{e}")

    def _worker_download(self, channel):
        """Worker function that runs off the main UI thread."""
        name = channel["name"]
        fmt = channel["date_format"]

        # Step 1: Find next Saturday's date or use selected date
        self._set_status(f"Finding video for {name}...")
        selected_date = self.channel_date_vars.get(name, tk.StringVar()).get()
        if selected_date and selected_date != "automat":
            try:
                date_obj = datetime.strptime(selected_date, "%d.%m.%Y").date()
                next_sat = date_obj.strftime(fmt)
            except Exception as e:
                self._set_status(f"Date parse error: {e}")
                return
        else:
            next_sat = get_next_saturday(date_format=fmt)

        # Step 2: Locate the video URL
        url = find_video_url(channel["url"], next_sat, date_format=fmt)
        if not url:
            self._set_status(f"No video found for {name} on {next_sat}.")
            self._send_notification("Video Not Found", f"No video found for {name} on {next_sat}.")
            return

        # Prepare channel-specific folder
        channel_folder = os.path.join(self.base_path, channel["folder"])
        os.makedirs(channel_folder, exist_ok=True)

        # Step 3: Check if that exact video is already downloaded
        numeric = next_sat.lower()
        date_obj = datetime.strptime(next_sat, fmt).date()
        romanian = format_romanian_date(date_obj).lower()

        existing = [
            f for f in os.listdir(channel_folder)
            if numeric in f.lower() or romanian in f.lower()
        ]
        if existing:
            existing_titles = ", ".join(existing)
            self._set_status(
                f"Video for {name} already exists: {existing_titles}"
            )
            return

        # Step 4: Delete previous (in channel folder) only if no custom date selected
        if not selected_date or selected_date == "automat":
            delete_old_videos(channel_folder, keep_old=self.settings.get("keep_old_videos", False))

        # Step 5: Download into channel folder
        quality_pref = self.channel_quality_vars.get(name, tk.StringVar()).get()
        self._set_status(f"Downloading from {name} ({quality_pref})...")
        try:
            download_video(url, channel_folder, quality_pref, protect=bool(selected_date and selected_date != "automat"))
            self._set_status(f"Download complete for {name}.")
            self._send_notification("Download Complete", f"Finished downloading video for {name}.")
        except Exception as e:
            self._set_status(f"Error downloading {name}.")
            self._send_notification("Download Error", f"Failed to download video for {name}.")
            messagebox.showerror(
                "Download Error",
                f"Failed to download {name}:\n{e}"
            )

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
            self.open_file_viewers[channel_folder].lift()
            self.open_file_viewers[channel_folder].focus_set()
        else:
            file_viewer_win = FileViewer(self, self.settings, channel["name"], channel_folder, self._on_file_viewer_close)
            file_viewer_win.transient(self)
            file_viewer_win.focus_set()
            self.open_file_viewers[channel_folder] = file_viewer_win

    def _on_file_viewer_close(self, folder_path):
        if folder_path in self.open_file_viewers:
            del self.open_file_viewers[folder_path]

    def _worker_play(self, channel):
        """Worker function to find and play the latest video."""
        channel_folder = os.path.join(self.base_path, channel["folder"])
        self._set_status(f"Searching for latest video in {channel['name']}...")

        if not os.path.exists(channel_folder):
            self._set_status(f"No videos downloaded for {channel['name']} yet.")
            return

        files = [os.path.join(channel_folder, f) for f in os.listdir(channel_folder)]
        if not files:
            self._set_status(f"No videos found for {channel['name']}.")
            return

        latest_file = max(files, key=os.path.getctime)

        try:
            self._set_status(f"Playing {os.path.basename(latest_file)}...")
            if self.settings.get("use_mpv", False) and self.settings.get("mpv_path"): # Use MPV if enabled
                mpv_path = self.settings.get("mpv_path")
                mpv_args = [mpv_path, latest_file]
                if self.settings.get("mpv_fullscreen", False):
                    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "player", "scripts", "delayed-fullscreen.lua"))
                    mpv_args.append(f"--script={script_path}")
                if self.settings.get("mpv_volume") is not None:
                    mpv_args.append(f"--volume={self.settings.get("mpv_volume")}")
                if self.settings.get("mpv_screen") != "Default":
                    mpv_args.append(f"--screen={self.settings.get("mpv_screen")}")
                custom_args = self.settings.get("mpv_custom_args", "").strip()
                if custom_args:
                    mpv_args.extend(shlex.split(custom_args))

                if os.name == 'nt': # Windows
                    process = subprocess.Popen(mpv_args, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                else: # macOS, Linux
                    process = subprocess.Popen(mpv_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    error_message = stderr.decode().strip() if stderr else "Unknown MPV error."
                    messagebox.showerror("MPV Playback Error", f"MPV exited with an error:\n{error_message}")
            else: # Fallback to default system player
                if os.name == 'nt': # Windows
                    os.startfile(latest_file)
                elif os.name == 'posix': # macOS, Linux
                    subprocess.call(['open', latest_file] if sys.platform == 'darwin' else ['xdg-open', latest_file])
            self._set_status(f"Launched video player for {channel['name']}.")
        except Exception as e:
            self._set_status(f"Error playing video: {e}")
            messagebox.showerror("Playback Error", f"Could not play video:\n{e}")

if __name__ == "__main__":
    app = YoutubeWeeklyGUI()
    app.mainloop()
    input("Press Enter to exit...") # Keep console open for debugging
    input("Press Enter to exit...") # Keep console open for debugging
    input("Press Enter to exit...") # Keep console open for debugging
    input("Press Enter to exit...") # Keep console open for debugging
    input("Press Enter to exit...") # Keep console open for debugging
    input("Press Enter to exit...") # Keep console open for debugging
    input("Press Enter to exit...") # Keep console open for debugging