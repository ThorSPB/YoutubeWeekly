import os
import json
import yt_dlp
import logging
from datetime import datetime, timedelta

def get_next_saturday():
    today = datetime.today()
    days_ahead = 5 - today.weekday()  # 5 = Saturday
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def find_video_url(channel_url, expected_date):
    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url + "/videos", download=False)
            entries = info.get("entries", [])

            for entry in entries:
                if expected_date in entry.get("title", ""):
                    return f"https://www.youtube.com/watch?v={entry['id']}"
        except Exception as e:
            logging.error(f"Failed to fetch video list: {e}")
            return None

    return None


def delete_old_videos(video_folder, keep_old):
    if not keep_old:
        for filename in os.listdir(video_folder):
            if filename.endswith(".mp4"):
                os.remove(os.path.join(video_folder, filename))
                logging.info(f"Deleted old video: {filename}")


def download_video(video_url, video_folder):
    os.makedirs(video_folder, exist_ok=True)

    ydl_opts = {
        'outtmpl': os.path.join(video_folder, '%(title)s.%(ext)s'),
        'quiet': False,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            logging.info(f"Downloading: {video_url}")
            ydl.download([video_url])
            logging.info("Download complete.")
        except Exception as e:
            logging.error(f"Download failed: {e}")
