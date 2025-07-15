import pytest
import os
from unittest.mock import patch, MagicMock
from app.frontend.gui import YoutubeWeeklyGUI
from app.frontend.file_viewer import FileViewer
import tkinter as tk
import subprocess
from app.backend.auto_downloader import AUTO_DOWNLOAD_LOG_FILE

@pytest.fixture
def mock_gui_instance(monkeypatch, tmp_path):
    with patch('app.backend.config.load_settings') as mock_load_settings:
        with patch('app.backend.config.load_channels') as mock_load_channels:
            monkeypatch.setattr("app.backend.auto_downloader.AUTO_DOWNLOAD_LOG_FILE", str(tmp_path / "auto_download_log.json"))
            
            mock_load_settings.return_value = {
                "video_folder": str(tmp_path / "data" / "videos"),
                "use_mpv": False,
                "mpv_path": "/usr/bin/mpv",
                "mpv_fullscreen": False,
                "mpv_volume": 100,
                "mpv_custom_args": "",
                "mpv_screen": "Default"
            }
            mock_load_channels.return_value = {
                "test_channel": {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
            }
            # Mock Tk and Toplevel to prevent GUI from opening during tests
            with patch('app.frontend.gui.YoutubeWeeklyGUI.__init__', return_value=None) as mock_gui_init:
                gui = YoutubeWeeklyGUI()
                # Manually set attributes that would normally be set by __init__
                gui.settings = mock_load_settings.return_value
                gui.base_path = gui.settings["video_folder"]
                gui._set_status = MagicMock() # Mock _set_status to prevent Tkinter calls
                yield gui
                mock_gui_init.assert_called_once()

@pytest.fixture
def mock_file_viewer_instance(monkeypatch):
    with patch('app.backend.config.load_settings') as mock_load_settings:
        with patch('app.backend.config.save_settings'):
            mock_load_settings.return_value = {
                "video_folder": "data/videos",
                "use_mpv": False,
                "mpv_path": "/usr/bin/mpv",
                "mpv_fullscreen": False,
                "mpv_volume": 100,
                "mpv_custom_args": "",
                "mpv_screen": "Default"
            }
            # Mock Tk and Toplevel to prevent GUI from opening during tests
            monkeypatch.setattr(tk, "Tk", MagicMock())
            monkeypatch.setattr(tk, "Toplevel", MagicMock())
            root = tk.Tk()
            root.withdraw()
            viewer = FileViewer(root, mock_load_settings.return_value, "Test Channel", "data/videos/test_channel")
            yield viewer
            viewer.destroy()
            root.destroy()

def test_play_latest_video_default_player(mock_gui_instance, tmp_path, monkeypatch):
    # Setup a dummy video file
    channel_folder = tmp_path / "data" / "videos" / "test_channel"
    channel_folder.mkdir(parents=True)
    dummy_video = channel_folder / "video.mp4"
    dummy_video.write_text("dummy video content")

    monkeypatch.setattr(mock_gui_instance, "base_path", str(tmp_path / "data" / "videos"))
    monkeypatch.setattr(os, "startfile", MagicMock())
    monkeypatch.setattr("subprocess.call", MagicMock())

    channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
    mock_gui_instance._worker_play(channel)

def test_play_latest_video_mpv(mock_gui_instance, tmp_path, monkeypatch):
    # Setup a dummy video file
    channel_folder = tmp_path / "data" / "videos" / "test_channel"
    channel_folder.mkdir(parents=True)
    dummy_video = channel_folder / "video.mp4"
    dummy_video.write_text("dummy video content")

    monkeypatch.setattr(mock_gui_instance, "base_path", str(tmp_path / "data" / "videos"))
    mock_gui_instance.settings["use_mpv"] = True
    mock_gui_instance.settings["mpv_path"] = "/usr/bin/mpv"
    mock_gui_instance.settings["mpv_fullscreen"] = True
    mock_gui_instance.settings["mpv_volume"] = 50
    mock_gui_instance.settings["mpv_custom_args"] = "--no-config"
    mock_gui_instance.settings["mpv_screen"] = "1"

    with patch('app.frontend.gui.subprocess.Popen') as mock_popen:
        channel = {"name": "Test Channel", "url": "http://example.com", "folder": "test_channel"}
        mock_gui_instance._worker_play(channel)

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "/usr/bin/mpv"
        assert str(dummy_video) in args
        assert "--fullscreen" in args
        assert "--volume=50" in args
        assert "--no-config" in args
        assert "--screen=1" in args

def test_file_viewer_play_selected_default_player(mock_file_viewer_instance, tmp_path, monkeypatch):
    # Setup a dummy video file
    channel_folder = tmp_path / "data" / "videos" / "test_channel"
    channel_folder.mkdir(parents=True)
    dummy_video = channel_folder / "selected_video.mp4"
    dummy_video.write_text("dummy video content")

    mock_file_viewer_instance.channel_folder = str(channel_folder)
    mock_file_viewer_instance.populate_files()
    mock_file_viewer_instance.selected_file_path = str(dummy_video)

    monkeypatch.setattr(os, "startfile", MagicMock()) # Mock for Windows
    monkeypatch.setattr("subprocess.call", MagicMock()) # Mock for Linux/macOS

    mock_file_viewer_instance.play_selected()

    if os.name == 'nt':
        os.startfile.assert_called_once_with(str(dummy_video))
    else:
        subprocess.call.assert_called_once()
        args = subprocess.call.call_args[0][0]
        assert str(dummy_video) in args

def test_file_viewer_play_selected_mpv(mock_file_viewer_instance, tmp_path, monkeypatch):
    # Setup a dummy video file
    channel_folder = tmp_path / "data" / "videos" / "test_channel"
    channel_folder.mkdir(parents=True)
    dummy_video = channel_folder / "selected_video.mp4"
    dummy_video.write_text("dummy video content")

    mock_file_viewer_instance.channel_folder = str(channel_folder)
    mock_file_viewer_instance.populate_files()
    mock_file_viewer_instance.selected_file_path = str(dummy_video)

    mock_file_viewer_instance.settings["use_mpv"] = True
    mock_file_viewer_instance.settings["mpv_path"] = "/usr/bin/mpv"
    mock_file_viewer_instance.settings["mpv_fullscreen"] = True
    mock_file_viewer_instance.settings["mpv_volume"] = 75
    mock_file_viewer_instance.settings["mpv_custom_args"] = "--no-osc"
    mock_file_viewer_instance.settings["mpv_screen"] = "0"

    with patch('subprocess.Popen') as mock_popen:
        mock_file_viewer_instance.play_selected()

        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "/usr/bin/mpv"
        assert str(dummy_video) in args
        assert "--fullscreen" in args
        assert "--volume=75" in args
        assert "--no-osc" in args
        assert "--screen=0" in args
