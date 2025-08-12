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

def run_automatic_checks(initial_settings, channels, send_notification_callback, progress_hook=None, show_window_callback=None):
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

    # Pre-check: Verify existence of downloaded files
    for channel_data in channels:
        channel_key = channel_data.get("folder", channel_data["name"])
        if channel_key != "others" and auto_download_log.get(current_sabbath_date, {}).get(channel_key) == "downloaded":
            channel_folder = os.path.join(settings.get("video_folder", "data/videos"), channel_data.get("folder", channel_key))
            date_format = channel_data.get("date_format", "%d.%m.%Y")
            expected_date_str = datetime.strptime(current_sabbath_date, "%Y-%m-%d").strftime(date_format)

            numeric = expected_date_str.lower()
            romanian = format_romanian_date(datetime.strptime(expected_date_str, date_format)).lower()

            # Check if the folder exists and contains a file matching the date
            found_file = False
            if os.path.exists(channel_folder):
                for f in os.listdir(channel_folder):
                    if numeric in f.lower() or romanian in f.lower():
                        found_file = True
                        break
            
            if not found_file:
                auto_download_log[current_sabbath_date][channel_key] = "pending"

    today = datetime.now().date()
    day_of_week = today.weekday() # Monday is 0, Sunday is 6

    # Perform checks only on Friday (4) and Saturday (5)
    if day_of_week == 1 or day_of_week == 2:
        channels_to_process = [
            ch for ch in channels
            if ch.get("folder", ch["name"]) != "others" and
               auto_download_log.get(current_sabbath_date, {}).get(ch.get("folder", ch["name"])) != "downloaded"
        ]

        if not channels_to_process:
            return

        initial_message = "Starting automatic download for: " + ", ".join([ch["name"] for ch in channels_to_process])
        send_notification_callback("Auto Download Started", initial_message)

        download_results = {}

        for channel_data in channels_to_process:
            channel_key = channel_data.get("folder", channel_data["name"])
            channel_name = channel_data.get("name", channel_key)
            channel_url = channel_data["url"]
            date_format = channel_data.get("date_format", "%d.%m.%Y")
            folder = os.path.join(settings.get("video_folder", "data/videos"), channel_data.get("folder", channel_key))

            expected_date_str = datetime.strptime(current_sabbath_date, "%Y-%m-%d").strftime(date_format)
            video_url = find_video_url(channel_url, expected_date_str, date_format=date_format)

            if video_url:
                try:
                    # IMPORTANT: Reset GUI download state for progress tracking
                    if progress_hook and hasattr(progress_hook, '__self__'):
                        gui_instance = progress_hook.__self__
                        # Schedule the reset on the main UI thread
                        gui_instance.after(0, lambda: setattr(gui_instance, 'download_stage', 1))
                        gui_instance.after(0, lambda: setattr(gui_instance, 'last_progress_value', 0))
                        # Update status to show which channel is being downloaded
                        gui_instance.after(0, lambda ch=channel_name: gui_instance._set_status(f"Auto downloading {ch}..."))
                    
                    os.makedirs(folder, exist_ok=True)
                    delete_old_videos(folder, settings.get("keep_old_videos", False))
                    quality = settings.get("default_quality", "1080p")
                    
                    # Call download_video with progress_hook
                    error = download_video(video_url, folder, quality, protect=settings.get("keep_old_videos", False), progress_hook=progress_hook)
                    
                    if error:
                        auto_download_log[current_sabbath_date][channel_key] = "error"
                        download_results[channel_name] = f"Failed: {error}"
                    else:
                        auto_download_log[current_sabbath_date][channel_key] = "downloaded"
                        download_results[channel_name] = "Success"
                        
                except Exception as e:
                    auto_download_log[current_sabbath_date][channel_key] = "error"
                    download_results[channel_name] = f"Failed: {e}"
            else:
                auto_download_log[current_sabbath_date][channel_key] = "not_found"
                download_results[channel_name] = "Not Found"

        # Reset GUI state after all downloads complete
        if progress_hook and hasattr(progress_hook, '__self__'):
            gui_instance = progress_hook.__self__
            gui_instance.after(0, lambda: gui_instance._set_status("Auto downloads complete."))

        # Final summary notification
        summary_items = []
        for channel, status in download_results.items():
            summary_items.append(f"{channel}: {status}")
        
        summary_message = "\n".join(summary_items)
        
        if not summary_items:
             summary_title = "Auto Download"
             summary_message = "All videos were already downloaded."
        elif all(status == "Success" for status in download_results.values()):
            summary_title = "Auto Download Complete"
            summary_message = "All videos downloaded successfully."
        elif any(status == "Success" for status in download_results.values()):
            summary_title = "Auto Download Partially Complete"
            summary_message = "\n".join(summary_items)
        else:
            summary_title = "Auto Download Failed"
            summary_message = "\n".join(summary_items)

        send_notification_callback(summary_title, summary_message, on_click=show_window_callback)

    # Save the updated log and settings
    save_auto_download_log(auto_download_log)
    settings["last_sabbath_checked"] = current_sabbath_date
    save_settings(settings)