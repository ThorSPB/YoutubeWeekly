def load_protected_videos():
    settings_path = os.path.join("config", "settings.json")
    with open(settings_path, "r", encoding="utf-8") as f:
        return json.load(f).get("protected_videos", {})

def add_protected_video(channel_folder, title):
    settings_path = os.path.join("config", "settings.json")
    with open(settings_path, "r", encoding="utf-8") as f:
        settings = json.load(f)
    protected = settings.setdefault("protected_videos", {})
    protected.setdefault(channel_folder, [])
    if title not in protected[channel_folder]:
        protected[channel_folder].append(title)
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
import os
import json
import time
import yt_dlp
import logging
from datetime import datetime, timedelta
from app.backend.config import load_settings
from tkinter import messagebox

def get_next_saturday(date_format="%d.%m.%Y"):
    today = datetime.today()
    weekday = today.weekday()
    if weekday < 5:  # Monday to Friday
        days_ahead = 5 - weekday
    elif weekday == 5:  # Saturday
        days_ahead = 0
    else:  # Sunday
        days_ahead = 6
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
        'flat': True,
    }

    try:
        expected_date_obj = datetime.strptime(expected_date, date_format).date()
    except Exception as e:
        logging.error(f"Expected date parsing error: {e}")
        return None

    # Build both possible matches
    formatted_numeric  = expected_date_obj.strftime(date_format).lower()
    formatted_romanian = format_romanian_date(expected_date_obj).lower()
    expected_title_parts = {formatted_numeric, formatted_romanian}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            start_time = time.time()
            info = ydl.extract_info(channel_url + "/videos", download=False)
            print(f"[DEBUG] yt-dlp took {time.time() - start_time:.2f} seconds to extract info.")
            entries = info.get("entries", [])

            for entry in entries[:]:
                title = entry.get("title", "").lower()
                # match if either format appears, and skip diaspora
                if any(part in title for part in expected_title_parts) and "diaspora" not in title:
                    return f"https://www.youtube.com/watch?v={entry['id']}"
        except Exception as e:
            logging.error(f"Failed to fetch video list: {e}")
            return None

def delete_old_videos(video_folder, keep_old):
    if not keep_old:
        # If keep_old is False, delete all .mp4 files regardless of protection status
        for filename in os.listdir(video_folder):
            if filename.endswith(".mp4"):
                os.remove(os.path.join(video_folder, filename))
                logging.info(f"Deleted old video: {filename}")
        # If keep_old is True, do nothing (i.e., keep all videos)

def download_video(video_url, video_folder, quality_pref="1080p", protect=False):
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

    # Determine format options based on quality_pref
    if quality_pref == "1080p":
        ydl_format = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        merge_format = 'mp4'
    elif quality_pref == "720p":
        ydl_format = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
        merge_format = 'mp4'
    elif quality_pref == "480p":
        ydl_format = 'bestvideo[height<=480]+bestaudio/best[height<=480]'
        merge_format = 'mp4'
    elif quality_pref == "mp3":
        ydl_format = 'bestaudio/best'
        merge_format = 'mp3'
    else:
        ydl_format = 'bestvideo+bestaudio/best'
        merge_format = 'mp4'

    settings, _ = load_settings()
    ffmpeg_path = settings.get("ffmpeg_path")

    ydl_opts = {
        'outtmpl': os.path.join(video_folder, '%(title)s.%(ext)s'),
        'quiet': False,
        'format': ydl_format,
        'noplaylist': True,
        'merge_output_format': merge_format,
        'postprocessors': [],
        'ffmpeg_location': ffmpeg_path
    }

    if quality_pref == "mp3":
        ydl_opts['postprocessors'].append({
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            logging.info(f"Downloading: {video_url} with quality {quality_pref}")
            ydl.download([video_url])
            logging.info("Download complete.")
            if protect:
                # Get video info to accurately identify the downloaded file
                info = ydl.extract_info(video_url, download=False)
                if info:
                    # Construct the expected filename based on yt-dlp's output template
                    # This assumes the default outtmpl: '%(title)s.%(ext)s'
                    video_filename = f"{info.get('title')}.{info.get('ext')}"
                    add_protected_video(os.path.basename(video_folder), video_filename)
        except Exception as e:
            logging.error(f"Download failed: {e}")
            messagebox.showerror("Download Error", f"Failed to download video:\n{e}")

def get_recent_sabbaths(n=30, date_format="%d.%m.%Y"):
    """Return the last `n` Sabbath (Saturday) dates formatted."""
    today = datetime.today()
    sabbaths = []
    for i in range(n):
        # Step back 7 days at a time from today or last Saturday
        ref_day = today - timedelta(days=(today.weekday() - 5) % 7 + i * 7)
        sabbaths.append(ref_day.strftime(date_format))
    return sabbaths