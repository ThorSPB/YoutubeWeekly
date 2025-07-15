import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
import os

from app.backend.auto_downloader import (
    load_auto_download_log,
    save_auto_download_log,
    get_current_sabbath_date,
    run_automatic_checks,
    AUTO_DOWNLOAD_LOG_FILE
)
from app.backend.config import save_settings

# Fixtures for mocking files and settings
@pytest.fixture
def mock_settings_file(tmp_path):
    test_settings_path = tmp_path / "settings.json"
    initial_settings = {
        "enable_auto_download": True,
        "enable_notifications": True,
        "video_folder": str(tmp_path / "videos"),
        "default_quality": "1080p",
        "last_sabbath_checked": None
    }
    with open(test_settings_path, "w") as f:
        json.dump(initial_settings, f)
    return test_settings_path

@pytest.fixture
def mock_auto_download_log_file(tmp_path, monkeypatch):
    test_log_path = tmp_path / "auto_download_log.json"
    monkeypatch.setattr("app.backend.auto_downloader.AUTO_DOWNLOAD_LOG_FILE", str(test_log_path))
    return test_log_path

@pytest.fixture
def mock_channels_data():
    return [
        {"name": "Colecta", "url": "http://example.com/colecta", "date_format": "%d.%m.%Y", "folder": "colecta"},
        {"name": "Scoala de Sabat", "url": "http://example.com/scoala", "date_format": "%d.%m.%Y", "folder": "scoala_de_sabat"}
    ]

@pytest.fixture
def mock_send_notification():
    return MagicMock()

# Helper functions to load/save settings from a specific path for testing
def load_settings_from_path(path):
    with open(path, "r") as f:
        return json.load(f)

def save_settings_to_path(path, settings_data):
    with open(path, "w") as f:
        json.dump(settings_data, f, indent=2)

# Tests for log functions
def test_load_auto_download_log_empty(mock_auto_download_log_file):
    assert load_auto_download_log() == {}

def test_save_and_load_auto_download_log(mock_auto_download_log_file):
    test_data = {"2025-07-19": {"channel_1": "downloaded"}}
    save_auto_download_log(test_data)
    assert load_auto_download_log() == test_data

# Tests for get_current_sabbath_date
@pytest.mark.parametrize("today_date, expected_sabbath", [
    (datetime(2025, 7, 14), "2025-07-19"),  # Monday
    (datetime(2025, 7, 18), "2025-07-19"),  # Friday
    (datetime(2025, 7, 19), "2025-07-19"),  # Saturday
    (datetime(2025, 7, 20), "2025-07-26"),  # Sunday
])
def test_get_current_sabbath_date(today_date, expected_sabbath, monkeypatch):
    class MockDatetime(datetime):
        @classmethod
        def now(cls):
            return today_date
    monkeypatch.setattr("app.backend.auto_downloader.datetime", MockDatetime)
    assert get_current_sabbath_date() == expected_sabbath

# Tests for run_automatic_checks
@patch("app.backend.auto_downloader.find_video_url")
@patch("app.backend.auto_downloader.download_video")
def test_run_automatic_checks_disabled(mock_download_video, mock_find_video_url,
                                       mock_settings_file, mock_channels_data, mock_send_notification, monkeypatch):
    # Temporarily change the SETTINGS_FILE path to our mock file
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(mock_settings_file))

    settings = load_settings_from_path(mock_settings_file)
    settings["enable_auto_download"] = False
    save_settings_to_path(mock_settings_file, settings)

    run_automatic_checks(settings, mock_channels_data, mock_send_notification)

    mock_find_video_url.assert_not_called()
    mock_download_video.assert_not_called()
    mock_send_notification.assert_not_called()

@patch("app.backend.auto_downloader.find_video_url")
@patch("app.backend.auto_downloader.download_video")
def test_run_automatic_checks_friday_new_sabbath(mock_download_video, mock_find_video_url,
                                                mock_settings_file, mock_auto_download_log_file, mock_channels_data,
                                                mock_send_notification, monkeypatch):
    # Temporarily change the SETTINGS_FILE path to our mock file
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(mock_settings_file))
    monkeypatch.setattr("app.backend.auto_downloader.AUTO_DOWNLOAD_LOG_FILE", str(mock_auto_download_log_file))

    # Mock today's date to be a Friday
    mock_today = datetime(2025, 7, 18) # Friday
    class MockDatetime(datetime):
        @classmethod
        def now(cls):
            return mock_today
    monkeypatch.setattr("app.backend.auto_downloader.datetime", MockDatetime)

    settings = load_settings_from_path(mock_settings_file)
    settings["last_sabbath_checked"] = "2025-07-12" # Previous Sabbath
    save_settings_to_path(mock_settings_file, settings)

    mock_find_video_url.side_effect = ["http://video1.url", "http://video2.url"]

    run_automatic_checks(settings, mock_channels_data, mock_send_notification)

    # Assertions
    assert mock_find_video_url.call_count == len(mock_channels_data)
    assert mock_download_video.call_count == len(mock_channels_data)
    assert mock_send_notification.call_count == len(mock_channels_data) * 2 # 1 checking, 1 downloaded per channel

    updated_settings = load_settings_from_path(mock_settings_file)
    assert updated_settings["last_sabbath_checked"] == "2025-07-19"

    log = load_auto_download_log()
    assert log["2025-07-19"]["colecta"] == "downloaded"
    assert log["2025-07-19"]["scoala_de_sabat"] == "downloaded"

@patch("app.backend.auto_downloader.find_video_url")
@patch("app.backend.auto_downloader.download_video")
def test_run_automatic_checks_saturday_partial_download(mock_download_video, mock_find_video_url,
                                                        mock_settings_file, mock_auto_download_log_file, mock_channels_data,
                                                        mock_send_notification, monkeypatch):
    # Temporarily change the SETTINGS_FILE path to our mock file
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(mock_settings_file))
    monkeypatch.setattr("app.backend.auto_downloader.AUTO_DOWNLOAD_LOG_FILE", str(mock_auto_download_log_file))

    # Mock today's date to be a Saturday
    mock_today = datetime(2025, 7, 19) # Saturday
    class MockDatetime(datetime):
        @classmethod
        def now(cls):
            return mock_today
    monkeypatch.setattr("app.backend.auto_downloader.datetime", MockDatetime)

    settings = load_settings_from_path(mock_settings_file)
    settings["last_sabbath_checked"] = "2025-07-19" # Same Sabbath, already checked Friday
    save_settings_to_path(mock_settings_file, settings)

    # Pre-populate log with one downloaded and one pending
    initial_log = {"2025-07-19": {"channel_1": "downloaded", "channel_2": "pending"}}
    save_auto_download_log(initial_log)

    mock_find_video_url.side_effect = ["http://video1.url", "http://video2.url"]

    run_automatic_checks(settings, mock_channels_data, mock_send_notification)

    # Assertions
    assert mock_find_video_url.call_count == len(mock_channels_data)
    assert mock_download_video.call_count == len(mock_channels_data)
    assert mock_send_notification.call_count == len(mock_channels_data) * 2 # 1 checking, 1 downloaded per channel

    updated_settings = load_settings_from_path(mock_settings_file)
    assert updated_settings["last_sabbath_checked"] == "2025-07-19"

    log = load_auto_download_log()
    assert log["2025-07-19"]["colecta"] == "downloaded"
    assert log["2025-07-19"]["scoala_de_sabat"] == "downloaded"