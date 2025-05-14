from app.backend.config import load_settings, load_channels
from app.backend.downloader import get_next_saturday, find_video_url, download_video, delete_old_videos

settings = load_settings()
channels = load_channels()

channel_url = channels["channel_1"]["url"]
expected_date = get_next_saturday()
video_url = find_video_url(channel_url, expected_date)

if video_url:
    delete_old_videos(settings["video_folder"], settings["keep_old_videos"])
    download_video(video_url, settings["video_folder"])
else:
    print("No video found for next Saturday.")
