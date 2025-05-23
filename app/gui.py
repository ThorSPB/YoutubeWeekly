import threading
import tkinter as tk
from tkinter import ttk, messagebox
import os

from app.backend.config import load_channels
from app.backend.downloader import find_video_url, download_video, get_next_saturday, delete_old_videos, format_romanian_date
from datetime import datetime

class YoutubeWeeklyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YoutubeWeekly Downloader")
        # Compact initial size, but allow vertical expansion for wrapped text
        self.geometry("450x250")
        # Fixed download base folder
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

        # Header label
        ttk.Label(
            self,
            text="Download next Saturday's video for each channel",
            font=(None, 12, 'bold')
        ).pack(pady=(15, 10))

        # Status label with wrapping
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(
            self,
            textvariable=self.status_var,
            foreground="blue",
            wraplength=400,
            justify="left"
        )
        self.status_label.pack(pady=(5, 15), padx=20, fill="x")

        # Buttons frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=(0, 15), padx=20, fill="x")

        # One download button per channel
        for channel in self.channels:
            btn = ttk.Button(
                btn_frame,
                text=f"Download for {channel['name']}",
                command=lambda ch=channel: self.download_for_channel(ch),
                width=40             
            )
            btn.pack(pady=5)

        # Quit button
        ttk.Button(self, text="Quit", command=self.quit, width=30).pack(pady=(0, 15))

        self.resizable(True, True)

    def _set_status(self, text):
        """Thread-safe status update."""
        self.status_var.set(text)
        self.update_idletasks()

    def download_for_channel(self, channel):
        """Launch the download check in a background thread."""
        threading.Thread(
            target=self._worker_download,
            args=(channel,),
            daemon=True
        ).start()

    def _worker_download(self, channel):
        """Worker function that runs off the main UI thread."""
        name = channel["name"]
        fmt = channel["date_format"]

        # Step 1: Find next Saturday's date
        self._set_status(f"Finding video for {name}...")
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

        # Step 4: Delete previous (in channel folder)
        delete_old_videos(channel_folder, keep_old=False)

        # Step 5: Download into channel folder
        self._set_status(f"Downloading from {name}...")
        try:
            download_video(url, channel_folder)
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
