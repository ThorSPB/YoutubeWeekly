import pytest
import os
import sys
from unittest.mock import patch, MagicMock, call
import tkinter as tk
from app.frontend.gui import YoutubeWeeklyGUI


@pytest.fixture
def gui(monkeypatch):
    """Create a mock GUI instance with all required attributes."""
    with patch('app.frontend.gui.YoutubeWeeklyGUI.__init__', return_value=None):
        g = YoutubeWeeklyGUI()

        g.settings = {
            "video_folder": "data/videos",
            "use_mpv": False,
            "mpv_path": "/usr/bin/mpv",
            "mpv_fullscreen": False,
            "mpv_volume": 100,
            "mpv_custom_args": "",
            "mpv_screen": "Default",
            "main_window_geometry": "500x300+50+50",
            "enable_notifications": True,
            "keep_old_videos": False,
        }
        g.base_path = g.settings["video_folder"]
        g.status_var = MagicMock()
        g.status_label = MagicMock()
        g.progress_bar = MagicMock()
        g.tray_icon = MagicMock()
        g.downloading_channels = set()
        g.open_file_viewers = {}
        g.download_stage = 0
        g.last_progress_value = 0

        g.channel_quality_vars = {"Test Channel": MagicMock()}
        g.channel_quality_vars["Test Channel"].get.return_value = "1080p"
        g.channel_date_vars = {"Test Channel": MagicMock()}
        g.channel_date_vars["Test Channel"].get.return_value = "automat"

        g.others_quality_var = MagicMock()
        g.others_quality_var.get.return_value = "720p"
        g.others_link_var = MagicMock()
        g.others_link_var.get.return_value = "http://youtube.com/watch?v=test"

        g.geometry = MagicMock(return_value="500x300+50+50")
        g.destroy = MagicMock()
        g.update_idletasks = MagicMock()
        g.after = MagicMock()
        g.recent_sabbaths_per_channel = {"Test Channel": ["automat", "15.07.2024"]}

        yield g


# --- Window position tests ---

def test_load_window_position_exists(gui):
    gui.load_window_position()
    gui.geometry.assert_called_once_with("500x300+50+50")


def test_load_window_position_not_exists(gui):
    del gui.settings["main_window_geometry"]
    gui.load_window_position()
    gui.geometry.assert_not_called()


# --- Status label tests ---

@pytest.mark.parametrize("text, expected_color", [
    ("Video already exists", "yellow"),
    ("No video found", "red"),
    ("Download complete.", "green"),
    ("Error downloading.", "red"),
    ("Some other message", "#ffffff"),
])
def test_set_status(gui, text, expected_color):
    gui._set_status(text)
    gui.status_label.config.assert_called_once_with(fg=expected_color)
    gui.status_var.set.assert_called_once_with(text)
    gui.update_idletasks.assert_called_once()


# --- Notification tests ---

def test_send_notification_disabled(gui):
    gui.settings["enable_notifications"] = False
    with patch('app.frontend.gui.notification.notify') as mock_notify:
        gui._send_notification("Title", "Message")
        mock_notify.assert_not_called()


def test_send_notification_error(gui):
    gui.settings["enable_notifications"] = True
    with patch('app.frontend.gui.notification.notify', side_effect=Exception("fail")):
        with patch('builtins.print') as mock_print:
            gui._send_notification("Title", "Message")
            mock_print.assert_called_once_with("Error sending notification: fail")


# --- Download channel tests ---

def test_download_for_channel(gui):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
    with patch('app.frontend.gui.threading.Thread') as mock_thread:
        gui.download_for_channel(channel)
        mock_thread.assert_called_once()
        assert mock_thread.call_args.kwargs['target'] == gui._worker_download
        assert mock_thread.call_args.kwargs['args'] == (channel,)
        mock_thread.return_value.start.assert_called_once()


def test_download_for_channel_already_downloading(gui):
    gui.downloading_channels.add("Test Channel")
    gui._set_status = MagicMock()
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
    gui.download_for_channel(channel)
    gui._set_status.assert_called_once_with("A download for Test Channel is already in progress.")


# --- Download others tests ---

def test_download_others_no_link(gui):
    gui.others_link_var.get.return_value = ""
    gui._set_status = MagicMock()
    gui.download_others()
    gui._set_status.assert_called_with("Please enter a YouTube link.")


def test_download_others_with_link(gui):
    gui._set_status = MagicMock()
    with patch('app.frontend.gui.threading.Thread') as mock_thread:
        gui.download_others()
        gui._set_status.assert_called_with("Starting download...")
        mock_thread.assert_called_once_with(
            target=gui._worker_download_others,
            args=(gui.others_link_var.get(),),
            daemon=True
        )
        mock_thread.return_value.start.assert_called_once()


# --- Play tests ---

def test_play_latest(gui):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
    with patch('app.frontend.gui.threading.Thread') as mock_thread:
        gui.play_latest(channel)
        mock_thread.assert_called_once_with(
            target=gui._worker_play,
            args=(channel,),
            daemon=True
        )
        mock_thread.return_value.start.assert_called_once()


def test_play_others(gui):
    with patch('app.frontend.gui.threading.Thread') as mock_thread:
        gui.play_others()
        mock_thread.assert_called_once_with(target=gui._worker_play_others, daemon=True)
        mock_thread.return_value.start.assert_called_once()


# --- Worker tests ---

def test_worker_play_others_no_folder(gui, monkeypatch):
    gui._set_status = MagicMock()
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    gui._worker_play_others()
    gui._set_status.assert_any_call("No videos downloaded for Others yet.")


def test_worker_play_others_no_files(gui, tmp_path):
    other_folder = tmp_path / "other"
    other_folder.mkdir()
    gui.base_path = str(tmp_path)
    gui._set_status = MagicMock()
    gui._worker_play_others()
    gui._set_status.assert_any_call("No videos found for Others.")


def test_worker_play_others_success(gui, tmp_path):
    other_folder = tmp_path / "other"
    other_folder.mkdir()
    (other_folder / "video.mp4").write_text("content")
    gui.base_path = str(tmp_path)
    gui._set_status = MagicMock()

    with patch('app.frontend.gui.play_video', return_value=None) as mock_play:
        gui._worker_play_others()
        mock_play.assert_called_once()
        gui._set_status.assert_any_call("Launched video player for Others.")


def test_worker_play_others_error(gui, tmp_path):
    other_folder = tmp_path / "other"
    other_folder.mkdir()
    (other_folder / "video.mp4").write_text("content")
    gui.base_path = str(tmp_path)
    gui._set_status = MagicMock()

    with patch('app.frontend.gui.play_video', return_value="Playback error"):
        with patch('app.frontend.gui.messagebox.showerror') as mock_err:
            gui._worker_play_others()
            gui._set_status.assert_any_call("Error playing video: Playback error")
            mock_err.assert_called_once()


def test_worker_play_channel_success(gui, tmp_path):
    channel_folder = tmp_path / "test_channel"
    channel_folder.mkdir()
    (channel_folder / "video.mp4").write_text("content")
    gui.base_path = str(tmp_path)
    gui._set_status = MagicMock()

    channel = {"name": "Test Channel", "folder": "test_channel"}
    with patch('app.frontend.gui.play_video', return_value=None) as mock_play:
        gui._worker_play(channel)
        mock_play.assert_called_once()
        gui._set_status.assert_any_call("Launched video player for Test Channel.")


def test_worker_download_others_success(gui, tmp_path):
    gui.base_path = str(tmp_path)
    gui._set_status = MagicMock()
    gui._send_notification = MagicMock()

    with patch('app.frontend.gui.download_video', return_value=None):
        gui._worker_download_others("http://youtube.com/watch?v=test")
        gui._set_status.assert_any_call("Download complete.")


def test_worker_download_others_error(gui, tmp_path):
    gui.base_path = str(tmp_path)
    gui._set_status = MagicMock()
    gui._send_notification = MagicMock()

    with patch('app.frontend.gui.download_video', return_value="Download failed"):
        with patch('app.frontend.gui.messagebox.showerror'):
            gui._worker_download_others("http://youtube.com/watch?v=test")
            gui._set_status.assert_any_call("Error downloading: Download failed")


def test_worker_download_channel_no_video(gui):
    gui._set_status = MagicMock()
    gui._send_notification = MagicMock()
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel", "date_format": "%d.%m.%Y"}

    with patch('app.frontend.gui.get_next_saturday', return_value="15.07.2024"):
        with patch('app.frontend.gui.find_video_url', return_value=(None, None)):
            with patch('app.frontend.gui.tk.StringVar', MagicMock):
                gui._worker_download(channel)
                gui._set_status.assert_any_call("No video found for Test Channel on 15.07.2024.")
                gui._send_notification.assert_called()


def test_worker_download_channel_already_exists(gui, tmp_path):
    gui.base_path = str(tmp_path)
    gui._set_status = MagicMock()
    channel_folder = tmp_path / "test_channel"
    channel_folder.mkdir()
    (channel_folder / "video_15.07.2024.mp4").write_text("content")
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel", "date_format": "%d.%m.%Y"}

    with patch('app.frontend.gui.get_next_saturday', return_value="15.07.2024"):
        with patch('app.frontend.gui.find_video_url', return_value=("http://youtube.com/watch?v=found", {"type": "exact", "title": "Found Video"})):
            with patch('app.frontend.gui.tk.StringVar', MagicMock):
                gui._worker_download(channel)
                gui._set_status.assert_any_call("Video for Test Channel already exists: video_15.07.2024.mp4")


# --- Open folder tests ---

def test_open_channel_folder(gui):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
    with patch('app.frontend.gui.FileViewer') as mock_fv:
        gui.open_channel_folder(channel)
        mock_fv.assert_called_once()
        assert mock_fv.call_args.args[2] == "Test Channel"


def test_open_others_folder(gui):
    with patch('app.frontend.gui.FileViewer') as mock_fv:
        gui.open_others_folder()
        mock_fv.assert_called_once()
        assert mock_fv.call_args.args[2] == "Others"
