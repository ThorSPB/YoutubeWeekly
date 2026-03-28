#!/usr/bin/env python3
"""
Validates configuration loading, saving, and schema.

Usage: python scripts/dry_run_config.py
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

EXPECTED_SETTINGS_KEYS = {
    "video_folder": str,
    "default_quality": str,
    "keep_old_videos": bool,
    "enable_auto_download": bool,
    "enable_notifications": bool,
    "use_mpv": bool,
    "mpv_fullscreen": bool,
    "mpv_volume": int,
    "mpv_screen": str,
    "mpv_custom_args": str,
}

EXPECTED_CHANNEL_KEYS = {"url"}  # Minimum required keys


def run_dry_run():
    print("=" * 60)
    print("YoutubeWeekly Config Validation Dry-Run")
    print("=" * 60)

    from app.backend.config import load_settings, save_settings, load_channels, get_default_executable_paths

    # Step 1: Load settings
    print("\n[1/4] Loading settings...")
    try:
        settings, warnings = load_settings()
        print(f"  OK - Loaded {len(settings)} keys")
        for w in warnings:
            print(f"  WARN: {w}")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    # Step 2: Validate settings schema
    print("\n[2/4] Validating settings schema...")
    errors = []
    for key, expected_type in EXPECTED_SETTINGS_KEYS.items():
        if key not in settings:
            # Some keys may come from the default file
            print(f"  SKIP: '{key}' not in current settings (may use default)")
            continue
        val = settings[key]
        if not isinstance(val, expected_type):
            errors.append(f"'{key}' expected {expected_type.__name__}, got {type(val).__name__}")
            print(f"  FAIL: {errors[-1]}")
        else:
            print(f"  OK - {key}: {val!r}")
    if errors:
        return 1

    # Step 3: Save/load roundtrip
    print("\n[3/4] Testing save/load roundtrip...")
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_settings = os.path.join(tmpdir, "settings.json")
        with open(tmp_settings, "w") as f:
            json.dump(settings, f)

        with patch("app.backend.config.SETTINGS_FILE", tmp_settings):
            settings["default_quality"] = "480p"
            save_settings(settings)

            reloaded, _ = load_settings()
            if reloaded["default_quality"] != "480p":
                print(f"  FAIL: Roundtrip failed, got {reloaded['default_quality']}")
                return 1
            print("  OK - Save/load roundtrip successful")

    # Step 4: Load channels
    print("\n[4/4] Loading and validating channels...")
    try:
        channels = load_channels()
        for key, ch in channels.items():
            missing = EXPECTED_CHANNEL_KEYS - set(ch.keys())
            if missing:
                print(f"  FAIL: Channel '{key}' missing keys: {missing}")
                return 1
            print(f"  OK - {key}: {ch.get('name', key)} -> {ch['url'][:50]}...")
    except Exception as e:
        print(f"  FAIL: {e}")
        return 1

    # Step 5: Executable paths
    print("\n[Bonus] Checking executable paths...")
    paths, path_warnings = get_default_executable_paths()
    print(f"  mpv: {paths['mpv_path'] or '(not found)'}")
    print(f"  ffmpeg: {paths['ffmpeg_path'] or '(not found)'}")
    for w in path_warnings:
        print(f"  INFO: {w}")

    print("\n" + "=" * 60)
    print("DRY RUN PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(run_dry_run())
