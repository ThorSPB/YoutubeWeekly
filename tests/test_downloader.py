import pytest
import os
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.backend.downloader import (
    load_protected_videos,
    add_protected_video,
    get_next_saturday,
    format_romanian_date,
    find_video_url,
    delete_old_videos,
    download_video,
    get_recent_sabbaths
)

# Fixture for mocking settings.json
@pytest.fixture
def mock_settings_file(tmp_path):
    settings_dir = tmp_path / "config"
    settings_dir.mkdir()
    settings_path = settings_dir / "settings.json"
    initial_settings = {
        "protected_videos": {
            "channel1": ["video_a.mp4"]
        }
    }
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(initial_settings, f)
    
    with patch('app.backend.downloader.os.path.join', return_value=str(settings_path)):
        yield settings_path

# Test for load_protected_videos
def test_load_protected_videos(mock_settings_file):
    protected = load_protected_videos()
    assert protected == {"channel1": ["video_a.mp4"]}

# Test for add_protected_video
def test_add_protected_video_new_video(mock_settings_file):
    add_protected_video("channel1", "video_b.mp4")
    with open(mock_settings_file, "r", encoding="utf-8") as f:
        settings = json.load(f)
    assert "video_b.mp4" in settings["protected_videos"]["channel1"]

def test_add_protected_video_existing_video(mock_settings_file):
    add_protected_video("channel1", "video_a.mp4") # Add existing video
    with open(mock_settings_file, "r", encoding="utf-8") as f:
        settings = json.load(f)
    assert settings["protected_videos"]["channel1"].count("video_a.mp4") == 1

def test_add_protected_video_new_channel(mock_settings_file):
    add_protected_video("channel2", "video_c.mp4")
    with open(mock_settings_file, "r", encoding="utf-8") as f:
        settings = json.load(f)
    assert "video_c.mp4" in settings["protected_videos"]["channel2"]

# Test for get_next_saturday
@pytest.mark.parametrize("today_weekday, expected_days_ahead", [
    (0, 5), # Monday
    (1, 4), # Tuesday
    (2, 3), # Wednesday
    (3, 2), # Thursday
    (4, 1), # Friday
    (5, 0), # Saturday
    (6, 6), # Sunday
])
def test_get_next_saturday(monkeypatch, today_weekday, expected_days_ahead):
    mock_today = datetime(2024, 7, 15) + timedelta(days=today_weekday - datetime(2024, 7, 15).weekday())
    class MockDatetime(datetime):
        @classmethod
        def today(cls):
            return mock_today
    monkeypatch.setattr('app.backend.downloader.datetime', MockDatetime)
    
    expected_date = (mock_today + timedelta(days=expected_days_ahead)).strftime("%d.%m.%Y")
    assert get_next_saturday() == expected_date

# Test for format_romanian_date
@pytest.mark.parametrize("date_obj, expected_format", [
    (datetime(2024, 1, 1), "1 ianuarie 2024"),
    (datetime(2024, 7, 15), "15 iulie 2024"),
    (datetime(2024, 12, 25), "25 decembrie 2024"),
])
def test_format_romanian_date(date_obj, expected_format):
    assert format_romanian_date(date_obj) == expected_format

# Test for find_video_url
def test_find_video_url_found(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"id": "video1", "title": "Video Title 15.07.2024"},
                {"id": "video2", "title": "Another Video 15 iulie 2024"},
                {"id": "video3", "title": "Some other video"},
            ]
        }
        url = find_video_url("http://example.com/channel", "15.07.2024")
        assert url == "https://www.youtube.com/watch?v=video1"

def test_find_video_url_not_found(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"id": "video1", "title": "Video Title 14.07.2024"},
            ]
        }
        url = find_video_url("http://example.com/channel", "15.07.2024")
        assert url is None

def test_find_video_url_diaspora_excluded(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"id": "video1", "title": "Video Title 15.07.2024 diaspora"},
            ]
        }
        url = find_video_url("http://example.com/channel", "15.07.2024")
        assert url is None

def test_find_video_url_extraction_error(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.side_effect = Exception("Extraction failed")
        url = find_video_url("http://example.com/channel", "15.07.2024")
        assert url is None

def test_find_video_url_invalid_date_format(monkeypatch):
    url = find_video_url("http://example.com/channel", "invalid-date")
    assert url is None

# Test for delete_old_videos
def test_delete_old_videos_no_keep_old(monkeypatch, tmp_path):
    video_folder = tmp_path / "test_channel"
    video_folder.mkdir()
    (video_folder / "old_video.mp4").write_text("content")
    (video_folder / "protected_video.mp4").write_text("content")
    (video_folder / "other_file.txt").write_text("content")

    monkeypatch.setattr('app.backend.downloader.os.listdir', lambda x: ["old_video.mp4", "protected_video.mp4", "other_file.txt"])
    monkeypatch.setattr('app.backend.downloader.os.path.basename', lambda x: "test_channel")
    mock_os_remove = MagicMock()
    monkeypatch.setattr('app.backend.downloader.os.remove', mock_os_remove)
    monkeypatch.setattr('app.backend.downloader.load_protected_videos', lambda: {"test_channel": ["protected_video.mp4"]})

    delete_old_videos(str(video_folder), keep_old=False)
    mock_os_remove.assert_called_once_with(str(video_folder / "old_video.mp4"))

def test_delete_old_videos_keep_old(monkeypatch, tmp_path):
    video_folder = tmp_path / "test_channel"
    video_folder.mkdir()
    (video_folder / "old_video.mp4").write_text("content")

    monkeypatch.setattr('app.backend.downloader.os.listdir', lambda x: ["old_video.mp4"])
    monkeypatch.setattr('app.backend.downloader.os.path.basename', lambda x: "test_channel")
    mock_os_remove = MagicMock()
    monkeypatch.setattr('app.backend.downloader.os.remove', mock_os_remove)
    monkeypatch.setattr('app.backend.downloader.load_protected_videos', lambda: {})

    delete_old_videos(str(video_folder), keep_old=True)
    mock_os_remove.assert_not_called()

def test_delete_old_videos_no_videos(monkeypatch, tmp_path):
    video_folder = tmp_path / "test_channel"
    video_folder.mkdir()

    monkeypatch.setattr('app.backend.downloader.os.listdir', lambda x: [])
    monkeypatch.setattr('app.backend.downloader.os.path.basename', lambda x: "test_channel")
    mock_os_remove = MagicMock()
    monkeypatch.setattr('app.backend.downloader.os.remove', mock_os_remove)
    monkeypatch.setattr('app.backend.downloader.load_protected_videos', lambda: {})

    delete_old_videos(str(video_folder), keep_old=False)
    mock_os_remove.assert_not_called()

# Test for download_video
@pytest.fixture
def mock_download_dependencies(monkeypatch):
    mock_os_path_exists = MagicMock(return_value=False)
    mock_os_listdir = MagicMock(return_value=[])
    mock_os_makedirs = MagicMock()
    mock_add_protected_video = MagicMock()
    mock_ydl = MagicMock()
    mock_ydl_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
    
    monkeypatch.setattr('app.backend.downloader.os.path.exists', mock_os_path_exists)
    monkeypatch.setattr('app.backend.downloader.os.listdir', mock_os_listdir)
    monkeypatch.setattr('app.backend.downloader.os.makedirs', mock_os_makedirs)
    monkeypatch.setattr('app.backend.downloader.add_protected_video', mock_add_protected_video)
    monkeypatch.setattr('app.backend.downloader.yt_dlp.YoutubeDL', mock_ydl)
    
    return {
        "mock_os_path_exists": mock_os_path_exists,
        "mock_os_listdir": mock_os_listdir,
        "mock_os_makedirs": mock_os_makedirs,
        "mock_add_protected_video": mock_add_protected_video,
        "mock_ydl": mock_ydl,
        "mock_ydl_instance": mock_ydl_instance
    }

def test_download_video_invalid_folder(mock_download_dependencies):
    download_video("http://example.com/video", "")
    mock_download_dependencies["mock_os_makedirs"].assert_not_called()
    mock_download_dependencies["mock_ydl"].assert_not_called()

def test_download_video_already_exists(mock_download_dependencies):
    mock_download_dependencies["mock_os_path_exists"].return_value = True
    mock_download_dependencies["mock_os_listdir"].return_value = ["some_video_id.mp4"]
    download_video("http://example.com/video?v=some_video_id", "/tmp/videos")
    mock_download_dependencies["mock_os_makedirs"].assert_not_called()
    mock_download_dependencies["mock_ydl"].assert_not_called()

def test_download_video_1080p(mock_download_dependencies):
    download_video("http://example.com/video", "/tmp/videos", quality_pref="1080p")
    mock_download_dependencies["mock_os_makedirs"].assert_called_once_with("/tmp/videos", exist_ok=True)
    args, kwargs = mock_download_dependencies["mock_ydl"].call_args
    assert args[0]['format'] == 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
    assert args[0]['merge_output_format'] == 'mp4'
    mock_download_dependencies["mock_ydl_instance"].download.assert_called_once_with(["http://example.com/video"])

def test_download_video_mp3(mock_download_dependencies):
    download_video("http://example.com/video", "/tmp/videos", quality_pref="mp3")
    mock_download_dependencies["mock_os_makedirs"].assert_called_once_with("/tmp/videos", exist_ok=True)
    args, kwargs = mock_download_dependencies["mock_ydl"].call_args
    assert args[0]['format'] == 'bestaudio/best'
    assert args[0]['merge_output_format'] == 'mp3'
    assert args[0]['postprocessors'][0]['key'] == 'FFmpegExtractAudio'
    mock_download_dependencies["mock_ydl_instance"].download.assert_called_once_with(["http://example.com/video"])

def test_download_video_protect(mock_download_dependencies):
    mock_download_dependencies["mock_os_listdir"].return_value = ["video_to_protect.mp4"]
    download_video("http://example.com/video?v=video_to_protect", "/tmp/videos", protect=True)
    mock_download_dependencies["mock_add_protected_video"].assert_called_once_with("videos", "video_to_protect.mp4")

def test_download_video_download_failure(mock_download_dependencies):
    mock_download_dependencies["mock_ydl_instance"].download.side_effect = Exception("Download error")
    download_video("http://example.com/video", "/tmp/videos")
    mock_download_dependencies["mock_ydl_instance"].download.assert_called_once()
    # Assert that logging.error was called, but mocking logging is more complex.
    # For now, just ensure no other unexpected calls or crashes.

# Test for get_recent_sabbaths
@pytest.mark.parametrize("n, expected_sabbaths", [
    (1, ["13.07.2024"]), # Assuming today is 15.07.2024 (Monday)
    (2, ["13.07.2024", "06.07.2024"]),
])
def test_get_recent_sabbaths(monkeypatch, n, expected_sabbaths):
    mock_today = datetime(2024, 7, 15) # A Monday
    class MockDatetime(datetime):
        @classmethod
        def today(cls):
            return mock_today
    monkeypatch.setattr('app.backend.downloader.datetime', MockDatetime)
    
    sabbaths = get_recent_sabbaths(n=n)
    assert sabbaths == expected_sabbaths
