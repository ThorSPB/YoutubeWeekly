import os
import pytest
from app.backend.downloader import delete_old_videos

@pytest.fixture
def mock_files():
    import os
    os.makedirs("data/videos", exist_ok=True)
    # Create mock old video file
    with open("data/videos/old_video.mp4", "w") as f:
        f.write("Old video content")
    yield
    # Cleanup after test
    if os.path.exists("data/videos/old_video.mp4"):
        os.remove("data/videos/old_video.mp4")
    if os.path.exists("data/videos"):
        try:
            os.rmdir("data/videos")
        except OSError:
            pass

def test_delete_old_videos(mock_files):
    video_folder = "data/videos"
    keep_old_videos = False

    # Test with delete option enabled
    delete_old_videos(video_folder, keep_old_videos)
    
    assert not os.path.exists("data/videos/old_video.mp4"), "Old video was not deleted"
