import json
import os
import platform
import sys
import shutil
import threading

# Lock for thread-safe access to SETTINGS_FILE
settings_lock = threading.Lock()

__version__ = "dev"

def get_app_data_dir():
    if platform.system() == "Windows":
        return os.path.join(os.environ["APPDATA"], "YoutubeWeekly")
    elif platform.system() == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "YoutubeWeekly")
    else:
        return os.path.join(os.path.expanduser("~"), ".config", "YoutubeWeekly")

APP_DATA_DIR = get_app_data_dir()
CONFIG_DIR = os.path.join(APP_DATA_DIR, 'config')
UPDATE_DIR = os.path.join(APP_DATA_DIR, 'updates')

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

def get_base_path():
    """ Get absolute path to base directory, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return os.path.dirname(sys.executable)
    else:
        return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def get_default_executable_paths():
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        base_path = os.path.join(sys._MEIPASS, 'app')
    else:
        # Running in a normal Python environment
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # This should be YoutubeWeekly/app
    mpv_path = ""
    ffmpeg_path = ""
    js_runtime_path = ""
    warnings = []

    system = platform.system()
    if system == "Windows":
        mpv_candidate = os.path.join(base_path, "player", "win64", "mpv-x86_64-20250715-git-fdbea0f", "mpv.exe")
        ffmpeg_candidate = os.path.join(base_path, "tools", "ffmpeg_win64", "ffmpeg-7.1.1-essentials_build", "bin", "ffmpeg.exe")
        qjs_candidate = os.path.join(base_path, "tools", "quickjs_win64", "qjs.exe")
    elif system == "Darwin": # macOS
        if platform.machine() == "arm64":
            mpv_candidate = os.path.join(base_path, "player", "macOS", "arm64", "mpv-arm64-0.40.0", "mpv.app", "Contents", "MacOS", "mpv")
            ffmpeg_candidate = os.path.join(base_path, "tools", "ffmpeg_macOS", "ffmpeg711arm", "ffmpeg")
            qjs_candidate = os.path.join(base_path, "tools", "quickjs_macOS", "arm64", "qjs")
        else: # Intel
            mpv_candidate = os.path.join(base_path, "player", "macOS", "intel", "mpv-0.39.0", "mpv.app", "Contents", "MacOS", "mpv")
            ffmpeg_candidate = os.path.join(base_path, "tools", "ffmpeg_macOS", "ffmpeg71intel", "ffmpeg")
            qjs_candidate = os.path.join(base_path, "tools", "quickjs_macOS", "intel", "qjs")
    elif system == "Linux":
        # Assuming a 64-bit Linux for now, adjust if 32-bit is needed
        mpv_candidate = "/usr/bin/mpv" # Placeholder, as you didn't provide a bundled Linux mpv
        ffmpeg_candidate = os.path.join(base_path, "tools", "ffmpeg_linux", "ffmpeg-7.0.2-amd64-static", "ffmpeg")
        qjs_candidate = os.path.join(base_path, "tools", "quickjs_linux", "qjs")

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

    # Validate the bundled JavaScript engine - see "JavaScript engine (QuickJS)"
    # in CLAUDE.md for why downloads need one at all.
    #
    # Deliberately adds NO warning when it is missing, unlike mpv and ffmpeg:
    # there is nothing for the user to configure (it is not exposed in
    # Settings), a source checkout legitimately has no bundled binary, and
    # yt-dlp falls back to auto-detecting a system runtime. An empty path here
    # means "let yt-dlp decide", which is exactly the old behaviour.
    if qjs_candidate and os.path.exists(qjs_candidate) and os.access(qjs_candidate, os.X_OK):
        js_runtime_path = qjs_candidate

    return {"mpv_path": mpv_path, "ffmpeg_path": ffmpeg_path,
            "js_runtime_path": js_runtime_path}, warnings

def _merge_missing_defaults(settings):
    """Add keys present in bundled defaults but missing from the user's settings.

    Migrates a settings file from older app versions: never overwrites existing
    user values, never removes keys. Returns True if any key was added so the
    caller can persist the merged result.
    """
    defaults = load_default_settings()
    if not defaults:
        return False

    # Window geometries and bundled exe paths are runtime-only; defaults file
    # may carry stale values for them, so skip those keys during migration.
    skip_keys = {"mpv_path", "ffmpeg_path", "js_runtime_path"}

    added = False
    for key, default_value in defaults.items():
        if key in skip_keys:
            continue
        if key.endswith("_geometry"):
            continue
        if key not in settings:
            settings[key] = default_value
            added = True
    return added


def load_settings():
    with settings_lock:
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}

    if _merge_missing_defaults(settings):
        with settings_lock:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)

    default_paths, warnings = get_default_executable_paths()

    # Always use the bundled executables
    settings["mpv_path"] = default_paths["mpv_path"]
    settings["ffmpeg_path"] = default_paths["ffmpeg_path"]
    settings["js_runtime_path"] = default_paths["js_runtime_path"]

    # Ensure video_folder is an absolute path relative to the executable
    video_folder = settings.get("video_folder", "data/videos")
    base_path = get_base_path()

    if not os.path.isabs(video_folder):
        video_folder = os.path.join(base_path, video_folder)
        settings["video_folder"] = video_folder
    elif not os.path.exists(video_folder):
        # Saved absolute path no longer exists (app moved or updated to new folder).
        # Reset to default relative path resolved against current base.
        video_folder = os.path.join(base_path, "data", "videos")
        settings["video_folder"] = video_folder

    if not os.path.exists(video_folder):
        os.makedirs(video_folder)

    return settings, warnings


def load_channels():
    with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_settings(settings):
    with settings_lock:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)

def load_default_settings():
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        default_settings_path = os.path.join(sys._MEIPASS, 'config', 'settings.json')
    else:
        # Running in a normal Python environment
        default_settings_path = os.path.join(os.path.dirname(__file__), '../../config', 'settings.json')
    
    try:
        with open(default_settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}