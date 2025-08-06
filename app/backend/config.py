import json
import os
import platform
import sys
import shutil

def get_app_data_dir():
    if platform.system() == "Windows":
        return os.path.join(os.environ["APPDATA"], "YoutubeWeekly")
    elif platform.system() == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "YoutubeWeekly")
    else:
        return os.path.join(os.path.expanduser("~"), ".config", "YoutubeWeekly")

APP_DATA_DIR = get_app_data_dir()
CONFIG_DIR = os.path.join(APP_DATA_DIR, 'config')

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    default_config_src = os.path.join(sys._MEIPASS, 'config')
else:
    # Running in a normal Python environment
    default_config_src = os.path.join(os.path.dirname(__file__), '../../config')

# Ensure all default config files exist in the app data directory
for item in os.listdir(default_config_src):
    s = os.path.join(default_config_src, item)
    d = os.path.join(CONFIG_DIR, item)
    if os.path.isfile(s) and not os.path.exists(d):
        shutil.copy2(s, d)

SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')
CHANNELS_FILE = os.path.join(CONFIG_DIR, 'channels.json')
AUTO_DOWNLOAD_LOG_FILE = os.path.join(CONFIG_DIR, "auto_download_log.json")

# Create an empty auto_download_log.json if it doesn't exist
if not os.path.exists(AUTO_DOWNLOAD_LOG_FILE):
    with open(AUTO_DOWNLOAD_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f)

def get_default_executable_paths():
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_path = os.path.join(sys._MEIPASS, 'app')
    else:
        # Running in a normal Python environment
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

    # Always use the bundled executables
    settings["mpv_path"] = default_paths["mpv_path"]
    settings["ffmpeg_path"] = default_paths["ffmpeg_path"]

    return settings, warnings


def load_channels():
    with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)
