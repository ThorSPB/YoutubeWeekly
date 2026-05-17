from app.backend.telemetry import _sanitize_settings


def test_sanitize_settings_includes_language():
    """language must be in the whitelist so the dashboard reports en/ro adoption."""
    full = {
        "keep_old_videos": True,
        "default_quality": "max",
        "enable_auto_download": True,
        "enable_notifications": False,
        "start_with_system": True,
        "check_for_updates": True,
        "auto_install_updates": False,
        "use_mpv": False,
        "mpv_fullscreen": True,
        "language": "ro",
    }
    out = _sanitize_settings(full)
    assert out["language"] == "ro"


def test_sanitize_settings_drops_sensitive_keys():
    """send_telemetry, install_id, paths, geometries must not leak through."""
    settings = {
        "default_quality": "1080p",
        "language": "en",
        "send_telemetry": False,
        "mpv_path": "C:\\Users\\someone\\mpv.exe",
        "ffmpeg_path": "/Users/secret/ffmpeg",
        "main_window_geometry": "515x285+674+440",
        "last_sabbath_checked": "2026-05-16",
    }
    out = _sanitize_settings(settings)
    for forbidden in ("send_telemetry", "mpv_path", "ffmpeg_path",
                      "main_window_geometry", "last_sabbath_checked"):
        assert forbidden not in out, f"{forbidden} leaked into the telemetry payload"
    assert out == {"default_quality": "1080p", "language": "en"}


def test_sanitize_settings_skips_missing_keys():
    """A user upgrading from v1.0.4 may lack newer keys — they shouldn't appear as None."""
    minimal = {"default_quality": "1080p"}
    out = _sanitize_settings(minimal)
    assert out == {"default_quality": "1080p"}
    assert "check_for_updates" not in out
