import os
import pytest
from unittest.mock import patch, MagicMock
from app.backend.downloader import delete_old_videos

@pytest.fixture
def mock_load_protected_videos(monkeypatch):
    def mock_func():
        return {"colecta": [], "scoala_de_sabat": [], "other": []}
    monkeypatch.setattr("app.backend.downloader.load_protected_videos", mock_func)

@pytest.fixture
def create_mock_video_file(tmp_path):
    def _create_mock_video(filename="old_video.mp4", content="Old video content"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return file_path
    return _create_mock_video

def test_delete_old_videos(create_mock_video_file, mock_load_protected_videos):
    video_file = create_mock_video_file()
    video_folder = str(video_file.parent)
    keep_old_videos = False

    delete_old_videos(video_folder, keep_old_videos)
    
    assert not video_file.exists(), "Old video was not deleted"
