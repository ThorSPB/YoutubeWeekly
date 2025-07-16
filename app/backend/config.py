import json
import os
import platform
import sys

if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    CONFIG_DIR = os.path.join(sys._MEIPASS, 'config')
else:
    # Running in a normal Python environment
    CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../../config')
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')
CHANNELS_FILE = os.path.join(CONFIG_DIR, 'channels.json')

def get_default_executable_paths():
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # This should be YoutubeWeekly/app
    mpv_path = ""
    ffmpeg_path = ""
    warnings = []

    system = platform.system()
    if system == "Windows":
        mpv_candidate = os.path.join(base_path, "player", "win64", "mpv-x86_64-20250715-git-fdbea0f", "mpv.exe")
        ffmpeg_candidate = os.path.join(base_path, "tools", "ffmpeg_win64", "ffmpeg-7.1.1-essentials_build", "bin", "ffmpeg.exe")
    elif system == "Darwin": # macOS
        if platform.machine() == "arm64":
            mpv_candidate = os.path.join(base_path, "player", "macOS", "arm64", "mpv-arm64-0.40.0", "mpv.app", "Contents", "MacOS", "mpv")
            ffmpeg_candidate = os.path.join(base_path, "tools", "ffmpeg_macOS", "ffmpeg711arm", "ffmpeg")
        else: # Intel
            mpv_candidate = os.path.join(base_path, "player", "macOS", "intel", "mpv-0.39.0", "mpv.app", "Contents", "MacOS", "mpv")
            ffmpeg_candidate = os.path.join(base_path, "tools", "ffmpeg_macOS", "ffmpeg71intel", "ffmpeg")
    elif system == "Linux":
        # Assuming a 64-bit Linux for now, adjust if 32-bit is needed
        mpv_candidate = "/usr/bin/mpv" # Placeholder, as you didn't provide a bundled Linux mpv
        ffmpeg_candidate = os.path.join(base_path, "tools", "ffmpeg_linux", "ffmpeg-7.0.2-amd64-static", "ffmpeg")
    
    # Validate mpv path
    if os.path.exists(mpv_candidate) and os.access(mpv_candidate, os.X_OK):
        mpv_path = mpv_candidate
    else:
        warnings.append(f"Warning: Default MPV executable not found or not executable at '{mpv_candidate}'. Please configure MPV path in settings.")

    # Validate ffmpeg path
    if os.path.exists(ffmpeg_candidate) and os.access(ffmpeg_candidate, os.X_OK):
        ffmpeg_path = ffmpeg_candidate
    else:
        warnings.append(f"Warning: Default FFmpeg executable not found or not executable at '{ffmpeg_candidate}'. Please configure FFmpeg path in settings.")

    return {"mpv_path": mpv_path, "ffmpeg_path": ffmpeg_path}, warnings

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        settings = {}

    default_paths, warnings = get_default_executable_paths()

    if not settings.get("mpv_path"):
        settings["mpv_path"] = default_paths["mpv_path"]
    
    if not settings.get("ffmpeg_path"):
        settings["ffmpeg_path"] = default_paths["ffmpeg_path"]

    return settings, warnings


def load_channels():
    with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
