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
        "last_sabbath_checked": None,
        "use_mpv": False,
        "mpv_path": "",
        "mpv_fullscreen": False,
        "mpv_volume": 100,
        "mpv_custom_args": "",
        "mpv_screen": "Default"
    }
    with open(test_settings_path, "w") as f:
        json.dump(initial_settings, f)
    return test_settings_path

def test_load_settings(mock_settings_file, monkeypatch):
    # Temporarily change the SETTINGS_FILE path to our mock file
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(mock_settings_file))

    settings, warnings = load_settings()
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
    assert "use_mpv" in settings, "Missing 'use_mpv' in settings"
    assert isinstance(settings["use_mpv"], bool), "'use_mpv' is not a boolean"
    assert settings["use_mpv"] == False, "Default for 'use_mpv' should be False"
    assert "mpv_path" in settings, "Missing 'mpv_path' in settings"
    assert isinstance(settings["mpv_path"], str), "'mpv_path' is not a string"
    # mpv_path is auto-detected from bundled executables, so don't assert specific value
    assert "mpv_fullscreen" in settings, "Missing 'mpv_fullscreen' in settings"
    assert isinstance(settings["mpv_fullscreen"], bool), "'mpv_fullscreen' is not a boolean"
    assert settings["mpv_fullscreen"] == False, "Default for 'mpv_fullscreen' should be False"
    assert "mpv_volume" in settings, "Missing 'mpv_volume' in settings"
    assert isinstance(settings["mpv_volume"], int), "'mpv_volume' is not an integer"
    assert settings["mpv_volume"] == 100, "Default for 'mpv_volume' should be 100"
    assert "mpv_custom_args" in settings, "Missing 'mpv_custom_args' in settings"
    assert isinstance(settings["mpv_custom_args"], str), "'mpv_custom_args' is not a string"
    assert settings["mpv_custom_args"] == "", "Default for 'mpv_custom_args' should be empty string"
    assert "mpv_screen" in settings, "Missing 'mpv_screen' in settings"
    assert isinstance(settings["mpv_screen"], str), "'mpv_screen' is not a string"
    assert settings["mpv_screen"] == "Default", "Default for 'mpv_screen' should be 'Default'"

def test_save_settings(mock_settings_file, monkeypatch):
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(mock_settings_file))

    settings, warnings = load_settings()
    settings["keep_old_videos"] = True
    settings["enable_auto_download"] = True
    settings["enable_notifications"] = False
    settings["main_window_geometry"] = "500x400+100+100"
    settings["settings_window_geometry"] = "300x200+50+50"
    settings["last_sabbath_checked"] = "2025-07-19"
    settings["use_mpv"] = True
    settings["mpv_path"] = "/usr/local/bin/mpv"
    settings["mpv_fullscreen"] = True
    settings["mpv_volume"] = 150
    settings["mpv_custom_args"] = "--no-border --ontop"
    settings["mpv_screen"] = "1"

    save_settings(settings)

    loaded_settings, _ = load_settings()
    assert loaded_settings["keep_old_videos"] == True
    assert loaded_settings["enable_auto_download"] == True
    assert loaded_settings["enable_notifications"] == False
    assert loaded_settings["main_window_geometry"] == "500x400+100+100"
    assert loaded_settings["settings_window_geometry"] == "300x200+50+50"
    assert loaded_settings["last_sabbath_checked"] == "2025-07-19"
    assert loaded_settings["use_mpv"] == True
    # mpv_path is always overridden by load_settings() with auto-detected bundled path
    # so we skip asserting the saved value and instead check that it's a string
    assert isinstance(loaded_settings["mpv_path"], str)
    assert loaded_settings["mpv_fullscreen"] == True
    assert loaded_settings["mpv_volume"] == 150
    assert loaded_settings["mpv_custom_args"] == "--no-border --ontop"
    assert loaded_settings["mpv_screen"] == "1"

def test_load_channels():
    channels = load_channels()
    assert "channel_1" in channels, "Missing 'channel_1' in channels"
    assert "url" in channels["channel_1"], "Channel URL is missing"


def test_load_settings_merges_missing_default_keys(tmp_path, monkeypatch):
    """v1.0.4-era settings file gets new keys filled in from bundled defaults."""
    legacy_path = tmp_path / "settings.json"
    legacy_settings = {
        "keep_old_videos": False,
        "video_folder": "data/videos",
        "default_quality": "1080p",
        "enable_auto_download": True,
        "enable_notifications": True,
        "use_mpv": False,
        "mpv_fullscreen": True,
    }
    with open(legacy_path, "w") as f:
        json.dump(legacy_settings, f)
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(legacy_path))

    settings, _ = load_settings()

    # Keys added in later versions should now be present
    assert "check_for_updates" in settings
    assert "auto_install_updates" in settings
    assert "send_telemetry" in settings

    # Existing user values must be preserved
    assert settings["default_quality"] == "1080p"
    assert settings["enable_auto_download"] is True

    # The merged result should have been persisted to disk
    with open(legacy_path, "r") as f:
        on_disk = json.load(f)
    assert "check_for_updates" in on_disk
    assert "send_telemetry" in on_disk


def test_load_settings_no_write_when_nothing_to_merge(tmp_path, monkeypatch):
    """Already-complete settings file is not rewritten on load."""
    from app.backend.config import load_default_settings

    complete_path = tmp_path / "settings.json"
    full = dict(load_default_settings())
    full["default_quality"] = "720p"  # mark to ensure user value survives
    with open(complete_path, "w") as f:
        json.dump(full, f)
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(complete_path))

    mtime_before = complete_path.stat().st_mtime_ns
    settings, _ = load_settings()
    mtime_after = complete_path.stat().st_mtime_ns

    assert mtime_after == mtime_before, "load_settings rewrote the file when no migration was needed"
    assert settings["default_quality"] == "720p"


# --- bundled JavaScript engine -------------------------------------------
#
# yt-dlp runs YouTube's own JavaScript to solve the signature / "n" challenge.
# Videos that demand it - every "Made for Kids" one - release no
# adaptive-format URL until it is solved, so without an engine every format
# above 360p is dropped and the download fails outright.

def _fake_bundle(tmp_path, monkeypatch, *, with_qjs, system="Linux", machine="x86_64"):
    """Point config at a fake app/ tree, optionally carrying a qjs binary."""
    import os
    app_dir = tmp_path / "app"
    (app_dir / "tools").mkdir(parents=True)
    if with_qjs:
        rel = {"Linux": ("quickjs_linux", "qjs"),
               "Windows": ("quickjs_win64", "qjs.exe"),
               "Darwin": (os.path.join("quickjs_macOS", machine_dir(machine)), "qjs")}[system]
        d = app_dir / "tools" / rel[0]
        d.mkdir(parents=True, exist_ok=True)
        exe = d / rel[1]
        exe.write_text("#!/bin/sh\nexit 0\n")
        exe.chmod(0o755)
    monkeypatch.setattr("app.backend.config.platform.system", lambda: system)
    monkeypatch.setattr("app.backend.config.platform.machine", lambda: machine)
    monkeypatch.setattr("app.backend.config.os.path.dirname",
                        lambda _p: str(app_dir / "backend"))
    return app_dir


def machine_dir(machine):
    return "arm64" if machine == "arm64" else "intel"


@pytest.mark.parametrize("system, machine, expected_tail", [
    ("Linux", "x86_64", ("quickjs_linux", "qjs")),
    ("Windows", "AMD64", ("quickjs_win64", "qjs.exe")),
    ("Darwin", "arm64", ("arm64", "qjs")),
    ("Darwin", "x86_64", ("intel", "qjs")),
])
def test_bundled_js_engine_is_found_on_every_platform(
        tmp_path, monkeypatch, system, machine, expected_tail):
    import os
    from app.backend.config import get_default_executable_paths
    _fake_bundle(tmp_path, monkeypatch, with_qjs=True, system=system, machine=machine)
    paths, _ = get_default_executable_paths()
    found = paths["js_runtime_path"]
    assert found, f"no js_runtime_path resolved for {system}/{machine}"
    assert os.path.basename(found) == expected_tail[1]
    assert expected_tail[0] in found


def test_missing_js_engine_is_silent_not_a_user_warning(tmp_path, monkeypatch):
    """A source checkout has no bundled binary, and there is nothing for the
    user to configure - it is not exposed in Settings. An empty path means
    "let yt-dlp auto-detect", which is the old behaviour, so nagging about it
    would be noise in the same list that reports a genuinely broken mpv."""
    from app.backend.config import get_default_executable_paths
    _fake_bundle(tmp_path, monkeypatch, with_qjs=False)
    paths, warnings = get_default_executable_paths()
    assert paths["js_runtime_path"] == ""
    assert not [w for w in warnings if "quickjs" in w.lower() or "javascript" in w.lower()]


def test_load_settings_always_resolves_the_js_engine(mock_settings_file, monkeypatch):
    """Like mpv_path and ffmpeg_path, it is recomputed on every load rather
    than trusted from the settings file - a saved path breaks the moment the
    app is updated or moved."""
    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(mock_settings_file))
    monkeypatch.setattr("app.backend.config.get_default_executable_paths",
                        lambda: ({"mpv_path": "", "ffmpeg_path": "",
                                  "js_runtime_path": "/bundled/qjs"}, []))
    settings, _ = load_settings()
    assert settings["js_runtime_path"] == "/bundled/qjs"
