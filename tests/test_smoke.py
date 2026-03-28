"""
E2E smoke test — validates the full find→download→delete pipeline with mocked yt-dlp.
"""
import pytest
import os
import json
from unittest.mock import patch, MagicMock
from app.backend.downloader import find_video_url, download_video, delete_old_videos
from app.backend.config import load_settings, save_settings, load_channels


def test_full_download_pipeline(tmp_path, monkeypatch):
    """Simulate a complete download cycle: find video, download, delete old."""

    # Setup mock settings
    settings_path = tmp_path / "settings.json"
    settings_data = {
        "video_folder": str(tmp_path / "videos"),
        "keep_old_videos": False,
        "default_quality": "1080p",
        "protected_videos": {}
    }
    with open(settings_path, "w") as f:
        json.dump(settings_data, f)
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(settings_path))

    # Create channel folder with an "old" video
    channel_folder = tmp_path / "videos" / "colecta"
    channel_folder.mkdir(parents=True)
    old_video = channel_folder / "old_video_01.01.2025.mp4"
    old_video.write_text("old content")

    # Mock yt-dlp for find_video_url
    with patch("app.backend.downloader.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Step 1: find_video_url
        mock_ydl.extract_info.return_value = {
            "entries": [
                {"id": "abc123", "title": "Weekly Video 15.03.2025"},
                {"id": "def456", "title": "Another 15 martie 2025 diaspora"},  # Should be excluded
            ]
        }
        url = find_video_url("https://youtube.com/c/TestChannel", "15.03.2025")
        assert url == "https://www.youtube.com/watch?v=abc123"

        # Step 2: delete_old_videos
        delete_old_videos(str(channel_folder), keep_old=False)
        assert not old_video.exists(), "Old video should be deleted"

        # Step 3: download_video (mock the actual download)
        mock_ydl.download.return_value = None
        mock_ydl.extract_info.return_value = {"title": "Weekly Video 15.03.2025", "ext": "mp4"}

        error = download_video(url, str(channel_folder), quality_pref="1080p")
        assert error is None
        mock_ydl.download.assert_called_once_with([url])


def test_channel_config_loads():
    """Verify channel configuration loads and has expected structure."""
    channels = load_channels()
    assert len(channels) >= 1

    for key, channel in channels.items():
        assert "url" in channel, f"Channel {key} missing 'url'"
        assert "name" in channel or key, f"Channel {key} missing identifier"


def test_settings_roundtrip(tmp_path, monkeypatch):
    """Verify settings can be saved and loaded back correctly."""
    settings_path = tmp_path / "settings.json"
    with open(settings_path, "w") as f:
        json.dump({"video_folder": str(tmp_path), "default_quality": "720p"}, f)
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(settings_path))

    settings, warnings = load_settings()
    assert settings["default_quality"] == "720p"

    settings["default_quality"] = "480p"
    save_settings(settings)

    reloaded, _ = load_settings()
    assert reloaded["default_quality"] == "480p"


def test_diaspora_exclusion():
    """Verify videos with 'diaspora' in title are excluded."""
    with patch("app.backend.downloader.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
            "entries": [
                {"id": "vid1", "title": "Video 10.05.2025 diaspora"},
                {"id": "vid2", "title": "Video 10.05.2025"},
            ]
        }
        url = find_video_url("https://youtube.com/c/Test", "10.05.2025")
        assert url == "https://www.youtube.com/watch?v=vid2"
