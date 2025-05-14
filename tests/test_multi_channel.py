import pytest
from unittest.mock import patch, MagicMock
from app.backend.downloader import find_video_url, download_video

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_find_video_url_first_channel_format(mock_yt_dlp):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {
        "entries": [
            {"title": "Video for 2025-04-12", "id": "id1"}
        ]
    }
    url = find_video_url("https://www.youtube.com/c/Channel1", "2025-04-12", date_format="%Y-%m-%d")
    assert url == "https://www.youtube.com/watch?v=id1"

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_find_video_url_second_channel_format(mock_yt_dlp):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {
        "entries": [
            {"title": "10.05.2025 [SMV RO] - Speranta in agitatie", "id": "id2"}
        ]
    }
    url = find_video_url("https://www.youtube.com/@ScoalaDeSabat", "10.05.2025", date_format="%d.%m.%Y")
    assert url == "https://www.youtube.com/watch?v=id2"

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_download_video_already_exists(mock_yt_dlp, tmp_path):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

    # Create a dummy file that simulates existing video
    existing_file = tmp_path / "id3.mp4"
    existing_file.write_text("dummy content")

    video_url = "https://www.youtube.com/watch?v=id3"
    download_video(video_url, str(tmp_path))

    # The download method should not be called because video exists
    mock_ydl_instance.download.assert_not_called()

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_find_video_url_no_matching_date(mock_yt_dlp):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {
        "entries": [
            {"title": "Some other video", "id": "id4"}
        ]
    }
    url = find_video_url("https://www.youtube.com/c/Channel1", "2025-04-12", date_format="%Y-%m-%d")
    assert url is None

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_integration_multi_channel_workflow(mock_yt_dlp, tmp_path):
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance

    # Setup extract_info to return videos for both channels
    def extract_info_side_effect(url, download):
        if "ScoalaDeSabat" in url:
            return {
                "entries": [
                    {"title": "10.05.2025 [SMV RO] - Speranta in agitatie", "id": "id2"}
                ]
            }
        else:
            return {
                "entries": [
                    {"title": "Video for 2025-04-12", "id": "id1"}
                ]
            }
    mock_ydl_instance.extract_info.side_effect = extract_info_side_effect

    # Test find_video_url for both channels
    url1 = find_video_url("https://www.youtube.com/c/Channel1", "2025-04-12", date_format="%Y-%m-%d")
    url2 = find_video_url("https://www.youtube.com/@ScoalaDeSabat", "10.05.2025", date_format="%d.%m.%Y")

    assert url1 == "https://www.youtube.com/watch?v=id1"
    assert url2 == "https://www.youtube.com/watch?v=id2"

    # Test download_video for both URLs
    download_video(url1, str(tmp_path))
    download_video(url2, str(tmp_path))

    # Check that download was called twice
    assert mock_ydl_instance.download.call_count == 2
