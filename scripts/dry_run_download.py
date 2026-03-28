#!/usr/bin/env python3
"""
Dry-run simulation of the download pipeline.
Tests find_video_url → download_video → delete_old_videos with mocked yt-dlp.

Usage: python scripts/dry_run_download.py [--channel colecta|scoala_de_sabat|all]
"""
import argparse
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backend.config import load_settings, load_channels
from app.backend.downloader import find_video_url, get_next_saturday, delete_old_videos, format_romanian_date
from datetime import datetime


def run_dry_run(channel_filter="all"):
    print("=" * 60)
    print("YoutubeWeekly Dry-Run Download Simulation")
    print("=" * 60)

    # Step 1: Load settings
    print("\n[1/5] Loading settings...")
    try:
        settings, warnings = load_settings()
        print(f"  OK - video_folder: {settings.get('video_folder')}")
        print(f"  OK - quality: {settings.get('default_quality', '1080p')}")
        if warnings:
            for w in warnings:
                print(f"  WARN: {w}")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    # Step 2: Load channels
    print("\n[2/5] Loading channels...")
    try:
        raw_channels = load_channels()
        channels = [
            {
                "name": ch_data.get("name", key),
                "url": ch_data["url"],
                "date_format": ch_data.get("date_format", "%d.%m.%Y"),
                "folder": ch_data.get("folder", key),
            }
            for key, ch_data in raw_channels.items()
        ]
        for ch in channels:
            print(f"  OK - {ch['name']} ({ch['folder']}) format={ch['date_format']}")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    # Step 3: Date matching
    print("\n[3/5] Testing date matching...")
    next_sat = get_next_saturday()
    print(f"  Next Saturday (numeric): {next_sat}")
    date_obj = datetime.strptime(next_sat, "%d.%m.%Y")
    romanian = format_romanian_date(date_obj)
    print(f"  Next Saturday (Romanian): {romanian}")

    # Step 4: Simulate find + download per channel
    print("\n[4/5] Simulating find & download for each channel...")

    if channel_filter != "all":
        channels = [ch for ch in channels if ch["folder"] == channel_filter]
        if not channels:
            print(f"  FAIL: No channel with folder '{channel_filter}'")
            return 1

    fake_entries = []
    for ch in channels:
        fmt = ch["date_format"]
        expected_date = get_next_saturday(date_format=fmt)
        fake_entries.append({
            "id": f"fake_{ch['folder']}",
            "title": f"Weekly Video {expected_date}",
        })

    for i, ch in enumerate(channels):
        print(f"\n  --- {ch['name']} ---")
        fmt = ch["date_format"]
        expected_date = get_next_saturday(date_format=fmt)
        print(f"  Looking for date: {expected_date}")

        # Mock yt-dlp
        with patch("app.backend.downloader.yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl
            mock_ydl.extract_info.return_value = {"entries": [fake_entries[i]]}

            url = find_video_url(ch["url"], expected_date, date_format=fmt)
            if url:
                print(f"  FOUND: {url}")
            else:
                print(f"  NOT FOUND (this is a simulation error)")
                return 1

        # Simulate folder creation
        channel_folder = os.path.join(settings.get("video_folder", "data/videos"), ch["folder"])
        print(f"  Would download to: {channel_folder}")
        print(f"  Would use quality: {settings.get('default_quality', '1080p')}")

    # Step 5: Test delete logic with temp dir
    print("\n[5/5] Testing delete_old_videos logic...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy files
        for name in ["old1.mp4", "old2.mp4", "keep.txt"]:
            open(os.path.join(tmpdir, name), "w").close()

        before = os.listdir(tmpdir)
        delete_old_videos(tmpdir, keep_old=False)
        after = os.listdir(tmpdir)

        deleted = set(before) - set(after)
        kept = set(after)
        print(f"  Deleted: {deleted}")
        print(f"  Kept: {kept}")

        if "keep.txt" not in kept:
            print(f"  FAIL: Non-mp4 file was deleted!")
            return 1
        if deleted != {"old1.mp4", "old2.mp4"}:
            print(f"  FAIL: Expected to delete mp4 files only")
            return 1
        print("  OK - Delete logic works correctly")

    print("\n" + "=" * 60)
    print("DRY RUN PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dry-run download simulation")
    parser.add_argument("--channel", default="all", help="Channel folder to test (default: all)")
    args = parser.parse_args()
    sys.exit(run_dry_run(args.channel))
