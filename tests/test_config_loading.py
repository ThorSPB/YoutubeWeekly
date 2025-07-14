import pytest
import json
from app.backend.config import load_settings, load_channels, save_settings

# Mock settings file for testing
@pytest.fixture
def mock_settings_file(tmp_path):
    test_settings_path = tmp_path / "settings.json"
    initial_settings = {
        "keep_old_videos": False,
        "video_folder": "data/videos",
        "protected_videos": {
            "colecta": [],
            "scoala_de_sabat": [],
            "other": []
        },
        "enable_auto_download": False,
        "enable_notifications": True,
        "main_window_geometry": None,
        "settings_window_geometry": None,
        "last_sabbath_checked": None
    }
    with open(test_settings_path, "w") as f:
        json.dump(initial_settings, f)
    return test_settings_path

def test_load_settings(mock_settings_file, monkeypatch):
    # Temporarily change the SETTINGS_FILE path to our mock file
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(mock_settings_file))

    settings = load_settings()
    assert "keep_old_videos" in settings, "Missing 'keep_old_videos' in settings"
    assert isinstance(settings["keep_old_videos"], bool), "'keep_old_videos' is not a boolean"
    assert "enable_auto_download" in settings, "Missing 'enable_auto_download' in settings"
    assert isinstance(settings["enable_auto_download"], bool), "'enable_auto_download' is not a boolean"
    assert settings["enable_auto_download"] == False, "Default for 'enable_auto_download' should be False"
    assert "enable_notifications" in settings, "Missing 'enable_notifications' in settings"
    assert isinstance(settings["enable_notifications"], bool), "'enable_notifications' is not a boolean"
    assert settings["enable_notifications"] == True, "Default for 'enable_notifications' should be True"
    assert "main_window_geometry" in settings, "Missing 'main_window_geometry' in settings"
    assert settings["main_window_geometry"] is None or isinstance(settings["main_window_geometry"], str), "'main_window_geometry' is not a string or None"
    assert "settings_window_geometry" in settings, "Missing 'settings_window_geometry' in settings"
    assert settings["settings_window_geometry"] is None or isinstance(settings["settings_window_geometry"], str), "'settings_window_geometry' is not a string or None"
    assert "last_sabbath_checked" in settings, "Missing 'last_sabbath_checked' in settings"
    assert settings["last_sabbath_checked"] is None or isinstance(settings["last_sabbath_checked"], str), "'last_sabbath_checked' is not a string or None"

def test_save_settings(mock_settings_file, monkeypatch):
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(mock_settings_file))

    settings = load_settings()
    settings["keep_old_videos"] = True
    settings["enable_auto_download"] = True
    settings["enable_notifications"] = False
    settings["main_window_geometry"] = "500x400+100+100"
    settings["settings_window_geometry"] = "300x200+50+50"
    settings["last_sabbath_checked"] = "2025-07-19"

    save_settings(settings)

    loaded_settings = load_settings()
    assert loaded_settings["keep_old_videos"] == True
    assert loaded_settings["enable_auto_download"] == True
    assert loaded_settings["enable_notifications"] == False
    assert loaded_settings["main_window_geometry"] == "500x400+100+100"
    assert loaded_settings["settings_window_geometry"] == "300x200+50+50"
    assert loaded_settings["last_sabbath_checked"] == "2025-07-19"

def test_load_channels():
    channels = load_channels()
    assert "channel_1" in channels, "Missing 'channel_1' in channels"
    assert "url" in channels["channel_1"], "Channel URL is missing"
