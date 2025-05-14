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


def find_video_url(channel_url, expected_date, date_format="%Y-%m-%d"):
    import re
    from datetime import datetime

    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': True,
        'nocheckcertificate': True,
    }

    def parse_date_from_title(title):
        # Try to find a date in the title matching the date_format
        try:
            # Extract date string based on format
            if date_format == "%Y-%m-%d":
                # Look for YYYY-MM-DD pattern
                match = re.search(r"\d{4}-\d{2}-\d{2}", title)
            elif date_format == "%d.%m.%Y":
                # Look for DD.MM.YYYY pattern
                match = re.search(r"\d{2}\.\d{2}\.\d{4}", title)
            else:
                match = None

            if match:
                date_str = match.group(0)
                return datetime.strptime(date_str, date_format).date()
        except Exception as e:
            logging.error(f"Date parsing error: {e}")
        return None

    expected_date_obj = None
    try:
        expected_date_obj = datetime.strptime(expected_date, date_format).date()
    except Exception as e:
        logging.error(f"Expected date parsing error: {e}")
        return None

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url + "/videos", download=False)
            entries = info.get("entries", [])

            for entry in entries:
                title = entry.get("title", "")
                video_date = parse_date_from_title(title)
                if video_date == expected_date_obj:
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
    if not video_folder:
        logging.error("Video folder path is empty or invalid.")
        return

    # Check if video already exists in folder by title (simplified check)
    video_title = video_url.split("v=")[-1]
    existing_files = os.listdir(video_folder) if os.path.exists(video_folder) else []
    for file in existing_files:
        if video_title in file:
            logging.info(f"Video already exists: {file}")
            return

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
