# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YoutubeWeekly is a desktop Python application that automatically downloads weekly videos from specific YouTube channels, particularly for Sabbath-related content. The app uses Tkinter for the GUI, yt-dlp for downloading, and includes features like automatic scheduling, quality selection, and system tray integration.

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

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application in development
python main.py

# Run with start minimized flag
python main.py --start-minimized
```

### Building
The application is designed to be packaged with PyInstaller. The build process should include:
- All config files from `config/` directory
- Bundled executables (mpv, ffmpeg) for different platforms
- Assets (icons) from `app/frontend/assets/`

## Architecture Overview

### Core Structure
- **Backend (`app/backend/`)**: Core business logic
  - `config.py`: Configuration management, platform-specific executable paths
  - `downloader.py`: YouTube video downloading logic using yt-dlp
  - `auto_downloader.py`: Automatic download scheduling for Sabbath videos
  - `updater.py`: Application update checking
  - `logger.py`: Logging utilities

- **Frontend (`app/frontend/`)**: UI components
  - `gui.py`: Main Tkinter application window with system tray integration
  - `settings_window.py`: Settings configuration dialog
  - `file_viewer.py`: File browser for downloaded videos

- **Configuration (`config/`)**: JSON configuration files
  - `settings.json`: User preferences, window geometry, quality settings
  - `channels.json`: YouTube channel configurations with date formats
  - `auto_download_log.json`: Tracking automatic downloads

### Key Design Patterns

1. **Cross-platform executable management**: `config.py` handles platform-specific paths for bundled mpv and ffmpeg executables
2. **Threading for downloads**: All download operations run in separate threads to prevent UI blocking
3. **Progress tracking**: Two-stage download progress (video + audio) with unified progress bar
4. **System tray integration**: Application can minimize to system tray and show notifications
5. **Single instance enforcement**: Uses socket-based IPC to prevent multiple instances

### Channel Configuration
Channels are defined in `config/channels.json` with:
- `name`: Display name
- `url`: YouTube channel URL
- `date_format`: Expected date format in video titles (e.g., "%d.%m.%Y" or "%d %B %Y")
- `folder`: Subdirectory name for downloads

### Date Matching Logic
The app searches for videos matching either:
- Numeric format (e.g., "16.08.2024")
- Romanian format (e.g., "16 august 2024")

### Automatic Downloads
- Runs on Tuesdays and Wednesdays (weekday 1 and 2)
- Downloads videos for the upcoming Saturday
- Tracks download status in `auto_download_log.json`
- Sends system notifications for completion/errors

### Video Player Integration
- Default: Uses system default video player
- Optional: Integrated mpv player with custom arguments
- Supports fullscreen, volume, screen selection, and custom mpv arguments

## Configuration Files

### settings.json Structure
```json
{
  "video_folder": "data/videos",
  "default_quality": "1080p",
  "keep_old_videos": false,
  "enable_auto_download": true,
  "enable_notifications": true,
  "use_mpv": false,
  "mpv_fullscreen": true,
  "mpv_volume": 100,
  "mpv_screen": "Default",
  "mpv_custom_args": ""
}
```

### Bundled Dependencies
The application includes platform-specific binaries:
- **Windows**: `app/player/win64/mpv-x86_64-*/mpv.exe`, `app/tools/ffmpeg_win64/*/ffmpeg.exe`
- **macOS**: `app/player/macOS/{arm64|intel}/*/mpv`, `app/tools/ffmpeg_macOS/*/ffmpeg`
- **Linux**: Uses system mpv, includes `app/tools/ffmpeg_linux/*/ffmpeg`

## Testing Strategy
- Unit tests for core downloading logic
- GUI testing with pytest
- Edge case testing for date parsing and video detection
- Multi-channel testing scenarios

## Important Notes
- Always test cross-platform compatibility when modifying executable paths
- Progress hooks must be thread-safe and schedule UI updates on main thread
- Configuration changes should trigger automatic reloading in the GUI
- System tray behavior varies by platform and should be tested thoroughly