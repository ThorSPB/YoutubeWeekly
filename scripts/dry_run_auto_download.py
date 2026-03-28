#!/usr/bin/env python3
"""
Dry-run simulation of the auto-download scheduler.
Tests that automatic checks run correctly on Fri/Sat and skip on other days.

Usage: python scripts/dry_run_auto_download.py [--day friday|saturday|wednesday]
"""
import argparse
import os
import sys
import json
import tempfile
from unittest.mock import patch
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backend.auto_downloader import run_automatic_checks, load_auto_download_log

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def run_dry_run(day_name="friday"):
    print("=" * 60)
    print(f"YoutubeWeekly Auto-Download Dry-Run (simulated: {day_name})")
    print("=" * 60)

    weekday = DAY_MAP.get(day_name.lower())
    if weekday is None:
        print(f"FAIL: Unknown day '{day_name}'. Use: {', '.join(DAY_MAP.keys())}")
        return 1

    # Build a fake date for the given weekday
    # Start from a known Monday (2025-07-14) and offset
    base_monday = datetime(2025, 7, 14)
    mock_today = base_monday + timedelta(days=weekday)
    print(f"  Simulated date: {mock_today.strftime('%A %Y-%m-%d')}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup mock settings
        settings_path = os.path.join(tmpdir, "settings.json")
        log_path = os.path.join(tmpdir, "auto_download_log.json")
        video_dir = os.path.join(tmpdir, "videos")
        os.makedirs(video_dir)

        settings = {
            "enable_auto_download": True,
            "video_folder": video_dir,
            "default_quality": "1080p",
            "keep_old_videos": False,
            "last_sabbath_checked": None,
        }
        with open(settings_path, "w") as f:
            json.dump(settings, f)
        with open(log_path, "w") as f:
            json.dump({}, f)

        channels = [
            {"name": "Colecta", "url": "http://example.com/colecta", "date_format": "%d.%m.%Y", "folder": "colecta"},
            {"name": "ScoalaDeSabat", "url": "http://example.com/scoala", "date_format": "%d.%m.%Y", "folder": "scoala_de_sabat"},
        ]

        notifications = []
        def mock_notify(title, message, on_click=None):
            notifications.append((title, message))

        class MockDatetime(datetime):
            @classmethod
            def now(cls):
                return mock_today

        with patch("app.backend.auto_downloader.datetime", MockDatetime), \
             patch("app.backend.config.SETTINGS_FILE", settings_path), \
             patch("app.backend.auto_downloader.AUTO_DOWNLOAD_LOG_FILE", log_path), \
             patch("app.backend.auto_downloader.find_video_url") as mock_find, \
             patch("app.backend.auto_downloader.download_video") as mock_download, \
             patch("app.backend.auto_downloader.delete_old_videos"):

            mock_find.return_value = ("https://youtube.com/watch?v=fake123", {"type": "exact", "title": "Fake Video"})
            mock_download.return_value = None  # Success

            run_automatic_checks(settings, channels, mock_notify)

        # Analyze results
        should_run = weekday in (4, 5)  # Friday or Saturday

        print(f"\n  Should run on {day_name}: {should_run}")
        print(f"  Notifications sent: {len(notifications)}")
        for title, msg in notifications:
            print(f"    - {title}: {msg}")

        # Read log file
        with open(log_path, "r") as f:
            log = json.load(f)
        print(f"  Log state: {json.dumps(log, indent=4)}")

        if should_run:
            if len(notifications) == 0:
                print("\n  FAIL: Expected notifications on Friday/Saturday")
                return 1
            if not log:
                print("\n  FAIL: Expected log entries")
                return 1
            # Check all channels are downloaded
            for date_key, channels_status in log.items():
                for ch, status in channels_status.items():
                    if status != "downloaded":
                        print(f"\n  FAIL: Channel {ch} status is '{status}', expected 'downloaded'")
                        return 1
            print("\n  OK - Auto-download ran and all channels downloaded")
        else:
            if len(notifications) > 0:
                print(f"\n  FAIL: Should not send notifications on {day_name}")
                return 1
            print(f"\n  OK - Correctly skipped on {day_name}")

    print("\n" + "=" * 60)
    print("DRY RUN PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dry-run auto-download simulation")
    parser.add_argument("--day", default="friday", help="Day to simulate (default: friday)")
    args = parser.parse_args()
    sys.exit(run_dry_run(args.day))
