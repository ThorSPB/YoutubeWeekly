# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YoutubeWeekly is a cross-platform desktop Python application that automatically downloads weekly videos from specific YouTube channels, particularly for Sabbath-related content (Romanian SDA channels). It uses Tkinter for the GUI with a dark theme, yt-dlp for downloading, and bundles mpv + ffmpeg for playback and conversion. Features include automatic scheduling, quality selection, date selection, system tray integration, start-with-system, silent self-update with rollback, anonymous usage telemetry (opt-out), and an in-app feedback system with developer replies.

**GitHub**: `ThorSPB/YoutubeWeekly`

**Current released version**: v1.3.1 (see `CHANGELOG.md`). The `__version__` constant in `app/backend/config.py` is `"dev"` when running from source; PyInstaller stamps the real version at build time via `build.py`. Update checks are skipped in dev mode.

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

`pytest.ini` sets `pythonpath = .` and uses `.pytest_cache_tmp` as cache dir. `tests/conftest.py` holds shared fixtures.

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run the GUI application
python app/frontend/gui.py

# Run with start minimized flag (to system tray)
python app/frontend/gui.py --start-minimized
```

`main.py` in the project root is a simple CLI-only script for quick testing of the download pipeline. The full GUI entry point is `app/frontend/gui.py`.

### Dry-Run Scripts
`scripts/dry_run_*.py` exercise subsystems without touching the GUI — useful for fast iteration and reproducing reported bugs:
- `dry_run_auto_download.py`, `dry_run_config.py`, `dry_run_download.py`
- `dry_run_feedback.py`, `dry_run_startup.py`, `dry_run_telemetry.py`, `dry_run_update.py`

### Building
`scripts/build.py` is the PyInstaller driver. Spec files at repo root:
- `youtubeweekly.spec` — main GUI executable
- `update_bootstrap.spec` — separate small bootstrap binary that performs the swap-in-place during auto-updates

The build bundles config defaults from `config/`, platform binaries for mpv/ffmpeg, icons from `app/frontend/assets/`, and help docs from `docs/`. The version is injected at build time so update checks compare correctly.

## Architecture Overview

### Core Structure

- **Backend (`app/backend/`)**: Core business logic
  - `config.py`: Configuration management, platform-specific executable paths, `__version__` constant, app data dir (`CONFIG_DIR`); copies default configs from `config/` into the OS-specific app data dir on first run. `load_settings()` returns `(settings, warnings)`.
  - `downloader.py`: yt-dlp-based downloads (find videos, quality/format selection, delete old videos, protected videos, recent Sabbath dates). Includes fuzzy date matching — handles off-by-one-day titles and formatting variants, and surfaces a confirmation prompt to the user.
  - `auto_downloader.py`: Automatic download scheduling for upcoming Sabbath (Fri/Sat).
  - `updater.py`: Talks to the GitHub releases API (`ThorSPB/YoutubeWeekly`). Provides current-release check, paginated listing of available versions for rollback (`MIN_ROLLBACK_VERSION = 1.1.0`), and asset downloader with progress callback. Per-platform asset selection (`win64`, `macos-arm64`, `macos-intel`, `linux-x64`).
  - `update_bootstrap.py`: External process that swaps a downloaded ZIP over the running install. Uses `WaitForSingleObject` on Windows for reliable exit detection; renames the running bootstrap before extraction so it can update itself.
  - `telemetry.py`: Anonymous usage analytics. Persistent install ID in `CONFIG_DIR/install_id`. Geo lookup happens **on the client** via `ip-api.com` (HTTP, free tier) — only the resolved `city`/`country` are sent, never the IP. Posts to `https://thorsp.ddns.net/ytw-telemetry/ping`. Gated on `send_telemetry` setting.
  - `feedback.py`: In-app feedback. Local thread cache at `CONFIG_DIR/feedback.json`. Screenshots compressed to JPEG (≤500 KB, max 1280×720) before upload. Posts to `https://thorsp.ddns.net/ytw-telemetry/feedback`. Reuses install ID + sanitized settings from telemetry module so a single anonymous identity links pings and feedback.
  - `logger.py`: Logging setup with timestamped log files.
  - `startup_manager.py`: Cross-platform startup management (dispatches to OS-specific modules).
  - `windows_startup.py`: Windows Registry-based startup (HKCU Run key).
  - `macos_startup.py`: macOS LaunchAgent-based startup (plist in `~/Library/LaunchAgents`).
  - `linux_startup.py`: Linux `.desktop` file-based startup (`~/.config/autostart/`).

- **Frontend (`app/frontend/`)**: UI components (dark theme `#2b2b2b`)
  - `gui.py`: Main Tkinter window. System tray, per-channel download buttons + play/folder buttons, quality/date selectors, unified progress bar, "Others" custom URL section, version badge bottom-left, refresh-update `↻` button, feedback button. Single-instance enforcement via socket IPC (port 65432).
  - `settings_window.py`: Settings dialog organized into **General / Player / Advanced** tabs. Includes telemetry toggle, check-for-updates toggle, auto-install-updates toggle (greyed out via the visual-tree pattern when its parent setting is disabled), reset-to-defaults, and the rollback launcher.
  - `feedback_window.py`: Feedback UI with conversation threads, latest-message preview, drag-and-drop multi-screenshot attach, reply support, notification badge for unread developer replies, mousewheel scrolling that propagates across child widgets.
  - `file_viewer.py`: File browser for downloaded videos (play, delete selected, delete all, open folder in OS file manager).
  - `help_window.py`: Modal help window that renders the Markdown files from `docs/`.
  - `player_utils.py`: Helpers for picking and launching the configured video player (default-OS player vs. integrated mpv).

- **Configuration (`config/`)**: Default JSON copied to app data dir on first run
  - `settings.json`: User preferences, window geometries, quality, mpv/ffmpeg paths, update + telemetry toggles
  - `channels.json`: YouTube channel configurations
  - `auto_download_log.json`: Tracking automatic download status per Sabbath date

- **Documentation (`docs/`)**: In-app help (Markdown)
  - `main_help.md`, `settings_help.md`

- **Tests (`tests/`)**: pytest suite
  - Core download: `test_downloader.py`, `test_download.py`, `test_video_check.py`, `test_old_video_deletion.py`, `test_edge_cases.py`, `test_multi_channel.py`
  - Auto download: `test_auto_downloader.py`
  - Config: `test_config_loading.py`
  - Updater: `test_updater.py`
  - Startup: `test_startup_manager.py`
  - Player: `test_player_logic.py`, `test_player_utils.py`
  - GUI: `test_gui.py`
  - Smoke: `test_smoke.py`
  - Shared fixtures: `conftest.py`

### Key Design Patterns

1. **Cross-platform executable management**: `config.py` resolves platform-specific paths for bundled mpv and ffmpeg (Windows, macOS arm64/Intel, Linux).
2. **Threading for downloads**: All download operations run in worker threads to keep the UI responsive.
3. **Progress tracking**: Two-stage download progress (video 0–50% + audio 50–100%) with unified progress bar and ratchet logic (only increases).
4. **System tray integration**: Minimize/close minimizes to tray. Persistent tray icon with Show/Quit menu, notifications via `plyer`.
5. **Single instance enforcement**: Socket IPC on port 65432. Second instance signals the first to show its window.
6. **App data directory**: Configs live in the OS-specific app data dir (AppData on Windows, `~/Library/Application Support/` on macOS, `~/.config/` on Linux). Defaults from `config/` are copied on first run.
7. **Start with system**: Cross-platform startup registration (Registry / LaunchAgent / `.desktop`) honoring `--start-minimized`.
8. **Silent auto-update**: When tray-running, updates can install silently on startup (`auto_install_updates`). A separate `update_bootstrap` binary performs the swap so the GUI can fully exit first. After a successful update, the next launch shows a Markdown changelog popup and an "Update complete!" status message.
9. **Version rollback**: Settings → Advanced → Rollback lists prior releases (paginated GitHub releases, filtered ≥ `MIN_ROLLBACK_VERSION` v1.1.0) and reuses the same bootstrap flow.
10. **Anonymous identity, client-side geo**: A single UUID install ID is created on first launch and shared between telemetry pings and feedback submissions. Location is resolved on-device so the user's IP never reaches our server.
11. **Dark theme UI**: Full dark theme across all windows.

### Channel Configuration
Channels in `config/channels.json`:
- `name`: Display name
- `url`: YouTube channel URL
- `date_format`: Expected date format in video titles (e.g., `"%d.%m.%Y"` or `"%d %B %Y"`)
- `folder`: Subdirectory name for downloads

Current channels: Departamentul Ispravnicie (colecta) and ScoalaDeSabat (scoala_de_sabat).

### Date Matching Logic
Searches for videos matching either:
- Numeric format (e.g., "16.08.2024")
- Romanian format (e.g., "16 august 2024")

Videos with "diaspora" in the title are excluded. The fuzzy matcher (since v1.1.0) also tolerates common title errors (off-by-one date, formatting variants) and surfaces a confirmation dialog when the closest match isn't exact.

### Automatic Downloads
- Runs on **Fridays and Saturdays** (weekday 4 and 5)
- Downloads videos for the upcoming Saturday
- Tracks status per channel per Sabbath date in `auto_download_log.json` (`pending`, `downloaded`, `not_found`, `error`)
- Verifies previously-downloaded files still exist on disk (re-queues if missing)
- Sends system notifications for start, completion, and errors
- Progress is shown in the main window progress bar

### Manual Downloads
- Per-channel download with quality selector. Supported qualities (since v1.1.0): `max`, `4K`, `2K`, `1080p`, `720p`, `480p`, `mp3`.
- Date selector: "automat" (next Saturday) or a specific past Sabbath date (last 30 Saturdays).
- "Others" section: paste any YouTube URL to download into the `other/` folder. Tracked separately in telemetry (since v1.2.0) so quality selection there is metered independently.

### Video Player Integration
- Default: System default video player (`os.startfile` on Windows, `xdg-open` on Linux, `open` on macOS)
- Optional: Integrated mpv with custom arguments
- Supports fullscreen (via Lua script), volume (0–130), screen selection, and arbitrary mpv args

### Update Checking
- On startup, queries the GitHub releases API for newer versions
- Compares semantic version from `config.__version__` against the latest tag (skipped when `__version__ == "dev"`)
- Update flow: in-app prompt → silent download via `updater.download_update()` → hands off to `update_bootstrap` → relaunch
- `check_for_updates` and `auto_install_updates` settings let the user opt out or fully automate
- After a successful update, the next launch shows the changelog popup with a centered Quit button

### Feedback System
- Opened from a button on the main window
- Threaded conversation view with the developer; reply support; unread badge
- Up to multiple screenshots per message (drag-and-drop)
- System info (OS, version, hardware via `psutil`) is included with each thread to help diagnose issues
- Local cache at `CONFIG_DIR/feedback.json`; server at `https://thorsp.ddns.net/ytw-telemetry/feedback`

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
  "check_for_updates": true,
  "auto_install_updates": false,
  "send_telemetry": true,
  "use_mpv": false,
  "mpv_fullscreen": true,
  "mpv_volume": 100,
  "mpv_screen": "Default",
  "mpv_custom_args": "",
  "last_sabbath_checked": "2025-08-16"
}
```

`mpv_path` and `ffmpeg_path` are auto-detected from bundled executables at runtime. Window geometry keys (`main_window_geometry`, `settings_window_geometry`, `file_viewer_*_geometry`) are saved automatically.

### Bundled Dependencies
Platform-specific binaries (gitignored via `app/tools/**` and `app/player/**`):
- **Windows**: `app/player/win64/mpv-x86_64-20250715-git-fdbea0f/mpv.exe`, `app/tools/ffmpeg_win64/ffmpeg-7.1.1-essentials_build/bin/ffmpeg.exe`
- **macOS**: `app/player/macOS/{arm64|intel}/*/mpv`, `app/tools/ffmpeg_macOS/*/ffmpeg`
- **Linux**: Uses system mpv (`/usr/bin/mpv`), includes `app/tools/ffmpeg_linux/ffmpeg-7.0.2-amd64-static/ffmpeg`

### Python Dependencies (`requirements.txt`)
- `pytest`, `pytest-cov` — testing
- `yt-dlp` — downloader
- `plyer` — cross-platform notifications
- `pyobjus` — macOS-only dep for plyer
- `screeninfo` — monitor detection for mpv screen selection
- `requests` — HTTP (updates, telemetry, feedback)
- `pystray`, `Pillow` — system tray icon + screenshot compression
- `psutil` — system info collection for feedback

`tkinter` is required but bundled with Python.

## Important Notes
- `load_settings()` returns a tuple `(settings, warnings)` — not just settings
- Always test cross-platform compatibility when modifying executable paths
- Progress hooks must be thread-safe and schedule UI updates on the main thread via `self.after(0, ...)`
- Configuration changes should trigger automatic reloading in the GUI
- System tray behavior varies by platform — test thoroughly
- The `config/` directory in the repo contains defaults; runtime configs live in the OS-specific app data dir
- `__version__` is `"dev"` in source checkouts. Code paths that depend on the real version (update check, telemetry payload) must handle the dev case — tests mock `__version__` where relevant
- Telemetry/feedback share an anonymous install ID. IP-based geo resolution is done on the client; do not move it server-side
- The auto-update flow relies on the separate `update_bootstrap` binary. Don't try to swap the running executable in-process
