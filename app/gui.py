import tkinter as tk
from tkinter import ttk, messagebox
from app.backend.downloader import find_video_url, download_video, get_next_saturday

class YoutubeWeeklyGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YoutubeWeekly Downloader")
        self.geometry("400x250")

        self.channels = [
            {
                "name": "DepartamentulIsprăvnicie",
                "url": "https://www.youtube.com/c/DepartamentulIsprăvnicie",
                "date_format": "%d.%m.%Y"
            },
            {
                "name": "ScoalaDeSabat",
                "url": "https://www.youtube.com/@ScoalaDeSabat",
                "date_format": "%d.%m.%Y"
            }
        ]

        ttk.Label(self, text="Download next Saturday's video for each channel").pack(pady=10)

        self.folder_path = "data/videos"

        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self, textvariable=self.status_var, foreground="black")
        self.status_label.pack(pady=5)

        for channel in self.channels:
            btn = ttk.Button(self, text=f"Download for {channel['name']}", command=lambda ch=channel: self.download_for_channel(ch))
            btn.pack(pady=5)

        ttk.Button(self, text="Quit", command=self.quit).pack(pady=10)

    def download_for_channel(self, channel):
        folder = self.folder_path

        self.status_var.set(f"Finding video for {channel['name']}...")
        self.update_idletasks()

        next_saturday = get_next_saturday(date_format=channel['date_format'])
        video_url = find_video_url(channel['url'], next_saturday, date_format=channel['date_format'])
        if not video_url:
            from datetime import datetime
            try:
                date_obj = datetime.strptime(next_saturday, channel['date_format'])
                display_date = date_obj.strftime(channel['date_format'])
            except Exception:
                display_date = next_saturday
            if channel['name'] == "DepartamentulIsprăvnicie":
                display_date = display_date.replace("-", ".")
            self.status_var.set(f"No video found for {channel['name']} on {display_date}.")
            return

        self.status_var.set(f"Downloading video from {channel['name']}...")
        self.update_idletasks()

        download_video(video_url, folder)
        self.status_var.set(f"Download complete for {channel['name']}.")

if __name__ == "__main__":
    app = YoutubeWeeklyGUI()
    app.mainloop()
