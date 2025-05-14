from app.backend.downloader import find_video_url
from datetime import datetime

def test_find_video_url():
    channel_url = "https://www.youtube.com/c/DepartamentulIsprăvnicie"
    # Mock date for the test: Assume the next Saturday is April 12, 2025
    mock_date = datetime(2025, 4, 12)
    
    video_url = find_video_url(channel_url, mock_date)
    assert video_url is not None, "No video URL found"
    # Here we could also validate the URL pattern or check against a known URL, if possible.
