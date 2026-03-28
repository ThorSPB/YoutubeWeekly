import pytest
from unittest.mock import patch, MagicMock
from app.frontend.player_utils import build_mpv_args, play_video


def test_build_mpv_args_basic():
    settings = {"mpv_path": "/usr/bin/mpv", "mpv_volume": 100, "mpv_screen": "Default", "mpv_custom_args": ""}
    args = build_mpv_args(settings, "/tmp/video.mp4")
    assert args == ["/usr/bin/mpv", "/tmp/video.mp4", "--volume=100"]


def test_build_mpv_args_fullscreen():
    settings = {"mpv_path": "/usr/bin/mpv", "mpv_fullscreen": True, "mpv_volume": 100, "mpv_screen": "Default", "mpv_custom_args": ""}
    args = build_mpv_args(settings, "/tmp/video.mp4", script_path="/scripts/fs.lua")
    assert "--script=/scripts/fs.lua" in args


def test_build_mpv_args_screen_selection():
    settings = {"mpv_path": "/usr/bin/mpv", "mpv_volume": 80, "mpv_screen": "1", "mpv_custom_args": ""}
    args = build_mpv_args(settings, "/tmp/video.mp4")
    assert "--screen=1" in args
    assert "--volume=80" in args


def test_build_mpv_args_custom_args():
    settings = {"mpv_path": "/usr/bin/mpv", "mpv_volume": 100, "mpv_screen": "Default", "mpv_custom_args": "--no-border --ontop"}
    args = build_mpv_args(settings, "/tmp/video.mp4")
    assert "--no-border" in args
    assert "--ontop" in args


def test_build_mpv_args_no_fullscreen_without_script():
    settings = {"mpv_path": "/usr/bin/mpv", "mpv_fullscreen": True, "mpv_volume": 100, "mpv_screen": "Default", "mpv_custom_args": ""}
    args = build_mpv_args(settings, "/tmp/video.mp4")  # No script_path
    assert not any("--script" in a for a in args)


@patch("app.frontend.player_utils.subprocess.Popen")
def test_play_video_mpv_success(mock_popen):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"", b"")
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    settings = {"use_mpv": True, "mpv_path": "/usr/bin/mpv", "mpv_volume": 100, "mpv_screen": "Default", "mpv_custom_args": ""}
    error = play_video(settings, "/tmp/video.mp4")
    assert error is None
    mock_popen.assert_called_once()


@patch("app.frontend.player_utils.subprocess.Popen")
def test_play_video_mpv_failure(mock_popen):
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"", b"MPV error")
    mock_process.returncode = 1
    mock_popen.return_value = mock_process

    settings = {"use_mpv": True, "mpv_path": "/usr/bin/mpv", "mpv_volume": 100, "mpv_screen": "Default", "mpv_custom_args": ""}
    error = play_video(settings, "/tmp/video.mp4")
    assert error == "MPV error"


@patch("app.frontend.player_utils.subprocess.call")
def test_play_video_default_player_linux(mock_call):
    settings = {"use_mpv": False}
    error = play_video(settings, "/tmp/video.mp4")
    assert error is None
    mock_call.assert_called_once()
