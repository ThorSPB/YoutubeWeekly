import pytest
from unittest.mock import patch, MagicMock
from app.backend.downloader import download_video

@pytest.fixture
def mock_yt_dlp():
    with patch("yt_dlp.YoutubeDL") as mock_yt_dlp_class:
        mock_yt_dlp_instance = MagicMock()
        mock_yt_dlp_class.return_value = mock_yt_dlp_instance
        yield mock_yt_dlp_instance

def test_download_video(mock_yt_dlp):
    video_url = "https://www.youtube.com/watch?v=example"
    video_folder = "data/videos"

    download_video(video_url, video_folder)

    # Check if yt-dlp download method was called
    mock_yt_dlp.download.assert_called_once()
