import pytest
import os
from unittest.mock import patch, MagicMock, call
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
            
            # Create a more comprehensive mock for FileViewer
            with patch('app.frontend.file_viewer.FileViewer.__init__', return_value=None):
                viewer = FileViewer.__new__(FileViewer)  # Create instance without calling __init__
                
                # Manually set the attributes that would normally be set by __init__
                viewer.settings = mock_load_settings.return_value
                viewer.channel_name = "Test Channel"
                viewer.geometry_key = f"file_viewer_{viewer.channel_name}_geometry"
                viewer.channel_folder = "data/videos/test_channel"
                viewer.selected_file_path = None
                
                # Mock GUI components to prevent Tkinter calls
                viewer.file_tree = MagicMock()
                viewer.geometry = MagicMock(return_value="800x600+100+100")
                viewer.destroy = MagicMock()
                
                # Keep the original play_selected method for testing
                viewer.play_selected = FileViewer.play_selected.__get__(viewer, FileViewer)
                
                yield viewer

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

# New tests for FileViewer
def test_file_viewer_load_window_position_exists(mock_file_viewer_instance):
    mock_file_viewer_instance.settings["file_viewer_Test Channel_geometry"] = "100x200+10+20"
    mock_file_viewer_instance.load_window_position()
    mock_file_viewer_instance.geometry.assert_called_once_with("100x200+10+20")

def test_file_viewer_load_window_position_not_exists(mock_file_viewer_instance):
    if "file_viewer_Test Channel_geometry" in mock_file_viewer_instance.settings:
        del mock_file_viewer_instance.settings["file_viewer_Test Channel_geometry"]
    mock_file_viewer_instance.load_window_position()
    mock_file_viewer_instance.geometry.assert_not_called()

def test_file_viewer_on_closing(mock_file_viewer_instance):
    with patch('app.frontend.file_viewer.save_settings') as mock_save_settings:
        mock_file_viewer_instance.on_closing()
        mock_save_settings.assert_called_once_with(mock_file_viewer_instance.settings)
        mock_file_viewer_instance.destroy.assert_called_once()

def test_file_viewer_populate_files_empty_folder(mock_file_viewer_instance, monkeypatch, tmp_path):
    empty_folder = tmp_path / "empty_channel"
    empty_folder.mkdir()
    mock_file_viewer_instance.channel_folder = str(empty_folder)
    monkeypatch.setattr(os, "listdir", MagicMock(return_value=[]))
    mock_file_viewer_instance.populate_files()
    mock_file_viewer_instance.file_tree.get_children.assert_called_once()
    mock_file_viewer_instance.file_tree.delete.assert_not_called()
    mock_file_viewer_instance.file_tree.insert.assert_not_called()

def test_file_viewer_populate_files_with_files(mock_file_viewer_instance, monkeypatch, tmp_path):
    folder_with_files = tmp_path / "channel_with_files"
    folder_with_files.mkdir()
    (folder_with_files / "video1.mp4").write_text("content")
    (folder_with_files / "video2.mp4").write_text("content")
    mock_file_viewer_instance.channel_folder = str(folder_with_files)
    monkeypatch.setattr(os, "listdir", MagicMock(return_value=["video1.mp4", "video2.mp4"]))
    monkeypatch.setattr(os.path, "isfile", MagicMock(return_value=True))
    mock_file_viewer_instance.file_tree.get_children.return_value = ["item1", "item2"]
    mock_file_viewer_instance.populate_files()
    mock_file_viewer_instance.file_tree.get_children.assert_called_once()
    mock_file_viewer_instance.file_tree.delete.assert_has_calls([
        call("item1"),
        call("item2")
    ])
    assert mock_file_viewer_instance.file_tree.insert.call_count == 2
    mock_file_viewer_instance.file_tree.insert.assert_any_call("", tk.END, values=("video1.mp4", ""))
    mock_file_viewer_instance.file_tree.insert.assert_any_call("", tk.END, values=("video2.mp4", ""))

def test_file_viewer_populate_files_folder_not_exists(mock_file_viewer_instance, monkeypatch):
    mock_file_viewer_instance.channel_folder = "/nonexistent/folder"
    monkeypatch.setattr(os.path, "exists", MagicMock(return_value=False))
    mock_file_viewer_instance.populate_files()
    mock_file_viewer_instance.file_tree.get_children.assert_not_called()

def test_file_viewer_on_file_select(mock_file_viewer_instance):
    # Simulate a file selection
    mock_file_viewer_instance.file_tree.focus.return_value = "I001"
    mock_file_viewer_instance.file_tree.item.return_value = {"values": ["selected_video.mp4", ""]}
    mock_file_viewer_instance.channel_folder = "/path/to/channel"

    mock_file_viewer_instance.on_file_select(None) # Event is not used

    mock_file_viewer_instance.file_tree.set.assert_called_with("I001", "selected", "✓")
    assert mock_file_viewer_instance.selected_file_path == os.path.join("/path/to/channel", "selected_video.mp4")

def test_file_viewer_on_file_select_no_selection(mock_file_viewer_instance):
    mock_file_viewer_instance.file_tree.focus.return_value = ""
    mock_file_viewer_instance.on_file_select(None)
    assert mock_file_viewer_instance.selected_file_path is None
    mock_file_viewer_instance.file_tree.set.assert_not_called()