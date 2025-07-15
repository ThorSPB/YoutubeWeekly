import pytest
import os
import sys
from unittest.mock import patch, MagicMock, call
import tkinter as tk
from app.frontend.gui import YoutubeWeeklyGUI

@pytest.fixture
def mock_gui_instance_for_gui_tests(monkeypatch):
    with patch('app.backend.config.load_settings') as mock_load_settings:
        with patch('app.backend.config.load_channels') as mock_load_channels:
            mock_load_settings.return_value = {
                "video_folder": "data/videos",
                "use_mpv": False,
                "mpv_path": "/usr/bin/mpv",
                "mpv_fullscreen": False,
                "mpv_volume": 100,
                "mpv_custom_args": "",
                "mpv_screen": "Default",
                "main_window_geometry": "500x300+50+50"
            }
            mock_load_channels.return_value = {
                "test_channel": {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
            }
        
            with patch('app.frontend.gui.YoutubeWeeklyGUI.__init__', return_value=None):
                gui = YoutubeWeeklyGUI()
                gui.settings = mock_load_settings.return_value
                gui.base_path = gui.settings["video_folder"]
                gui.status_var = MagicMock()
                gui.status_label = MagicMock()
                
                # Directly assign MagicMock instances for StringVar-like objects
                gui.channel_quality_vars = {"Test Channel": MagicMock()}
                gui.channel_quality_vars["Test Channel"].get.return_value = "1080p"
                
                gui.others_quality_var = MagicMock()
                gui.others_quality_var.get.return_value = "720p"
                
                gui.others_link_var = MagicMock()
                gui.others_link_var.get.return_value = "http://youtube.com/watch?v=test"
                
                gui.channel_date_vars = {"Test Channel": MagicMock()}
                gui.channel_date_vars["Test Channel"].get.return_value = "automat"

                gui.geometry = MagicMock(return_value="500x300+50+50")
                gui.destroy = MagicMock()
                gui.update_idletasks = MagicMock()
                gui.recent_sabbaths_per_channel = {"Test Channel": ["automat", "15.07.2024"]}
                yield gui

def test_gui_load_window_position_exists(mock_gui_instance_for_gui_tests):
    mock_gui_instance_for_gui_tests.load_window_position()
    mock_gui_instance_for_gui_tests.geometry.assert_called_once_with("500x300+50+50")

def test_gui_load_window_position_not_exists(mock_gui_instance_for_gui_tests):
    del mock_gui_instance_for_gui_tests.settings["main_window_geometry"]
    mock_gui_instance_for_gui_tests.load_window_position()
    mock_gui_instance_for_gui_tests.geometry.assert_not_called()

def test_gui_on_closing(mock_gui_instance_for_gui_tests):
    with patch('app.frontend.gui.save_settings') as mock_save_settings:
        mock_gui_instance_for_gui_tests.on_closing()
        mock_save_settings.assert_called_once_with(mock_gui_instance_for_gui_tests.settings)
        mock_gui_instance_for_gui_tests.destroy.assert_called_once()

@pytest.mark.parametrize("text, expected_color", [
    ("Video already exists", "yellow"),
    ("No video found", "red"),
    ("Download complete.", "green"),
    ("Error downloading.", "red"),
    ("Some other message", "#ffffff"),
])
def test_gui_set_status(mock_gui_instance_for_gui_tests, text, expected_color):
    mock_gui_instance_for_gui_tests._set_status(text)
    mock_gui_instance_for_gui_tests.status_label.config.assert_called_once_with(fg=expected_color)
    mock_gui_instance_for_gui_tests.status_var.set.assert_called_once_with(text)
    mock_gui_instance_for_gui_tests.update_idletasks.assert_called_once()

def test_gui_send_notification_enabled(mock_gui_instance_for_gui_tests):
    mock_gui_instance_for_gui_tests.settings["enable_notifications"] = True
    with patch('app.frontend.gui.notification.notify') as mock_notify:
        mock_gui_instance_for_gui_tests._send_notification("Test Title", "Test Message")
        mock_notify.assert_called_once_with(
            title="Test Title",
            message="Test Message",
            app_name="YoutubeWeekly Downloader",
            timeout=10
        )

def test_gui_send_notification_disabled(mock_gui_instance_for_gui_tests):
    mock_gui_instance_for_gui_tests.settings["enable_notifications"] = False
    with patch('app.frontend.gui.notification.notify') as mock_notify:
        mock_gui_instance_for_gui_tests._send_notification("Test Title", "Test Message")
        mock_notify.assert_not_called()

def test_gui_send_notification_error(mock_gui_instance_for_gui_tests):
    mock_gui_instance_for_gui_tests.settings["enable_notifications"] = True
    with patch('app.frontend.gui.notification.notify', side_effect=Exception("Notification error")) as mock_notify:
        with patch('builtins.print') as mock_print:
            mock_gui_instance_for_gui_tests._send_notification("Test Title", "Test Message")
            mock_notify.assert_called_once()
            mock_print.assert_called_once_with("Error sending notification: Notification error")

def test_gui_download_for_channel(mock_gui_instance_for_gui_tests):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
    with patch('app.frontend.gui.threading.Thread') as mock_thread:
        mock_gui_instance_for_gui_tests.download_for_channel(channel)
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        assert kwargs['target'] == mock_gui_instance_for_gui_tests._worker_download
        assert kwargs['args'] == (channel,)
        assert kwargs['daemon'] == True
        mock_thread.return_value.start.assert_called_once()

def test_gui_download_others_no_link(mock_gui_instance_for_gui_tests):
    mock_gui_instance_for_gui_tests.others_link_var.get.return_value = ""
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    mock_gui_instance_for_gui_tests.download_others()
    # Check that the final status message is correct
    mock_gui_instance_for_gui_tests._set_status.assert_called_once_with("Please enter a YouTube link.")

def test_gui_download_others_with_link(mock_gui_instance_for_gui_tests):
    mock_gui_instance_for_gui_tests.others_link_var.get.return_value = "http://youtube.com/watch?v=test"
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    with patch('app.frontend.gui.threading.Thread') as mock_thread:
        mock_gui_instance_for_gui_tests.download_others()
        mock_gui_instance_for_gui_tests._set_status.assert_called_once_with("Starting download...")
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        assert kwargs['target'] == mock_gui_instance_for_gui_tests._worker_download_others
        assert kwargs['args'] == ("http://youtube.com/watch?v=test",)
        assert kwargs['daemon'] == True
        mock_thread.return_value.start.assert_called_once()

def test_gui_play_others(mock_gui_instance_for_gui_tests):
    with patch('app.frontend.gui.threading.Thread') as mock_thread:
        mock_gui_instance_for_gui_tests.play_others()
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        assert kwargs['target'] == mock_gui_instance_for_gui_tests._worker_play_others
        assert kwargs['daemon'] == True
        mock_thread.return_value.start.assert_called_once()

def test_gui_open_others_folder(mock_gui_instance_for_gui_tests):
    with patch('app.frontend.gui.FileViewer') as mock_file_viewer:
        mock_gui_instance_for_gui_tests.open_others_folder()
        mock_file_viewer.assert_called_once_with(
            mock_gui_instance_for_gui_tests,
            mock_gui_instance_for_gui_tests.settings,
            "Others",
            os.path.join(mock_gui_instance_for_gui_tests.base_path, "other")
        )
        mock_file_viewer.return_value.transient.assert_called_once_with(mock_gui_instance_for_gui_tests)
        mock_file_viewer.return_value.focus_set.assert_called_once()

def test_gui_worker_download_others_success(mock_gui_instance_for_gui_tests):
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    mock_gui_instance_for_gui_tests._send_notification = MagicMock()
    with patch('app.frontend.gui.download_video') as mock_download_video:
        mock_gui_instance_for_gui_tests._worker_download_others("http://youtube.com/watch?v=test")
        mock_download_video.assert_called_once_with(
                "http://youtube.com/watch?v=test",
                os.path.join(mock_gui_instance_for_gui_tests.base_path, "other"),
                mock_gui_instance_for_gui_tests.others_quality_var.get()
            )
        mock_gui_instance_for_gui_tests._set_status.assert_called_once_with("Download complete.")
        mock_gui_instance_for_gui_tests._send_notification.assert_called_once_with(
            "Download Complete",
            "Finished downloading video from link: http://youtube.com/watch?v=test"
        )

def test_gui_worker_download_others_failure(mock_gui_instance_for_gui_tests):
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    mock_gui_instance_for_gui_tests._send_notification = MagicMock()
    with patch('app.frontend.gui.download_video', side_effect=Exception("Download error")) as mock_download_video:
        with patch('app.frontend.gui.messagebox.showerror') as mock_messagebox:
            mock_gui_instance_for_gui_tests._worker_download_others("http://youtube.com/watch?v=test")
            mock_download_video.assert_called_once()
            mock_gui_instance_for_gui_tests._set_status.assert_called_once_with("Error downloading.")
            mock_gui_instance_for_gui_tests._send_notification.assert_called_once_with(
                "Download Error",
                "Failed to download video from link: http://youtube.com/watch?v=test"
            )
            mock_messagebox.assert_called_once()

def test_gui_worker_play_others_no_folder(mock_gui_instance_for_gui_tests, monkeypatch):
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    monkeypatch.setattr(os.path, "exists", MagicMock(return_value=False))
    mock_gui_instance_for_gui_tests._worker_play_others()
    # Check that both status calls are made
    expected_calls = [call("Searching for latest video in Others..."), call("No videos downloaded for Others yet.")]
    mock_gui_instance_for_gui_tests._set_status.assert_has_calls(expected_calls)

def test_gui_worker_play_others_no_files(mock_gui_instance_for_gui_tests, monkeypatch, tmp_path):
    other_folder = tmp_path / "other"
    other_folder.mkdir()
    mock_gui_instance_for_gui_tests.base_path = str(tmp_path)
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    monkeypatch.setattr(os.path, "exists", MagicMock(return_value=True))
    monkeypatch.setattr(os, "listdir", MagicMock(return_value=[]))
    mock_gui_instance_for_gui_tests._worker_play_others()
    # Check that both status calls are made
    expected_calls = [call("Searching for latest video in Others..."), call("No videos found for Others.")]
    mock_gui_instance_for_gui_tests._set_status.assert_has_calls(expected_calls)

def test_gui_worker_play_others_mpv(mock_gui_instance_for_gui_tests, monkeypatch, tmp_path):
    other_folder = tmp_path / "other"
    other_folder.mkdir()
    dummy_video = other_folder / "video.mp4"
    dummy_video.write_text("content")
    mock_gui_instance_for_gui_tests.base_path = str(tmp_path)
    mock_gui_instance_for_gui_tests.settings["use_mpv"] = True
    mock_gui_instance_for_gui_tests.settings["mpv_path"] = "/usr/bin/mpv"
    mock_gui_instance_for_gui_tests.settings["mpv_fullscreen"] = True
    mock_gui_instance_for_gui_tests.settings["mpv_volume"] = 50
    mock_gui_instance_for_gui_tests.settings["mpv_custom_args"] = "--no-config"
    mock_gui_instance_for_gui_tests.settings["mpv_screen"] = "1"
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    monkeypatch.setattr(os.path, "exists", MagicMock(return_value=True))
    monkeypatch.setattr(os, "listdir", MagicMock(return_value=["video.mp4"]))
    monkeypatch.setattr(os.path, "getctime", lambda x: 100 if "video.mp4" in str(x) else 0)

    with patch('app.frontend.gui.subprocess.Popen') as mock_popen:
        mock_gui_instance_for_gui_tests._worker_play_others()
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert args[0][0] == "/usr/bin/mpv"
        assert str(dummy_video) in args[0]
        assert "--fullscreen" in args[0]
        assert "--volume=50" in args[0]
        assert "--no-config" in args[0]
        assert "--screen=1" in args[0]
        # Check that the final status message is correct
        expected_calls = [call("Searching for latest video in Others..."), call(f"Playing {dummy_video.name}...",), call("Launched video player for Others.")]
        mock_gui_instance_for_gui_tests._set_status.assert_has_calls(expected_calls)

def test_gui_worker_play_others_default_player(mock_gui_instance_for_gui_tests, monkeypatch, tmp_path):
    other_folder = tmp_path / "other"
    other_folder.mkdir()
    dummy_video = other_folder / "video.mp4"
    dummy_video.write_text("content")
    mock_gui_instance_for_gui_tests.base_path = str(tmp_path)
    mock_gui_instance_for_gui_tests.settings["use_mpv"] = False
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    monkeypatch.setattr(os.path, "exists", MagicMock(return_value=True))
    monkeypatch.setattr(os, "listdir", MagicMock(return_value=["video.mp4"]))
    monkeypatch.setattr(os.path, "getctime", lambda x: 100 if "video.mp4" in str(x) else 0)

    if os.name == 'nt':
        with patch('app.frontend.gui.os.startfile') as mock_startfile:
            mock_gui_instance_for_gui_tests._worker_play_others()
            mock_startfile.assert_called_once_with(str(dummy_video))
    else:
        with patch('app.frontend.gui.subprocess.call') as mock_call:
            mock_gui_instance_for_gui_tests._worker_play_others()
            mock_call.assert_called_once()
            args, kwargs = mock_call.call_args
            assert str(dummy_video) in args[0]
    # Check that the final status message is correct
    expected_calls = [call("Searching for latest video in Others..."), call(f"Playing {dummy_video.name}..."), call("Launched video player for Others.")]
    mock_gui_instance_for_gui_tests._set_status.assert_has_calls(expected_calls)

def test_gui_worker_play_others_error(mock_gui_instance_for_gui_tests, monkeypatch, tmp_path):
    other_folder = tmp_path / "other"
    other_folder.mkdir()
    dummy_video = other_folder / "video.mp4"
    dummy_video.write_text("content")
    mock_gui_instance_for_gui_tests.base_path = str(tmp_path)
    # Ensure use_mpv is False to match the code path we are testing
    mock_gui_instance_for_gui_tests.settings["use_mpv"] = False 
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    monkeypatch.setattr(os.path, "exists", MagicMock(return_value=True))
    monkeypatch.setattr(os, "listdir", MagicMock(return_value=["video.mp4"]))
    monkeypatch.setattr(os.path, "getctime", lambda x: 100 if "video.mp4" in str(x) else 0)

    # Patch the correct function (os.startfile for Windows default player)
    with patch('app.frontend.gui.os.startfile', side_effect=Exception("Playback error")):
        with patch('app.frontend.gui.messagebox.showerror') as mock_messagebox:
            mock_gui_instance_for_gui_tests._worker_play_others()
            # Check that the error status message is called
            expected_calls = [
                call("Searching for latest video in Others..."), 
                call(f"Playing {dummy_video.name}..."), 
                call("Error playing video: Playback error")
            ]
            mock_gui_instance_for_gui_tests._set_status.assert_has_calls(expected_calls)
            mock_messagebox.assert_called_once()

def test_gui_worker_download_channel_success(mock_gui_instance_for_gui_tests, monkeypatch):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel", "date_format": "%d.%m.%Y"}
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    mock_gui_instance_for_gui_tests._send_notification = MagicMock()
    mock_gui_instance_for_gui_tests.channel_date_vars["Test Channel"].get.return_value = "automat"

    with patch('app.frontend.gui.get_next_saturday', return_value="15.07.2024") as mock_get_next_saturday:
        with patch('app.frontend.gui.find_video_url', return_value="http://youtube.com/watch?v=found") as mock_find_video_url:
            with patch('app.frontend.gui.os.makedirs') as mock_makedirs:
                with patch('app.frontend.gui.os.listdir', return_value=[]) as mock_listdir:
                    with patch('app.frontend.gui.delete_old_videos') as mock_delete_old_videos:
                        with patch('app.frontend.gui.download_video') as mock_download_video:
                            # Mock tk.StringVar to prevent Tkinter initialization
                            with patch('tkinter.StringVar') as mock_string_var:
                                mock_string_var_instance = MagicMock()
                                mock_string_var_instance.get.return_value = "automat"
                                mock_string_var.return_value = mock_string_var_instance

                                mock_gui_instance_for_gui_tests._worker_download(channel)

                                mock_get_next_saturday.assert_called_once()
                                mock_find_video_url.assert_called_once_with("http://example.com", "15.07.2024", date_format="%d.%m.%Y")
                                mock_makedirs.assert_called_once_with(os.path.join(mock_gui_instance_for_gui_tests.base_path, "test_channel"), exist_ok=True)
                                mock_listdir.assert_called_once_with(os.path.join(mock_gui_instance_for_gui_tests.base_path, "test_channel"))
                                mock_delete_old_videos.assert_called_once_with(os.path.join(mock_gui_instance_for_gui_tests.base_path, "test_channel"), keep_old=False)
                                mock_download_video.assert_called_once_with(
                                    "http://youtube.com/watch?v=found",
                                    os.path.join(mock_gui_instance_for_gui_tests.base_path, "test_channel"),
                                    "1080p",
                                    protect=False
                                )
                                mock_gui_instance_for_gui_tests._set_status.assert_has_calls([
                                    call(f"Finding video for {channel['name']}..."),
                                    call(f"Downloading from {channel['name']} ({mock_gui_instance_for_gui_tests.channel_quality_vars["Test Channel"].get()})..."),
                                    call(f"Download complete for {channel['name']}.")
                                ])
                                mock_gui_instance_for_gui_tests._send_notification.assert_called_with("Download Complete", "Finished downloading video for Test Channel.")

def test_gui_worker_download_channel_no_video(mock_gui_instance_for_gui_tests, monkeypatch):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel", "date_format": "%d.%m.%Y"}
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    mock_gui_instance_for_gui_tests._send_notification = MagicMock()
    mock_gui_instance_for_gui_tests.channel_date_vars["Test Channel"].get.return_value = "automat"

    with patch('app.frontend.gui.get_next_saturday', return_value="15.07.2024"):
        with patch('app.frontend.gui.find_video_url', return_value=None) as mock_find_video_url:
            # Mock tk.StringVar to prevent Tkinter initialization
            with patch('tkinter.StringVar') as mock_string_var:
                mock_string_var_instance = MagicMock()
                mock_string_var_instance.get.return_value = "automat"
                mock_string_var.return_value = mock_string_var_instance

                mock_gui_instance_for_gui_tests._worker_download(channel)

                mock_find_video_url.assert_called_once()
                expected_calls = [call(f"Finding video for {channel['name']}..."), call(f"No video found for {channel['name']} on 15.07.2024.")]
                mock_gui_instance_for_gui_tests._set_status.assert_has_calls(expected_calls)
                mock_gui_instance_for_gui_tests._send_notification.assert_called_once_with("Video Not Found", "No video found for Test Channel on 15.07.2024.")

def test_gui_worker_download_channel_already_exists(mock_gui_instance_for_gui_tests, monkeypatch):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel", "date_format": "%d.%m.%Y"}
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    mock_gui_instance_for_gui_tests.channel_date_vars["Test Channel"].get.return_value = "automat"

    with patch('app.frontend.gui.get_next_saturday', return_value="15.07.2024"):
        with patch('app.frontend.gui.find_video_url', return_value="http://youtube.com/watch?v=found"):
            with patch('app.frontend.gui.os.listdir', return_value=["video_15.07.2024.mp4"]) as mock_listdir:
                # Mock tk.StringVar to prevent Tkinter initialization
                with patch('tkinter.StringVar') as mock_string_var:
                    mock_string_var_instance = MagicMock()
                    mock_string_var_instance.get.return_value = "automat"
                    mock_string_var.return_value = mock_string_var_instance

                    mock_gui_instance_for_gui_tests._worker_download(channel)

                    mock_listdir.assert_called_once()
                    expected_calls = [call(f"Finding video for {channel['name']}..."), call(f"Video for {channel['name']} already exists: video_15.07.2024.mp4")]
                    mock_gui_instance_for_gui_tests._set_status.assert_has_calls(expected_calls)

def test_gui_worker_download_channel_download_failure(mock_gui_instance_for_gui_tests, monkeypatch):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel", "date_format": "%d.%m.%Y"}
    mock_gui_instance_for_gui_tests._set_status = MagicMock()
    mock_gui_instance_for_gui_tests._send_notification = MagicMock()
    mock_gui_instance_for_gui_tests.channel_date_vars["Test Channel"].get.return_value = "automat"

    with patch('app.frontend.gui.get_next_saturday', return_value="15.07.2024"):
        with patch('app.frontend.gui.find_video_url', return_value="http://youtube.com/watch?v=found"):
            with patch('app.frontend.gui.os.makedirs'):
                with patch('app.frontend.gui.os.listdir', return_value=[]):
                    with patch('app.frontend.gui.delete_old_videos'):
                        with patch('app.frontend.gui.download_video', side_effect=Exception("Download error")) as mock_download_video:
                            with patch('app.frontend.gui.messagebox.showerror') as mock_messagebox:
                                # Mock tk.StringVar to prevent Tkinter initialization
                                with patch('tkinter.StringVar') as mock_string_var:
                                    mock_string_var_instance = MagicMock()
                                    mock_string_var_instance.get.return_value = "automat"
                                    mock_string_var.return_value = mock_string_var_instance

                                    mock_gui_instance_for_gui_tests._worker_download(channel)

                                    mock_download_video.assert_called_once()
                                    expected_calls = [
                                        call(f"Finding video for {channel['name']}..."),
                                        call(f"Downloading from {channel['name']} ({mock_gui_instance_for_gui_tests.channel_quality_vars["Test Channel"].get()})..."),
                                        call(f"Error downloading {channel['name']}.")
                                    ]
                                    mock_gui_instance_for_gui_tests._set_status.assert_has_calls(expected_calls)
                                    mock_gui_instance_for_gui_tests._send_notification.assert_called_once_with("Download Error", "Failed to download video for Test Channel.")
                                    mock_messagebox.assert_called_once()

def test_gui_play_latest(mock_gui_instance_for_gui_tests):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
    with patch('app.frontend.gui.threading.Thread') as mock_thread:
        mock_gui_instance_for_gui_tests.play_latest(channel)
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        assert kwargs['target'] == mock_gui_instance_for_gui_tests._worker_play
        assert kwargs['args'] == (channel,)
        assert kwargs['daemon'] == True
        mock_thread.return_value.start.assert_called_once()

def test_gui_open_channel_folder(mock_gui_instance_for_gui_tests):
    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
    with patch('app.frontend.gui.FileViewer') as mock_file_viewer:
        mock_gui_instance_for_gui_tests.open_channel_folder(channel)
        mock_file_viewer.assert_called_once_with(
            mock_gui_instance_for_gui_tests,
            mock_gui_instance_for_gui_tests.settings,
            "Test Channel",
            os.path.join(mock_gui_instance_for_gui_tests.base_path, "test_channel")
        )
        mock_file_viewer.return_value.transient.assert_called_once_with(mock_gui_instance_for_gui_tests)
        mock_file_viewer.return_value.focus_set.assert_called_once()