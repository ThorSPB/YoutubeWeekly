import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import shlex
import time
from plyer import notification
import json
from PIL import Image
import pystray

from app.backend.config import load_channels, load_settings, save_settings
from app.backend.downloader import find_video_url, download_video, get_next_saturday, delete_old_videos, format_romanian_date, get_recent_sabbaths
from datetime import datetime
from app.frontend.settings_window import SettingsWindow
from app.frontend.file_viewer import FileViewer
from app.backend.auto_downloader import run_automatic_checks
from app.backend.updater import check_for_updates

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
        self.iconbitmap(resource_path("assets/icon4.ico"))
        self.configure(bg="#2b2b2b")

        self.settings, self.startup_warnings = load_settings()

        if self.startup_warnings:
            messagebox.showwarning("Configuration Warnings", "\n".join(self.startup_warnings))

        self.quality_options = ["1080p", "720p", "480p", "mp3"]
        self.channel_quality_vars = {}
        self.channel_date_vars = {}
        self.open_file_viewers = {}
        self.download_stage = 0 # 0: idle, 1: video, 2: audio
        self.last_progress_value = 0
        self.downloading_channels = set()

        style = ttk.Style()
        style.theme_use("default")
        # Standardize font across OS
        default_font = ("Segoe UI", 10) if os.name == "nt" else ("Helvetica Neue", 11)
        style.configure(".", font=default_font)
        style.configure("TButton", background="#444444", foreground="white")
        style.map("TButton", background=[("active", "#555555")])
        style.configure("Dark.TFrame", background="#2b2b2b")

        self.title("YoutubeWeekly Downloader")
        saved_geometry = self.settings.get("main_window_geometry")
        if saved_geometry:
            self.geometry(saved_geometry)
        else:
            self.geometry("515x275")  # Default size
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

        # Run automatic checks in a separate thread
        threading.Thread(
            target=run_automatic_checks,
            args=(self.settings, self.channels, self._send_notification, self.progress_hook),
            daemon=True
        ).start()

        # Check for updates in a separate thread
        threading.Thread(target=self._check_for_updates_thread, daemon=True).start()

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

        # Main content frame for channel buttons and others section
        content_frame = ttk.Frame(self, style="Dark.TFrame")
        content_frame.pack(pady=(0, 15), padx=20, fill="x", expand=True)

        # One download button + quality selector per channel
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
        others_frame = ttk.Frame(content_frame)
        others_frame.configure(style="Dark.TFrame")
        others_frame.pack(pady=(10, 0), anchor="w", fill="x")

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
            width=27,
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
        ttk.Button(self, text="Quit", command=self.on_closing, width=10).pack(pady=(15, 15))

        # Progress bar
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=300, mode="determinate")


        self.resizable(False, False)

        self.bind("<Configure>", self._on_resize)

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
        image = Image.open(resource_path("assets/icon4.ico"))
        menu = (pystray.MenuItem('Show', self.show_from_tray, default=True),
                pystray.MenuItem('Quit', self.quit_application))
        self.tray_icon = pystray.Icon("YoutubeWeekly", image, "YoutubeWeekly Downloader", menu)
        self.tray_icon.run_detached()

    def show_from_tray(self, icon, item):
        self.tray_icon.stop()
        self.deiconify()
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)
        self.focus_force()

    def quit_application(self, icon=None, item=None):
        # Ensure operations are performed on the main Tkinter thread
        self.after(0, self._perform_quit)

    def _perform_quit(self):
        if hasattr(self, 'tray_icon') and self.tray_icon.visible:
            self.tray_icon.stop()
        self.destroy()

    def open_settings(self):
        settings_win = SettingsWindow(self, self.settings)
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
        channel_name = channel["name"]
        if channel_name in self.downloading_channels:
            self._set_status(f"A download for {channel_name} is already in progress.")
            return

        self.downloading_channels.add(channel_name)
        self.download_stage = 1 # Reset for new download
        self.last_progress_value = 0
        try:
            threading.Thread(
                target=self._worker_download,
                args=(channel,),
                daemon=True
            ).start()
        finally:
            # This will run immediately after the thread starts, maybe not what we want.
            # self.downloading_channels.remove(channel_name)
            pass

    def download_others(self):
        """Download video from the link in the others entry to data/videos/other."""
        if "others" in self.downloading_channels:
            self._set_status("A download for 'others' is already in progress.")
            return

        self.downloading_channels.add("others")
        self.download_stage = 1 # Reset for new download
        self.last_progress_value = 0
        link = self.others_link_var.get().strip()
        if not link:
            self._set_status("Please enter a YouTube link.")
            self.downloading_channels.remove("others")
            return

        self._set_status("Starting download...")
        try:
            threading.Thread(
                target=self._worker_download_others,
                args=(link,),
                daemon=True
            ).start()
        except Exception as e:
            self._set_status(f"Error starting download thread: {e}")
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
            file_viewer_win = FileViewer(self, self.settings, "Others", other_folder, self._on_file_viewer_close)
            self.open_file_viewers[other_folder] = file_viewer_win

    def _worker_download_others(self, link):
        folder = os.path.join(self.base_path, "other")
        try:
            error = download_video(link, folder, self.others_quality_var.get(), progress_hook=self.progress_hook)
            if error:
                self._set_status(f"Error downloading: {error}")
                self._send_notification("Download Error", f"Failed to download video from link: {link}\n{error}")
                messagebox.showerror(
                    "Download Error",
                    f"Failed to download video:\n{error}"
                )
            else:
                self._set_status("Download complete.")
                self._send_notification("Download Complete", f"Finished downloading video from link: {link}")
        except Exception as e:
            self._set_status(f"Error downloading: {e}")
            self._send_notification("Download Error", f"Failed to download video from link: {link}\n{e}")
            messagebox.showerror(
                "Download Error",
                f"Failed to download video:\n{e}"
            )
        finally:
            if "others" in self.downloading_channels:
                self.downloading_channels.remove("others")

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
                mpv_args = [f'"{mpv_path}"', f'"{latest_file}"']
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
                    command = ' '.join(mpv_args)
                    process = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
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
            self._set_status(f"Launched video player for Others.")
        except Exception as e:
            self._set_status(f"Error playing video: {e}")
            messagebox.showerror("Playback Error", f"Could not play video:\n{e}")

    def _worker_download(self, channel):
        """Worker function that runs off the main UI thread."""
        name = channel["name"]
        try:
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
                error = download_video(url, channel_folder, quality_pref, protect=self.settings.get("keep_old_videos", False), progress_hook=self.progress_hook)
                if error:
                    self._set_status(f"Error downloading {name}: {error}")
                    self._send_notification("Download Error", f"Failed to download video for {name}: {error}")
                    messagebox.showerror(
                        "Download Error",
                        f"Failed to download {name}:\n{error}"
                    )
                else:
                    self._send_notification("Download Complete", f"Finished downloading video for {name}.")
            except Exception as e:
                self._set_status(f"Error downloading {name}: {e}")
                self._send_notification("Download Error", f"Failed to download video for {name}: {e}")
                messagebox.showerror(
                    "Download Error",
                    f"Failed to download {name}:\n{e}"
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
                mpv_args = [f'"{mpv_path}"', f'"{latest_file}"']
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
                    command = ' '.join(mpv_args)
                    process = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
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

    def open_folder_in_explorer(self, folder_path):
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            self.progress_bar.pack(pady=(0, 10), padx=20, fill="x")
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
            if total_bytes:
                percent = (d['downloaded_bytes'] / total_bytes) * 100
                unified_percent = 0
                if self.download_stage == 1: # Video part (0-50%)
                    unified_percent = percent / 2
                elif self.download_stage == 2: # Audio part (50-100%)
                    unified_percent = 50 + (percent / 2)
                
                # Ratchet logic: only update if progress has increased
                if unified_percent > self.last_progress_value:
                    self.last_progress_value = unified_percent
                    self.progress_bar['value'] = unified_percent
                    self._set_status(f"Downloading... {unified_percent:.1f}%")
                    self.update_idletasks()
                    time.sleep(0.1)

        elif d['status'] == 'finished':
            if self.download_stage == 1:
                self.download_stage = 2 # Move to audio stage
                # Ensure the bar hits 50% exactly
                if self.last_progress_value < 50:
                    self.last_progress_value = 50
                    self.progress_bar['value'] = 50
                    self._set_status(f"Downloading... 50.0%")
                    self.update_idletasks()
            else:
                # Ensure the bar hits 100% exactly
                self.progress_bar['value'] = 100
                self._set_status("Download complete.")
                self.update_idletasks()
                time.sleep(0.5) # Give user a moment to see "complete"
                self.progress_bar.pack_forget()
                self.download_stage = 0 # Reset to idle
                self.last_progress_value = 0

    def _check_for_updates_thread(self):
        is_new_version, latest_version, download_url = check_for_updates()
        if is_new_version:
            messagebox.showinfo(
                "Update Available",
                f"A new version ({latest_version}) is available!\n\nDownload it from: {download_url}"
            )

if __name__ == "__main__":
    import socket

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
            messagebox.showerror("Error", "Could not connect to the running instance.")
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
