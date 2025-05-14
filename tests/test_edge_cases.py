import os
import pytest
from unittest.mock import patch, MagicMock
from app.backend.downloader import download_video, delete_old_videos, find_video_url
from datetime import datetime

# Edge cases for download_video
@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_download_video_invalid_url(mock_yt_dlp, caplog):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.download.side_effect = Exception("Invalid URL")

    download_video("invalid_url", "data/videos")
    assert any("Download failed" in record.message for record in caplog.records)

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_download_video_empty_folder(mock_yt_dlp, caplog):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

    download_video("https://www.youtube.com/watch?v=example", "")

    assert any("Video folder path is empty or invalid." in record.message for record in caplog.records)

# Edge cases for delete_old_videos
def test_delete_old_videos_empty_folder(tmp_path):
    delete_old_videos(str(tmp_path), keep_old=False)
    # No error should occur

def test_delete_old_videos_non_mp4_files(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("Not a video")
    delete_old_videos(str(tmp_path), keep_old=False)
    assert file_path.exists()

def test_delete_old_videos_keep_old(tmp_path):
    file_path = tmp_path / "video.mp4"
    file_path.write_text("Video content")
    delete_old_videos(str(tmp_path), keep_old=True)
    assert file_path.exists()

# Edge cases for find_video_url
@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_find_video_url_no_videos(mock_yt_dlp):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {"entries": []}

    url = find_video_url("https://www.youtube.com/c/SomeChannel", "2025-04-12")
    assert url is None

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_find_video_url_multiple_videos_same_date(mock_yt_dlp):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {
        "entries": [
            {"title": "Video for 2025-04-12 part 1", "id": "id1"},
            {"title": "Video for 2025-04-12 part 2", "id": "id2"},
        ]
    }

    url = find_video_url("https://www.youtube.com/c/SomeChannel", "2025-04-12")
    assert url == "https://www.youtube.com/watch?v=id1"

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_find_video_url_invalid_channel(mock_yt_dlp):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.side_effect = Exception("Invalid channel URL")

    url = find_video_url("invalid_channel_url", "2025-04-12")
    assert url is None

# Integration test simulating full workflow
@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_integration_workflow(mock_yt_dlp, tmp_path):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {
        "entries": [
            {"title": "Weekly Video 2025-04-12", "id": "videoid"}
        ]
    }

    # Step 1: Find video URL
    video_url = find_video_url("https://www.youtube.com/c/SomeChannel", "2025-04-12")
    assert video_url == "https://www.youtube.com/watch?v=videoid"

    # Step 2: Download video
    download_video(video_url, str(tmp_path))
    mock_ydl_instance.download.assert_called_once()

    # Create a dummy old video file to test deletion
    old_video = tmp_path / "old_video.mp4"
    old_video.write_text("old video content")

    # Step 3: Delete old videos
    delete_old_videos(str(tmp_path), keep_old=False)
    assert not old_video.exists()
