import threading
import tkinter as tk
from tkinter import ttk, messagebox

from app.backend.config import load_channels
from app.backend.downloader import find_video_url, download_video, get_next_saturday

class YoutubeWeeklyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YoutubeWeekly Downloader")
        self.geometry("400x300")

        # Fixed download folder
        self.folder_path = "data/videos"

        # Load channels configuration
        raw = load_channels()
        self.channels = [
            {
                "name": ch_data.get("name", key),
                "url": ch_data["url"],
                "date_format": ch_data.get("date_format", "%d.%m.%Y")
            }
            for key, ch_data in raw.items()
        ]

        ttk.Label(self, text="Download next Saturday's video for each channel").pack(pady=10)

        # Status label
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self, textvariable=self.status_var, foreground="blue")
        self.status_label.pack(pady=5)

        # One download button per channel
        for channel in self.channels:
            btn = ttk.Button(
                self,
                text=f"Download for {channel['name']}",
                command=lambda ch=channel: self.download_for_channel(ch)
            )
            btn.pack(pady=5, fill="x", padx=20)

        # Quit button
        ttk.Button(self, text="Quit", command=self.quit).pack(pady=15)

    def _set_status(self, text):
        """Thread-safe status update."""
        self.status_var.set(text)
        self.update_idletasks()

    def download_for_channel(self, channel):
        """Launch the download check in a background thread."""
        thread = threading.Thread(
            target=self._worker_download, args=(channel,), daemon=True
        )
        thread.start()

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

        # Step 3: Download the video
        self._set_status(f"Downloading from {name}...")
        try:
            download_video(url, self.folder_path)
            self._set_status(f"Download complete for {name}.")
        except Exception as e:
            self._set_status(f"Error downloading {name}.")
            messagebox.showerror("Download Error", f"Failed to download {name}:\n{e}")

if __name__ == "__main__":
    app = YoutubeWeeklyGUI()
    app.mainloop()
