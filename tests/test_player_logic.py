import pytest
import os
import sys
from unittest.mock import patch, MagicMock, call
from app.frontend.gui import YoutubeWeeklyGUI
from app.frontend.file_viewer import FileViewer
import tkinter as tk


@pytest.fixture
def gui(tmp_path):
    """Create a mock GUI instance for player tests."""
    with patch('app.frontend.gui.YoutubeWeeklyGUI.__init__', return_value=None):
        g = YoutubeWeeklyGUI()
        g.settings = {
            "video_folder": str(tmp_path / "data" / "videos"),
            "use_mpv": False,
            "mpv_path": "/usr/bin/mpv",
            "mpv_fullscreen": False,
            "mpv_volume": 100,
            "mpv_custom_args": "",
            "mpv_screen": "Default",
        }
        g.base_path = g.settings["video_folder"]
        g._set_status = MagicMock()
        g.downloading_channels = set()
        yield g


@pytest.fixture
def file_viewer():
    """Create a mock FileViewer instance."""
    with patch('app.frontend.file_viewer.FileViewer.__init__', return_value=None):
        fv = FileViewer.__new__(FileViewer)
        fv.settings = {
            "use_mpv": False,
            "mpv_path": "/usr/bin/mpv",
            "mpv_fullscreen": False,
            "mpv_volume": 100,
            "mpv_custom_args": "",
            "mpv_screen": "Default",
        }
        fv.channel_name = "Test Channel"
        fv.channel_folder = "data/videos/test_channel"
        fv.geometry_key = "file_viewer_Test Channel_geometry"
        fv.script_path = "/scripts/delayed-fullscreen.lua"
        fv.selected_file_path = None
        fv.on_close_callback = MagicMock()
        fv.file_tree = MagicMock()
        fv.geometry = MagicMock(return_value="800x600+100+100")
        fv.destroy = MagicMock()
        yield fv


# --- GUI play tests ---

def test_play_latest_default_player(gui, tmp_path):
    channel_folder = tmp_path / "data" / "videos" / "test_channel"
    channel_folder.mkdir(parents=True)
    (channel_folder / "video.mp4").write_text("content")
    channel = {"name": "Test Channel", "folder": "test_channel"}

    with patch('app.frontend.gui.play_video', return_value=None) as mock_play:
        gui._worker_play(channel)
        mock_play.assert_called_once()
        gui._set_status.assert_any_call("Launched video player for Test Channel.")


def test_play_latest_mpv(gui, tmp_path):
    channel_folder = tmp_path / "data" / "videos" / "test_channel"
    channel_folder.mkdir(parents=True)
    (channel_folder / "video.mp4").write_text("content")
    gui.settings["use_mpv"] = True

    channel = {"name": "Test Channel", "folder": "test_channel"}
    with patch('app.frontend.gui.play_video', return_value=None) as mock_play:
        gui._worker_play(channel)
        mock_play.assert_called_once()
        # Verify settings were passed
        call_args = mock_play.call_args
        assert call_args.args[0] == gui.settings


def test_play_latest_error(gui, tmp_path):
    channel_folder = tmp_path / "data" / "videos" / "test_channel"
    channel_folder.mkdir(parents=True)
    (channel_folder / "video.mp4").write_text("content")
    channel = {"name": "Test Channel", "folder": "test_channel"}

    with patch('app.frontend.gui.play_video', return_value="Player crashed"):
        with patch('app.frontend.gui.messagebox.showerror') as mock_err:
            gui._worker_play(channel)
            gui._set_status.assert_any_call("Error playing video: Player crashed")
            mock_err.assert_called_once()


def test_play_latest_no_folder(gui):
    channel = {"name": "Test Channel", "folder": "test_channel"}
    gui._worker_play(channel)
    gui._set_status.assert_any_call("No videos downloaded for Test Channel yet.")


def test_play_latest_empty_folder(gui, tmp_path):
    channel_folder = tmp_path / "data" / "videos" / "test_channel"
    channel_folder.mkdir(parents=True)
    channel = {"name": "Test Channel", "folder": "test_channel"}
    gui._worker_play(channel)
    gui._set_status.assert_any_call("No videos found for Test Channel.")


# --- FileViewer tests ---

def test_file_viewer_play_selected_no_selection(file_viewer):
    with patch('app.frontend.file_viewer.messagebox.showwarning') as mock_warn:
        file_viewer.play_selected()
        mock_warn.assert_called_once()


def test_file_viewer_play_selected_success(file_viewer, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_text("content")
    file_viewer.selected_file_path = str(video)

    with patch('app.frontend.file_viewer.play_video', return_value=None) as mock_play:
        file_viewer.play_selected()
        mock_play.assert_called_once_with(file_viewer.settings, str(video), file_viewer.script_path)


def test_file_viewer_play_selected_error(file_viewer, tmp_path):
    video = tmp_path / "video.mp4"
    video.write_text("content")
    file_viewer.selected_file_path = str(video)

    with patch('app.frontend.file_viewer.play_video', return_value="MPV error"):
        with patch('app.frontend.file_viewer.messagebox.showerror') as mock_err:
            file_viewer.play_selected()
            mock_err.assert_called_once()


def test_file_viewer_load_position_exists(file_viewer):
    file_viewer.settings["file_viewer_Test Channel_geometry"] = "100x200+10+20"
    file_viewer.load_window_position()
    file_viewer.geometry.assert_called_with("100x200+10+20")


def test_file_viewer_load_position_default(file_viewer):
    file_viewer.load_window_position()
    file_viewer.geometry.assert_called_with("362x329+1223+406")


def test_file_viewer_on_closing(file_viewer):
    with patch('app.frontend.file_viewer.save_settings') as mock_save:
        file_viewer.on_closing()
        mock_save.assert_called_once_with(file_viewer.settings)
        file_viewer.on_close_callback.assert_called_once_with(file_viewer.channel_folder)
        file_viewer.destroy.assert_called_once()


def test_file_viewer_populate_files_empty(file_viewer, tmp_path):
    folder = tmp_path / "channel"
    folder.mkdir()
    file_viewer.channel_folder = str(folder)
    file_viewer.populate_files()
    file_viewer.file_tree.insert.assert_not_called()


def test_file_viewer_populate_files_with_files(file_viewer, tmp_path):
    folder = tmp_path / "channel"
    folder.mkdir()
    (folder / "video1.mp4").write_text("a")
    (folder / "video2.mp4").write_text("b")
    file_viewer.channel_folder = str(folder)
    file_viewer.file_tree.get_children.return_value = []
    file_viewer.populate_files()
    assert file_viewer.file_tree.insert.call_count == 2


def test_file_viewer_populate_files_nonexistent(file_viewer):
    file_viewer.channel_folder = "/nonexistent/path"
    file_viewer.populate_files()
    file_viewer.file_tree.insert.assert_not_called()


def test_file_viewer_on_file_select(file_viewer):
    file_viewer.file_tree.focus.return_value = "I001"
    file_viewer.file_tree.item.return_value = {"values": ["video.mp4", ""]}
    file_viewer.file_tree.get_children.return_value = ["I001"]
    file_viewer.channel_folder = "/path/to/channel"
    file_viewer.on_file_select(None)
    assert file_viewer.selected_file_path == os.path.join("/path/to/channel", "video.mp4")


def test_file_viewer_on_file_select_none(file_viewer):
    file_viewer.file_tree.focus.return_value = ""
    file_viewer.file_tree.get_children.return_value = []
    file_viewer.on_file_select(None)
    assert file_viewer.selected_file_path is None
