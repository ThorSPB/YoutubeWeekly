import json
import os
from datetime import datetime, timedelta

from app.backend.config import load_settings, save_settings, load_channels, CONFIG_DIR
from app.backend.downloader import find_video_url, download_video, get_next_saturday, format_romanian_date, delete_old_videos
from app.backend.overrides import (
    clear_channel_videos,
    download_override,
    fetch_overrides,
    get_override,
    override_signature,
)
from app.backend.telemetry import send_telemetry_ping
from app.i18n import t

AUTO_DOWNLOAD_LOG_FILE = os.path.join(CONFIG_DIR, "auto_download_log.json")

# Key inside a Sabbath's log entry holding the override signature applied per
# channel. Prefixed so it can never collide with a channel folder name.
APPLIED_OVERRIDES_KEY = "_applied_overrides"

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

def _expected_date_strings(current_sabbath_date, date_format):
    """The date spellings this channel's filenames are expected to carry."""
    expected = datetime.strptime(current_sabbath_date, "%Y-%m-%d").strftime(date_format)
    romanian = format_romanian_date(datetime.strptime(expected, date_format))
    return [expected.lower(), romanian.lower()]


def _folder_snapshot(folder):
    """Filenames currently in a folder, for diffing what a download produced."""
    try:
        return set(os.listdir(folder))
    except OSError:
        return set()


def _downloaded_filename(folder, before):
    """The file a download just created, ignoring partials."""
    new = [
        f for f in _folder_snapshot(folder) - before
        if not f.endswith((".part", ".ytdl", ".temp"))
    ]
    if not new:
        return None
    # Largest wins if yt-dlp left intermediate artifacts behind.
    return max(new, key=lambda f: os.path.getsize(os.path.join(folder, f)))


def run_automatic_checks(initial_settings, channels, send_notification_callback,
                         progress_hook=None, show_window_callback=None,
                         status_callback=None, reset_progress_callback=None):
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

    # Overrides for the *current* Sabbath only — never a past one. Cached and
    # ETag-guarded, so this is a 304 unless something actually changed.
    overrides, _ = fetch_overrides()
    applied_overrides = auto_download_log[current_sabbath_date].setdefault(
        APPLIED_OVERRIDES_KEY, {}
    )

    # Pre-check: Verify existence of downloaded files
    for channel_data in channels:
        channel_key = channel_data.get("folder", channel_data["name"])
        if channel_key != "others" and auto_download_log.get(current_sabbath_date, {}).get(channel_key) == "downloaded":
            channel_folder = os.path.join(settings.get("video_folder", "data/videos"), channel_data.get("folder", channel_key))
            date_format = channel_data.get("date_format", "%d.%m.%Y")
            numeric, romanian = _expected_date_strings(current_sabbath_date, date_format)

            # A video that came from an override is named after whatever the
            # override pointed at, which generally does NOT contain this
            # Sabbath's date — that mismatch is the whole reason the override
            # exists. Verify the recorded filename instead, or we would delete
            # and re-download it on every launch.
            record = applied_overrides.get(channel_key) or {}
            recorded_file = record.get("file") if isinstance(record, dict) else None

            found_file = False
            if os.path.exists(channel_folder):
                if recorded_file:
                    found_file = os.path.isfile(os.path.join(channel_folder, recorded_file))
                else:
                    for f in os.listdir(channel_folder):
                        if numeric in f.lower() or romanian in f.lower():
                            found_file = True
                            break

            if not found_file:
                auto_download_log[current_sabbath_date][channel_key] = "pending"
                if recorded_file:
                    # The override's own video was deleted, so let the force
                    # override apply again. When there is no recorded filename
                    # we simply couldn't verify it — dropping the signature
                    # there would re-download on every single launch.
                    applied_overrides.pop(channel_key, None)

    # A force override that hasn't been applied yet supersedes whatever the
    # client has, so those channels get reprocessed even if already downloaded.
    pending_forced = {}
    for channel_data in channels:
        channel_key = channel_data.get("folder", channel_data["name"])
        if channel_key == "others":
            continue
        override = get_override(channel_key, current_sabbath_date, overrides)
        if not (override and override.get("force")):
            continue
        record = applied_overrides.get(channel_key) or {}
        already = record.get("sig") if isinstance(record, dict) else record
        if already != override_signature(override):
            pending_forced[channel_key] = override

    today = datetime.now().date()
    day_of_week = today.weekday() # Monday is 0, Sunday is 6

    # Normally only Friday (4) and Saturday (5). A pending force override is an
    # explicit instruction from the operator, so it is honoured on any day.
    if day_of_week == 4 or day_of_week == 5 or pending_forced:
        channels_to_process = [
            ch for ch in channels
            if ch.get("folder", ch["name"]) != "others" and
               (auto_download_log.get(current_sabbath_date, {}).get(ch.get("folder", ch["name"])) != "downloaded"
                or ch.get("folder", ch["name"]) in pending_forced)
        ]

        # Outside the Fri/Sat window, only act on the forced channels.
        if day_of_week not in (4, 5):
            channels_to_process = [
                ch for ch in channels_to_process
                if ch.get("folder", ch["name"]) in pending_forced
            ]

        if not channels_to_process:
            save_auto_download_log(auto_download_log)
            return

        initial_message = t("auto_starting_msg", channels=", ".join([ch["name"] for ch in channels_to_process]))
        send_notification_callback(t("auto_started"), initial_message)

        download_results = {}

        for channel_data in channels_to_process:
            channel_key = channel_data.get("folder", channel_data["name"])
            channel_name = channel_data.get("name", channel_key)
            channel_url = channel_data["url"]
            date_format = channel_data.get("date_format", "%d.%m.%Y")
            folder = os.path.join(settings.get("video_folder", "data/videos"), channel_data.get("folder", channel_key))

            expected_date_str = datetime.strptime(current_sabbath_date, "%Y-%m-%d").strftime(date_format)
            keep_old = settings.get("keep_old_videos", False)

            # Resolve the source for this channel:
            #   1. a force override wins outright, replacing anything already here
            #   2. otherwise the normal title-date search
            #   3. otherwise a fallback override, if one is set
            forced = pending_forced.get(channel_key)
            source_override = forced
            video_url = None

            if not forced:
                video_url, _match_info = find_video_url(
                    channel_url, expected_date_str, date_format=date_format
                )
                if not video_url:
                    # Search came up empty — use the override if there is one.
                    # Force isn't required here: forcing is about beating a
                    # *successful* search and replacing an existing download.
                    source_override = get_override(
                        channel_key, current_sabbath_date, overrides
                    )

            if source_override or video_url:
                try:
                    # Reset progress tracking and update status for this channel
                    if reset_progress_callback:
                        reset_progress_callback()
                    if status_callback:
                        status_callback(t("auto_downloading", name=channel_name))

                    os.makedirs(folder, exist_ok=True)

                    if forced:
                        # A force override supersedes this Sabbath's video, so it
                        # must go even when the user keeps old videos.
                        previous = applied_overrides.get(channel_key) or {}
                        targets = None
                        if keep_old:
                            targets = _expected_date_strings(current_sabbath_date, date_format)
                            if isinstance(previous, dict) and previous.get("file"):
                                targets.append(previous["file"])
                        clear_channel_videos(folder, targets)
                    else:
                        delete_old_videos(folder, keep_old)

                    quality = settings.get("default_quality", "1080p")
                    before = _folder_snapshot(folder)

                    if source_override:
                        error = download_override(
                            source_override, folder, quality,
                            progress_hook=progress_hook, protect=keep_old,
                        )
                    else:
                        error = download_video(
                            video_url, folder, quality,
                            protect=keep_old, progress_hook=progress_hook,
                        )

                    if error:
                        auto_download_log[current_sabbath_date][channel_key] = "error"
                        download_results[channel_name] = f"Failed: {error}"
                    else:
                        auto_download_log[current_sabbath_date][channel_key] = "downloaded"
                        download_results[channel_name] = "Success"
                        if source_override:
                            # Remember which override produced which file, so the
                            # next run recognises it instead of re-downloading.
                            applied_overrides[channel_key] = {
                                "sig": override_signature(source_override),
                                "file": _downloaded_filename(folder, before),
                            }
                        else:
                            applied_overrides.pop(channel_key, None)

                except Exception as e:
                    auto_download_log[current_sabbath_date][channel_key] = "error"
                    download_results[channel_name] = f"Failed: {e}"
            else:
                auto_download_log[current_sabbath_date][channel_key] = "not_found"
                download_results[channel_name] = "Not Found"

        # Update status after all downloads complete
        if status_callback:
            status_callback(t("auto_complete_status"))

        # Final summary notification
        summary_items = []
        for channel, status in download_results.items():
            summary_items.append(f"{channel}: {status}")
        
        summary_message = "\n".join(summary_items)
        
        if not summary_items:
             summary_title = t("auto_already_downloaded")
             summary_message = t("auto_already_downloaded_msg")
        elif all(status == "Success" for status in download_results.values()):
            summary_title = t("auto_complete")
            summary_message = t("auto_complete_msg")
        elif any(status == "Success" for status in download_results.values()):
            summary_title = t("auto_partial")
            summary_message = "\n".join(summary_items)
        else:
            summary_title = t("auto_failed")
            summary_message = "\n".join(summary_items)

        send_notification_callback(summary_title, summary_message, on_click=show_window_callback)

        successful_count = sum(1 for s in download_results.values() if s == "Success")
        if successful_count > 0:
            send_telemetry_ping(settings, successful_count, session_type="auto")

    # Save the updated log and settings
    save_auto_download_log(auto_download_log)
    settings["last_sabbath_checked"] = current_sabbath_date
    save_settings(settings)