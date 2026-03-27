# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YoutubeWeekly is a cross-platform desktop Python application (v1.0.4) that automatically downloads weekly videos from specific YouTube channels, particularly for Sabbath-related content (Romanian SDA channels). The app uses Tkinter for the GUI with a dark theme, yt-dlp for downloading, and includes features like automatic scheduling, quality selection, date selection, system tray integration, and start-with-system support.

**GitHub**: `ThorSPB/YoutubeWeekly`

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov

# Run specific test file
pytest tests/test_downloader.py
```

**pytest.ini** sets `pythonpath = .` and uses `.pytest_cache_tmp` as cache dir.

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run the GUI application
python app/frontend/gui.py

# Run with start minimized flag (to system tray)
python app/frontend/gui.py --start-minimized
```

Note: `main.py` in the project root is a simple CLI-only script for quick testing of the download pipeline. The full GUI application entry point is `app/frontend/gui.py`.

### Building
The application is designed to be packaged with PyInstaller. The build process should include:
- All config files from `config/` directory
- Bundled executables (mpv, ffmpeg) for different platforms
- Assets (icons) from `app/frontend/assets/`
- Help docs from `docs/`

## Architecture Overview

### Core Structure
- **Backend (`app/backend/`)**: Core business logic
  - `config.py`: Configuration management, platform-specific executable paths, version constant (`__version__`), app data directory management (copies default configs to OS-specific app data dir on first run)
  - `downloader.py`: YouTube video downloading using yt-dlp (find videos, download with quality/format options, delete old videos, protected videos, recent Sabbath dates)
  - `auto_downloader.py`: Automatic download scheduling for Sabbath videos (runs on Fridays and Saturdays)
  - `updater.py`: Checks GitHub releases API for new versions
  - `logger.py`: Logging setup with timestamped log files
  - `startup_manager.py`: Cross-platform startup management (delegates to OS-specific modules)
  - `windows_startup.py`: Windows Registry-based startup (HKCU Run key)
  - `macos_startup.py`: macOS LaunchAgent-based startup (plist in ~/Library/LaunchAgents)
  - `linux_startup.py`: Linux .desktop file-based startup (~/.config/autostart/)

- **Frontend (`app/frontend/`)**: UI components (dark theme)
  - `gui.py`: Main Tkinter application window with system tray, per-channel download buttons, quality/date selectors, progress bar, play/folder buttons, "Others" custom URL download section, single-instance enforcement via socket IPC
  - `settings_window.py`: Settings configuration dialog (video folder, quality, auto-download, notifications, start-with-system, mpv settings, ffmpeg path, reset to defaults)
  - `file_viewer.py`: File browser for downloaded videos (play, delete selected, delete all, open folder in OS file manager)
  - `help_window.py`: Modal help window that renders markdown files from `docs/` with simple formatting

- **Configuration (`config/`)**: Default JSON configuration files (copied to app data dir on first run)
  - `settings.json`: User preferences, window geometries, quality settings, mpv/ffmpeg paths
  - `channels.json`: YouTube channel configurations with date formats
  - `auto_download_log.json`: Tracking automatic download status per Sabbath date

- **Documentation (`docs/`)**: In-app help files
  - `main_help.md`: User guide displayed from the main window help button
  - `settings_help.md`: Settings guide displayed from the settings window help button

- **Tests (`tests/`)**: pytest test suite
  - `test_downloader.py`, `test_download.py`: Core download logic tests
  - `test_auto_downloader.py`: Automatic download scheduling tests
  - `test_config_loading.py`: Configuration loading tests
  - `test_edge_cases.py`: Edge case testing for date parsing and video detection
  - `test_gui.py`: GUI testing
  - `test_multi_channel.py`: Multi-channel download scenarios
  - `test_old_video_deletion.py`: Video cleanup logic tests
  - `test_player_logic.py`: Video player integration tests
  - `test_video_check.py`: Video existence checking tests

### Key Design Patterns

1. **Cross-platform executable management**: `config.py` handles platform-specific paths for bundled mpv and ffmpeg executables (Windows, macOS arm64/Intel, Linux)
2. **Threading for downloads**: All download operations run in separate threads to prevent UI blocking
3. **Progress tracking**: Two-stage download progress (video 0-50% + audio 50-100%) with unified progress bar and ratchet logic (only increases)
4. **System tray integration**: Application minimizes to system tray on minimize/close, persistent tray icon with Show/Quit menu, notifications via plyer
5. **Single instance enforcement**: Uses socket-based IPC (port 65432) to prevent multiple instances; second instance signals the first to show its window
6. **App data directory**: Configs are stored in OS-specific app data directories (AppData on Windows, Library/Application Support on macOS, ~/.config on Linux), with defaults copied from `config/` on first run
7. **Start with system**: Cross-platform startup registration (Windows Registry, macOS LaunchAgent, Linux .desktop autostart) with `--start-minimized` flag
8. **Dark theme UI**: Full dark theme with `#2b2b2b` background across all windows

### Channel Configuration
Channels are defined in `config/channels.json` with:
- `name`: Display name
- `url`: YouTube channel URL
- `date_format`: Expected date format in video titles (e.g., `"%d.%m.%Y"` or `"%d %B %Y"`)
- `folder`: Subdirectory name for downloads

Current channels: Departamentul Ispravnicie (colecta) and ScoalaDeSabat (scoala_de_sabat).

### Date Matching Logic
The app searches for videos matching either:
- Numeric format (e.g., "16.08.2024")
- Romanian format (e.g., "16 august 2024")

Videos with "diaspora" in the title are excluded from matches.

### Automatic Downloads
- Runs on **Fridays and Saturdays** (weekday 4 and 5)
- Downloads videos for the upcoming Saturday
- Tracks download status per channel per Sabbath date in `auto_download_log.json` (states: pending, downloaded, not_found, error)
- Verifies previously-downloaded files still exist on disk (re-queues if missing)
- Sends system notifications for start, completion, and errors
- Progress is shown in the main window progress bar

### Manual Downloads
- Per-channel download with quality selector (1080p, 720p, 480p, mp3)
- Date selector: "automat" (next Saturday) or specific past Sabbath dates (last 30 Saturdays)
- "Others" section: paste any YouTube URL to download to the `other/` folder

### Video Player Integration
- Default: Uses system default video player (os.startfile on Windows, xdg-open on Linux, open on macOS)
- Optional: Integrated mpv player with custom arguments
- Supports fullscreen (via Lua script), volume (0-130), screen selection, and custom mpv arguments

### Update Checking
- On startup, checks GitHub releases API (`ThorSPB/YoutubeWeekly`) for newer versions
- Compares semantic version from `config.__version__` against latest release tag
- Shows info dialog if update is available

## Configuration Files

### settings.json Structure
```json
{
  "video_folder": "data/videos",
  "default_quality": "1080p",
  "keep_old_videos": false,
  "enable_auto_download": true,
  "enable_notifications": true,
  "start_with_system": true,
  "use_mpv": false,
  "mpv_fullscreen": true,
  "mpv_volume": 100,
  "mpv_screen": "Default",
  "mpv_custom_args": "",
  "last_sabbath_checked": "2025-08-16"
}
```

Note: `mpv_path` and `ffmpeg_path` are auto-detected from bundled executables at runtime. Window geometry keys (`main_window_geometry`, `settings_window_geometry`, `file_viewer_*_geometry`) are saved automatically.

### Bundled Dependencies
The application includes platform-specific binaries (gitignored via `app/tools/**` and `app/player/**`):
- **Windows**: `app/player/win64/mpv-x86_64-20250715-git-fdbea0f/mpv.exe`, `app/tools/ffmpeg_win64/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe`
- **macOS**: `app/player/macOS/{arm64|intel}/*/mpv`, `app/tools/ffmpeg_macOS/*/ffmpeg`
- **Linux**: Uses system mpv (`/usr/bin/mpv`), includes `app/tools/ffmpeg_linux/ffmpeg-7.0.2-amd64-static/ffmpeg`

### Python Dependencies (requirements.txt)
- `pytest`, `pytest-cov`: Testing
- `plyer`: Cross-platform notifications
- `screeninfo`: Monitor detection for mpv screen selection
- `requests`: HTTP client (update checker)
- `pystray`: System tray integration
- `Pillow`: Image processing (tray icon)
- `pyobjus`: macOS-only dependency for plyer

Note: `yt-dlp` and `tkinter` are required but not listed in requirements.txt (yt-dlp installed separately, tkinter bundled with Python).

## Important Notes
- `load_settings()` returns a tuple `(settings, warnings)` -- not just settings
- Always test cross-platform compatibility when modifying executable paths
- Progress hooks must be thread-safe and schedule UI updates on the main thread via `self.after(0, ...)`
- Configuration changes should trigger automatic reloading in the GUI
- System tray behavior varies by platform and should be tested thoroughly
- The `config/` directory in the repo contains defaults; runtime configs live in the OS-specific app data directory