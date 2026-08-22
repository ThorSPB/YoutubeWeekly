import os
import json
import time
import yt_dlp
import logging
from datetime import datetime, timedelta
from app.backend.config import load_settings, SETTINGS_FILE, settings_lock
from app.backend.progress import PROGRESS_PLAN_STATUS
from tkinter import messagebox


# Suffixes yt-dlp leaves behind while a download is still in flight. A ".part"
# for a 1080p video holds a *video-only* stream (audio is a separate download
# that gets merged afterwards), so a leftover one plays as picture with no
# sound. Never offer these as playable, and never let one satisfy an
# "is it already downloaded?" check.
PARTIAL_SUFFIXES = (".part", ".ytdl", ".temp")


def is_partial_download(filename):
    """True for a yt-dlp scratch file from a download that never finished."""
    return str(filename).lower().endswith(PARTIAL_SUFFIXES)


def list_playable_files(folder):
    """Filenames in `folder` that are finished downloads, safe to play or list."""
    try:
        names = os.listdir(folder)
    except OSError:
        return []
    return [
        f for f in names
        if not is_partial_download(f) and os.path.isfile(os.path.join(folder, f))
    ]


def purge_partial_downloads(folder):
    """Delete unfinished-download leftovers, returning the names removed.

    Called before a download so a previous failure can't block the retry (its
    filename still carries the Sabbath date the existence check looks for), and
    after a failure so nothing half-written is left lying around to be played.
    """
    removed = []
    try:
        names = os.listdir(folder)
    except OSError:
        return removed
    for name in names:
        if not is_partial_download(name):
            continue
        try:
            os.remove(os.path.join(folder, name))
            removed.append(name)
            logging.info(f"Removed unfinished download: {name}")
        except OSError as e:
            logging.warning(f"Could not remove unfinished download {name}: {e}")
    return removed


def folder_snapshot(folder):
    """Filenames currently in a folder, for diffing what a download produced."""
    try:
        return set(os.listdir(folder))
    except OSError:
        return set()


def newly_downloaded_file(folder, before):
    """The file a download just created, ignoring partials."""
    new = [f for f in folder_snapshot(folder) - before if not is_partial_download(f)]
    if not new:
        return None
    # Largest wins if yt-dlp left intermediate artifacts behind.
    return max(new, key=lambda f: os.path.getsize(os.path.join(folder, f)))


def build_download_plan(ydl, video_url):
    """Stream count and byte total for a pending download, or None if unknown.

    Lets a progress bar be weighted by real sizes instead of guessing. It
    matters because a 1080p download's audio stream is a small fraction of its
    video - giving each an equal share of the bar made it crawl and then leap.

    Best-effort by design: if any stream's size is missing we return None rather
    than a total that would make the bar lie, and the caller falls back to
    counting streams. Never raises - a failure here must not fail the download.
    """
    try:
        info = ydl.extract_info(video_url, download=False)
        if not info:
            return None
        streams = info.get("requested_formats") or [info]
        total = 0
        for fmt in streams:
            size = fmt.get("filesize") or fmt.get("filesize_approx")
            if not size:
                return None
            total += size
        if not total:
            return None
        return {"streams": len(streams), "total_bytes": total}
    except Exception as e:
        # A cosmetic progress bar is never worth failing a download over.
        logging.info(f"Could not size the download up front: {e}")
        return None


def load_protected_videos():
    with settings_lock:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("protected_videos", {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

def add_protected_video(channel_folder, title):
    with settings_lock:
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}

        protected = settings.setdefault("protected_videos", {})
        protected.setdefault(channel_folder, [])
        if title not in protected[channel_folder]:
            protected[channel_folder].append(title)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)

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


import re


def _normalize_date_in_text(text):
    """Replace any non-digit delimiters between date components with dots.

    Handles cases like '13 03.2026', '13,03,2026', '13 03 2026' -> '13.03.2026'
    """
    # Match date-like patterns: 1-2 digits, separator, 1-2 digits, separator, 4 digits
    return re.sub(r'(\d{1,2})[^\d]+(\d{1,2})[^\d]+(\d{4})', r'\1.\2.\3', text)


def _build_date_variants(date_obj):
    """Build all date string variants for matching (exact date + nearby days).

    Returns: dict mapping date_string -> offset_days (0 = exact match)
    """
    variants = {}
    for offset in [0, -1, 1]:
        d = date_obj + timedelta(days=offset)
        # Numeric format with dots
        numeric = f"{d.day:02d}.{d.month:02d}.{d.year}"
        # Also try without leading zeros
        numeric_no_pad = f"{d.day}.{d.month}.{d.year}"
        # Romanian format
        romanian = format_romanian_date(d).lower()

        variants[numeric.lower()] = offset
        variants[numeric_no_pad.lower()] = offset
        variants[romanian] = offset
    return variants


def find_video_url(channel_url, expected_date, date_format="%d.%m.%Y"):
    """Find a video URL matching the expected date.

    Returns: (url, match_info) tuple where match_info is:
        - None if no match found (url will also be None)
        - {"type": "exact", "title": ...} for exact date match
        - {"type": "fuzzy", "title": ..., "reason": ...} for nearby date or delimiter mismatch
    """

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
        return None, None

    # Build exact match strings
    formatted_numeric = expected_date_obj.strftime(date_format).lower()
    formatted_romanian = format_romanian_date(expected_date_obj).lower()
    exact_parts = {formatted_numeric, formatted_romanian}

    # Build fuzzy variants (±1 day, normalized delimiters)
    date_variants = _build_date_variants(expected_date_obj)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            start_time = time.time()
            info = ydl.extract_info(channel_url + "/videos", download=False)
            logging.debug(f"yt-dlp took {time.time() - start_time:.2f} seconds to extract info.")
            entries = info.get("entries", [])

            best_fuzzy = None

            for entry in entries:
                title = entry.get("title", "")
                title_lower = title.lower()

                if "diaspora" in title_lower:
                    continue

                url = f"https://www.youtube.com/watch?v={entry['id']}"

                # 1. Exact match (current behavior)
                if any(part in title_lower for part in exact_parts):
                    return url, {"type": "exact", "title": title}

                # 2. Fuzzy match: normalize delimiters in title, then check variants
                normalized_title = _normalize_date_in_text(title_lower)
                for variant, offset in date_variants.items():
                    if variant in title_lower or variant in normalized_title:
                        reason = []
                        if offset != 0:
                            reason.append(f"date is off by {abs(offset)} day ({'before' if offset < 0 else 'after'} Sabbath)")
                        if variant in normalized_title and variant not in title_lower:
                            reason.append("delimiter mismatch in date format")
                        if offset == 0 and variant not in exact_parts and not reason:
                            reason.append("non-standard date format")
                        if reason:
                            best_fuzzy = (url, {
                                "type": "fuzzy",
                                "title": title,
                                "reason": "; ".join(reason),
                            })
                            break
                if best_fuzzy:
                    break

            if best_fuzzy:
                return best_fuzzy

        except Exception as e:
            logging.error(f"Failed to fetch video list: {e}")
            return None, None

    return None, None

def delete_old_videos(video_folder, keep_old, keep=None):
    """Drop previous Sabbaths' videos, unless the user keeps old ones.

    `keep` names files that must survive - normally the file the current
    download just produced. Without it, re-downloading a video that is already
    on disk would delete the very file it just confirmed.
    """
    if keep_old:
        # keep_old is True: keep all videos.
        return
    protected = {k for k in (keep or []) if k}
    for filename in os.listdir(video_folder):
        if filename.endswith(".mp4") and filename not in protected:
            os.remove(os.path.join(video_folder, filename))
            logging.info(f"Deleted old video: {filename}")

def download_video(video_url, video_folder, quality_pref="1080p", protect=False, progress_hook=None):
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
    quality_formats = {
        "max":   'bestvideo+bestaudio/best',
        "4k":    'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
        "2k":    'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
        "1080p": 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        "720p":  'bestvideo[height<=720]+bestaudio/best[height<=720]',
        "480p":  'bestvideo[height<=480]+bestaudio/best[height<=480]',
    }

    if quality_pref == "mp3":
        ydl_format = 'bestaudio/best'
        merge_format = 'mp3'
    elif quality_pref in quality_formats:
        ydl_format = quality_formats[quality_pref]
        merge_format = 'mp4'
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
        'ffmpeg_location': ffmpeg_path,
        'progress_hooks': [progress_hook] if progress_hook else []
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
            if progress_hook:
                # Tell the UI how much is coming before any bytes move, so its
                # bar is weighted by real sizes rather than stream count.
                plan = build_download_plan(ydl, video_url) or {}
                try:
                    progress_hook({
                        "status": PROGRESS_PLAN_STATUS,
                        "streams": plan.get("streams"),
                        "total_bytes": plan.get("total_bytes"),
                    })
                except Exception:
                    pass
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
        except yt_dlp.utils.DownloadError as e:
            error_message = str(e)
            logging.error(f"Download failed: {error_message}")
            # A partly-transferred video-only stream is worse than nothing: it
            # is offered as playable (picture, no sound) and its name blocks
            # the retry. Take it with us.
            purge_partial_downloads(video_folder)
            return error_message
        except Exception as e:
            error_message = str(e)
            logging.error(f"An unexpected error occurred during download: {error_message}")
            purge_partial_downloads(video_folder)
            return error_message
    return None # Return None on successful download

def get_recent_sabbaths(n=30, date_format="%d.%m.%Y"):
    """Return the last `n` Sabbath (Saturday) dates formatted."""
    today = datetime.today()
    sabbaths = []
    for i in range(n):
        # Step back 7 days at a time from today or last Saturday
        ref_day = today - timedelta(days=(today.weekday() - 5) % 7 + i * 7)
        sabbaths.append(ref_day.strftime(date_format))
    return sabbaths