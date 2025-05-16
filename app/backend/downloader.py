import os
import json
import yt_dlp
import logging
from datetime import datetime, timedelta

def get_next_saturday(date_format="%d.%m.%Y"):
    today = datetime.today()
    days_ahead = 5 - today.weekday()  # 5 = Saturday
    if days_ahead <= 0:
        days_ahead += 7
    return (today + timedelta(days=days_ahead)).strftime(date_format)



def format_romanian_date(date_obj):
    months = {
        1: "ianuarie", 2: "februarie", 3: "martie", 4: "aprilie", 5: "mai", 6: "iunie",
        7: "iulie", 8: "august", 9: "septembrie", 10: "octombrie", 11: "noiembrie", 12: "decembrie"
    }
    return f"{date_obj.day} {months[date_obj.month]} {date_obj.year}"


def find_video_url(channel_url, expected_date, date_format="%d.%m.%Y"):
    from datetime import datetime

    ydl_opts = {
        'quiet': True,
        'extract_flat': 'in_playlist',
        'force_generic_extractor': True,
        'nocheckcertificate': True,
    }

    try:
        expected_date_obj = datetime.strptime(expected_date, date_format).date()
    except Exception as e:
        logging.error(f"Expected date parsing error: {e}")
        return None

    expected_title_part = format_romanian_date(expected_date_obj).lower()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(channel_url + "/videos", download=False)
            entries = info.get("entries", [])

            for entry in entries:
                title = entry.get("title", "").lower()
                if expected_title_part in title and "diaspora" not in title:
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
