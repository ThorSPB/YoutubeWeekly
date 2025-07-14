from unittest.mock import patch, MagicMock
from app.backend.downloader import find_video_url
from datetime import datetime

@patch("app.backend.downloader.yt_dlp.YoutubeDL")
def test_find_video_url(mock_yt_dlp):
    # Setup mock
    mock_ydl_instance = MagicMock()
    mock_yt_dlp.return_value.__enter__.return_value = mock_ydl_instance
    mock_ydl_instance.extract_info.return_value = {
        "entries": [
            {"title": "Video for 12.04.2025", "id": "exampleid"}
        ]
    }

    channel_url = "https://www.youtube.com/c/DepartamentulIsprăvnicie"
    mock_date = datetime(2025, 4, 12)

    video_url = find_video_url(channel_url, mock_date.strftime("%d.%m.%Y"))
    assert video_url == "https://www.youtube.com/watch?v=exampleid", "Video URL did not match expected"
