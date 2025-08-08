import json
import os
from datetime import datetime, timedelta

from app.backend.config import load_settings, save_settings, load_channels, CONFIG_DIR
from app.backend.downloader import find_video_url, download_video, get_next_saturday, format_romanian_date, delete_old_videos

AUTO_DOWNLOAD_LOG_FILE = os.path.join(CONFIG_DIR, "auto_download_log.json")

def load_auto_download_log():
    try:
        with open(AUTO_DOWNLOAD_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_auto_download_log(log_data):
    with open(AUTO_DOWNLOAD_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)

def get_current_sabbath_date():
    today = datetime.now().date()
    # Calculate days until next Saturday (Saturday is weekday 5)
    days_until_saturday = (5 - today.weekday() + 7) % 7
    if days_until_saturday == 0: # If today is Saturday
        return today.strftime("%Y-%m-%d")
    else:
        # If today is not Saturday, get the date of the upcoming Saturday
        upcoming_saturday = today + timedelta(days=days_until_saturday)
        return upcoming_saturday.strftime("%Y-%m-%d")

def run_automatic_checks(initial_settings, channels, send_notification_callback, progress_hook=None):
    settings, _ = load_settings() # Reload settings to get the latest values
    if not settings.get("enable_auto_download", False):
        return

    current_sabbath_date = get_current_sabbath_date()
    auto_download_log = load_auto_download_log()

    # Clean up old logs and initialize for new Sabbath if necessary
    if current_sabbath_date not in auto_download_log:
        auto_download_log = {current_sabbath_date: {}}
    else:
        # Remove logs for past Sabbaths, keeping only the current one
        temp_log = {current_sabbath_date: auto_download_log[current_sabbath_date]}
        auto_download_log = temp_log

    # Initialize channels for the current Sabbath if they are not present
    for channel_data in channels:
        channel_key = channel_data.get("folder", channel_data["name"])
        if channel_key != "others" and channel_key not in auto_download_log[current_sabbath_date]:
            auto_download_log[current_sabbath_date][channel_key] = "pending"

    today = datetime.now().date()
    day_of_week = today.weekday() # Monday is 0, Sunday is 6

    # Perform checks only on Friday (4) and Saturday (5)
    if day_of_week == 4 or day_of_week == 5:
        channels_to_check = [ch for ch in channels if ch.get("folder", ch["name"]) != "others"]
        if not channels_to_check:
            return

        initial_message = "Starting automatic download check for channels: " + ", ".join([ch["name"] for ch in channels_to_check])
        send_notification_callback("Auto Download Initiated", initial_message)

        download_results = {} # To store results for the final summary

        for channel_data in channels_to_check:
            channel_key = channel_data.get("folder", channel_data["name"])
            channel_name = channel_data.get("name", channel_key)
            channel_url = channel_data["url"]
            date_format = channel_data.get("date_format", "%d.%m.%Y")
            folder = os.path.join(settings.get("video_folder", "data/videos"), channel_data.get("folder", channel_key))

            # Only attempt download if status is not 'downloaded'
            if auto_download_log[current_sabbath_date].get(channel_key) != "downloaded":
                send_notification_callback("Auto Download", f"Checking for {channel_name} video...")
                
                # Use the Sabbath date for finding the video
                expected_date_str = datetime.strptime(current_sabbath_date, "%Y-%m-%d").strftime(date_format)
                video_url = find_video_url(channel_url, expected_date_str, date_format=date_format)

                if video_url:
                    try:
                        # Ensure folder exists before downloading
                        os.makedirs(folder, exist_ok=True)
                        # Delete old videos before downloading, based on the setting
                        delete_old_videos(folder, settings.get("keep_old_videos", False))
                        download_video(video_url, folder, settings.get("default_quality", "1080p"), protect=settings.get("keep_old_videos", False), progress_hook=progress_hook)
                        auto_download_log[current_sabbath_date][channel_key] = "downloaded"
                        download_results[channel_name] = "Downloaded"
                        send_notification_callback("Auto Download Success", f"Downloaded {channel_name} video.")
                    except Exception as e:
                        auto_download_log[current_sabbath_date][channel_key] = "error"
                        download_results[channel_name] = f"Error: {e}"
                        send_notification_callback("Auto Download Error", f"Failed to download {channel_name}: {e}")
                else:
                    auto_download_log[current_sabbath_date][channel_key] = "not_found"
                    download_results[channel_name] = "Not Found"
                    send_notification_callback("Auto Download Info", f"No video found for {channel_name}.")
            else:
                download_results[channel_name] = "Already Downloaded"

        # Final summary notification
        summary_message = "Automatic download summary:\n"
        all_successful = True
        any_successful = False
        for channel, status in download_results.items():
            summary_message += f"- {channel}: {status}\n"
            if "Error" in status or "Not Found" in status:
                all_successful = False
            elif status == "Downloaded":
                any_successful = True
        
        if all_successful and any_successful:
            send_notification_callback("Auto Download Complete", "All selected videos downloaded successfully!")
        elif any_successful:
            send_notification_callback("Auto Download Partial Success", "Some videos downloaded, others had issues.")
        else:
            send_notification_callback("Auto Download Failed", "No videos were downloaded successfully.")

    # Save the updated log and settings
    save_auto_download_log(auto_download_log)
    settings["last_sabbath_checked"] = current_sabbath_date
    save_settings(settings)
