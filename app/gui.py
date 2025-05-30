import threading
import tkinter as tk
from tkinter import ttk, messagebox
import os

from app.backend.config import load_channels
from app.backend.downloader import find_video_url, download_video, get_next_saturday, delete_old_videos, format_romanian_date, get_recent_sabbaths
from datetime import datetime

class YoutubeWeeklyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configure(bg="#2b2b2b")

        self.quality_options = ["1080p", "720p", "480p", "mp3"]
        self.channel_quality_vars = {}
        self.channel_date_vars = {}

        style = ttk.Style()
        style.theme_use("default")
        style.configure("TButton", background="#444444", foreground="white")
        style.map("TButton", background=[("active", "#555555")])
        style.configure("Dark.TFrame", background="#2b2b2b")

        self.title("YoutubeWeekly Downloader")
        self.geometry("455x260")
        self.base_path = "data/videos"

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

        # Header label
        tk.Label(
            self,
            text="Download next Saturday's video for each channel",
            font=(None, 16, 'bold'),
            fg="white",
            bg="#2b2b2b"
        ).pack(pady=(5, 10))

        # Status label with wrapping
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            self,
            textvariable=self.status_var,
            fg="#ffffff",
            bg="#2b2b2b",
            anchor="w",
            justify="left",
            wraplength=self.winfo_width()
        )
        self.status_label.pack(pady=(5, 15), padx=20, fill="x")

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.configure(style="Dark.TFrame")
        btn_frame.pack(pady=(0, 15), padx=20, fill="x")

        # One download button + quality selector per channel
        for channel in self.channels:
            row = ttk.Frame(btn_frame)
            row.pack(pady=3, anchor="w")

            var = tk.StringVar(value="1080p")
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

        # Others link entry and button frame
        others_frame = ttk.Frame(self)
        others_frame.configure(style="Dark.TFrame")
        others_frame.pack(pady=(0, 15), padx=20, anchor="w")

        self.others_quality_var = tk.StringVar(value="1080p")
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

        # Quit button
        ttk.Button(self, text="Quit", command=self.quit, width=10).pack(pady=(0, 15))

        self.resizable(False, False)

        self.bind("<Configure>", self._on_resize)

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

    def _worker_download_others(self, link):
        folder = os.path.join(self.base_path, "other")
        try:
            download_video(link, folder, self.others_quality_var.get())
            self._set_status("Download complete.")
        except Exception as e:
            self._set_status("Error downloading.")
            messagebox.showerror(
                "Download Error",
                f"Failed to download video:\n{e}"
            )

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
            delete_old_videos(channel_folder, keep_old=False)

        # Step 5: Download into channel folder
        quality_pref = self.channel_quality_vars.get(name, tk.StringVar()).get()
        self._set_status(f"Downloading from {name} ({quality_pref})...")
        try:
            download_video(url, channel_folder, quality_pref, protect=bool(selected_date and selected_date != "automat"))
            self._set_status(f"Download complete for {name}.")
        except Exception as e:
            self._set_status(f"Error downloading {name}.")
            messagebox.showerror(
                "Download Error",
                f"Failed to download {name}:\n{e}"
            )

if __name__ == "__main__":
    app = YoutubeWeeklyGUI()
    app.mainloop()
