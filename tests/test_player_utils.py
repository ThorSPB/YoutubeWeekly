import pytest
from unittest.mock import patch, MagicMock
from app.frontend.player_utils import AUDIO_WINDOW_ARGS, build_mpv_args, is_audio_file, play_video


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
@patch("app.frontend.player_utils.os.name", "posix")
@patch("app.frontend.player_utils.sys.platform", "linux")
def test_play_video_default_player_linux(mock_call):
    settings = {"use_mpv": False}
    error = play_video(settings, "/tmp/video.mp4")
    assert error is None
    mock_call.assert_called_once()


# An audio file used to play with no window at all: nothing to pause or close it
# with, and closing the app did not stop it (church PC, 2026-11-20).
CHURCH = {"mpv_path": "mpv.exe", "use_mpv": True, "mpv_fullscreen": True, "mpv_volume": 100,
          "mpv_screen": "1", "mpv_custom_args": ""}


@pytest.mark.parametrize("name", ["Karaoke Version.mp3", "NEGATIV.MP3", "x.m4a", "x.wav", "x.flac", "x.ogg", "x.opus"])
def test_an_audio_file_gets_a_window_with_its_controls(name):
    args = build_mpv_args(CHURCH, f"D:/videos/other/{name}", script_path="fs.lua")
    assert is_audio_file(name)
    for a in AUDIO_WINDOW_ARGS:
        assert a in args


def test_an_audio_window_stays_off_the_projector():
    """No fullscreen script and no --screen: a backing track never covers the lyrics."""
    args = build_mpv_args(CHURCH, "D:/videos/other/track.mp3", script_path="fs.lua")
    assert not any(a.startswith("--script=") for a in args)
    assert not any(a.startswith("--screen=") for a in args)
    assert "--volume=100" in args


def test_a_video_still_goes_fullscreen_on_its_screen_with_no_forced_window():
    args = build_mpv_args(CHURCH, "D:/videos/colecta/22 august 2026.mp4", script_path="fs.lua")
    assert "--script=fs.lua" in args and "--screen=1" in args
    assert not any(a.startswith("--force-window") for a in args)
    assert not is_audio_file("x.mp4")
