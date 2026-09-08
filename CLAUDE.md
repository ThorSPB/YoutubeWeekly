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
  - `downloader.py`: yt-dlp-based downloads (find videos, quality/format selection, delete old videos, protected videos, recent Sabbath dates). Includes fuzzy date matching — handles off-by-one-day titles and formatting variants, and surfaces a confirmation prompt to the user. Hands yt-dlp the bundled JS engine, and retries a failed download once across `FALLBACK_PLAYER_CLIENTS` — see "JavaScript engine (QuickJS)" and "Player-client fallback" below.
  - `auto_downloader.py`: Automatic download scheduling for upcoming Sabbath (Fri/Sat).
  - `updater.py`: Talks to the GitHub releases API (`ThorSPB/YoutubeWeekly`). Provides current-release check, paginated listing of available versions for rollback (`MIN_ROLLBACK_VERSION = 1.1.0`), and asset downloader with progress callback. Per-platform asset selection (`win64`, `macos-arm64`, `macos-intel`, `linux-x64`).
  - `update_bootstrap.py`: External process that swaps a downloaded ZIP over the running install. Uses `WaitForSingleObject` on Windows for reliable exit detection; renames the running bootstrap before extraction so it can update itself.
  - `telemetry.py`: Anonymous usage analytics. Persistent install ID in `CONFIG_DIR/install_id`. Geo lookup happens **on the client** via `ip-api.com` (HTTP, free tier) — only the resolved `city`/`country` are sent, never the IP. Posts to `https://thorsp.net/ytw-telemetry/ping`. Gated on `send_telemetry` setting.
  - `overrides.py`: Server-driven video overrides. When a channel titles a video with the wrong date (a wrong *year*, typically) the date matcher can't find it, so the operator publishes an override from the telemetry dashboard pointing at the right video. Two modes: **fallback** (used only when the app's own search finds nothing) and **force** (beats the search, and replaces a video already downloaded for that Sabbath). Sources are a link (yt-dlp) or a video file hosted on the Pi (streamed over HTTP with yt-dlp-shaped progress events). Discovery is a conditional GET against `https://thorsp.net/ytw-telemetry/overrides` — an unchanged poll is a bodyless 304. Identity-free (no install ID), so it runs regardless of the telemetry opt-out. See "Video Overrides" below.
  - `feedback.py`: In-app feedback. Local thread cache at `CONFIG_DIR/feedback.json`. Screenshots compressed to JPEG (≤500 KB, max 1280×720) before upload. Posts to `https://thorsp.net/ytw-telemetry/feedback`. Reuses install ID + sanitized settings from telemetry module so a single anonymous identity links pings and feedback.
  - `progress.py`: Download-progress model — see Key Design Patterns #3. No tkinter import, so headless callers and tests can use it.
  - `changelog.py`: Locates the changelog (localized `CHANGELOG_<lang>.md` first, English as fallback), splits it into `## ` sections and works out which are **new to this user**. `notes_since(content, previous, current)` is inclusive of the current version and exclusive of the one they had, so a 1.4.0 → 1.5.1 jump shows the 1.5.0 notes too; `all_notes()` backs the Settings → Advanced → Release Notes reader. Non-version headings (`## Unreleased`) are parsed but excluded from both.
  - `logger.py`: Logging setup with timestamped log files.
  - `startup_manager.py`: Cross-platform startup management (dispatches to OS-specific modules).
  - `windows_startup.py`: Windows Registry-based startup (HKCU Run key).
  - `macos_startup.py`: macOS LaunchAgent-based startup (plist in `~/Library/LaunchAgents`).
  - `linux_startup.py`: Linux `.desktop` file-based startup (`~/.config/autostart/`).

- **Frontend (`app/frontend/`)**: UI components (dark theme `#2b2b2b`)
  - `gui.py`: Main Tkinter window. System tray, per-channel download buttons + play/folder buttons, quality/date selectors, unified progress bar, "Others" custom URL section, version badge bottom-left, refresh-update `↻` button, feedback button. Single-instance enforcement via socket IPC (port 65432).
  - `settings_window.py`: Settings dialog organized into **General / Player / Advanced** tabs. Includes telemetry toggle, check-for-updates toggle, auto-install-updates toggle (greyed out via the visual-tree pattern when its parent setting is disabled), reset-to-defaults, the rollback launcher, and a **Release Notes** button (Advanced) that opens the full history in a `HelpWindow` — which now accepts a `content=` argument so it can render markdown that isn't a doc file on disk.
  - `feedback_window.py`: Feedback UI with conversation threads, latest-message preview, drag-and-drop multi-screenshot attach, reply support, notification badge for unread developer replies, mousewheel scrolling that propagates across child widgets.
  - `file_viewer.py`: File browser for downloaded videos (play, delete selected, delete all, open folder in OS file manager).
  - `help_window.py`: Modal help window that renders the Markdown files from `docs/`.
  - `player_utils.py`: Helpers for picking and launching the configured video player (default-OS player vs. integrated mpv).

- **Configuration (`config/`)**: Default JSON copied to app data dir on first run
  - `settings.json`: User preferences, window geometries, quality, mpv/ffmpeg paths, update + telemetry toggles
  - `channels.json`: YouTube channel configurations
  - `auto_download_log.json`: Tracking automatic download status per Sabbath date

- **Documentation (`docs/`)**: In-app help (Markdown), with `_ro` variants
  - `main_help.md`, `settings_help.md` (+ `main_help_ro.md`, `settings_help_ro.md`)
  - Release notes live at the repo **root**: `CHANGELOG.md` + `CHANGELOG_ro.md`. `release.yml` copies `CHANGELOG*.md` into the dist root, so a new translation ships without touching the workflow. **Keep the two files structurally identical** — same sections, same bullet counts; `tests/test_changelog.py` asserts it.
  - **Write new notes under `## Unreleased`; the release stamps them.** Nobody moves them by hand — `scripts/stamp_changelog.py` renames that heading to `## v<version>` in the `create-release` job, **before the tag is cut**, and commits it with a skip-CI marker in the message, or the push to `main` starts a second Release run.
  - ⚠ **Never put the literal skip-CI token in a commit message or a PR body.** GitHub honours it anywhere in the message, body included — and a squash merge uses the PR body as the commit message, so it silently skips CI on `main` too. It cost a CI-less PR here. Describe it in prose (as this line does) and keep the real token inside the workflow file. The build jobs therefore check out **the tag**, not the triggering commit, or they would ship the pre-stamp file. If `## Unreleased` is gone, add the heading back when you write the next note; the stamper never re-creates it.
  - ⚠ **`changelog.py` ignores non-version headings**, so a note left under `## Unreleased` is invisible to users — no error, it simply never appears. **v1.6.1 shipped that way and showed its users nothing.** The stamper is what prevents it; `tests/test_changelog.py` pins the whole chain, including that `notes_since()` returns nothing before stamping and the note after.

- **Tests (`tests/`)**: pytest suite
  - Core download: `test_downloader.py`, `test_download.py`, `test_video_check.py`, `test_old_video_deletion.py`, `test_edge_cases.py`, `test_multi_channel.py`
  - Auto download: `test_auto_downloader.py`
  - Config: `test_config_loading.py`
  - Updater: `test_updater.py`
  - Progress model: `test_progress.py`
  - Release notes: `test_changelog.py`
  - Startup: `test_startup_manager.py`
  - Player: `test_player_logic.py`, `test_player_utils.py`
  - GUI: `test_gui.py`
  - Smoke: `test_smoke.py`
  - Shared fixtures: `conftest.py`

### Key Design Patterns

1. **Cross-platform executable management**: `config.py` resolves platform-specific paths for bundled mpv and ffmpeg (Windows, macOS arm64/Intel, Linux).
2. **Threading for downloads**: All download operations run in worker threads to keep the UI responsive.
3. **Progress tracking**: `app/backend/progress.py` (`DownloadProgress`) folds yt-dlp's *per-stream* events into one monotonic percentage. Byte-weighted when the producer supplies a plan (`build_download_plan` / `download_hosted_file` emit a synthetic `ytw_plan` event before any bytes move); otherwise an even split across the stream count **inferred from the first stream's codecs** — a video-only first stream means audio follows and gets merged, anything else stands alone. Completion is also declared by the calling worker when its download returns clean. Do **not** hardcode a stream count: an mp3, a pre-merged format and a hosted override file are all single-stream, and assuming yt-dlp's video+audio pair used to leave the bar stuck at 50% forever.
4. **System tray integration**: Minimize/close minimizes to tray. Persistent tray icon with Show/Quit menu, notifications via `plyer`.
5. **Single instance enforcement**: Socket IPC on port 65432. Second instance signals the first to show its window.
6. **App data directory**: Configs live in the OS-specific app data dir (AppData on Windows, `~/Library/Application Support/` on macOS, `~/.config/` on Linux). Defaults from `config/` are copied on first run.
7. **Start with system**: Cross-platform startup registration (Registry / LaunchAgent / `.desktop`) honoring `--start-minimized`.
8. **Silent auto-update**: When tray-running, updates can install silently on startup (`auto_install_updates`). A separate `update_bootstrap` binary performs the swap so the GUI can fully exit first. After a successful update, the next launch shows a Markdown changelog popup and an "Update complete!" status message. Where the new instance comes back is decided by the window's **current** state (`_window_is_hidden()`), not by `--start-minimized` in argv — an app launched into the tray at boot keeps that flag for its whole life, so updating from the foreground hours later used to relaunch into the tray. If notes are owed while the app is hidden they're held in `_pending_changelog` and shown the first time the window is opened.
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

### JavaScript engine (QuickJS)

**Downloads need a JavaScript engine.** yt-dlp solves YouTube's signature /
`n` challenge by *running YouTube's own JavaScript*, and some videos release no
adaptive-format URL until that is solved. Adaptive formats are the only route
above 360p (the sole surviving muxed format is 360p), so with no engine those
videos fail outright — with YouTube's flatly wrong "This video is not
available", because yt-dlp then falls through its clients until `visionos`
refuses.

**The discriminator is YouTube's "Made for Kids" flag.** Measured 2026-09-07
across 22 videos, no engine vs `quickjs`: **8/8 kids videos failed, 0/10
non-kids failed**; every failure returned 1080p with an engine. The kids set
spanned five unrelated channels plus Cocomelon and Baby Shark, 2021 and 2026
uploads, all `People & Blogs`, `isFamilySafe: true` in *both* groups. That is
why nothing else had ever failed: an ordinary video is served by `visionos`
with clean URLs and never needs JavaScript at all.

- **`app/tools/quickjs_<platform>/qjs[.exe]`**, fetched per platform in
  `release.yml` (pinned by `QUICKJS_TAG`) from **quickjs-ng**, which publishes
  static single-file builds of ~2 MB. `app/tools` is bundled wholesale by the
  spec, so no spec change is needed for a new binary under it.
- `config.py::get_default_executable_paths()` resolves it into
  **`js_runtime_path`**, recomputed on every `load_settings()` like
  `mpv_path`/`ffmpeg_path` — a saved path breaks when the app is moved or
  updated.
- A missing engine adds **no user-facing warning**, unlike mpv and ffmpeg: it
  is not exposed in Settings so there is nothing to configure, a source
  checkout legitimately has none, and an empty path just means "let yt-dlp
  auto-detect". `download_video` logs which engine it used instead, so a build
  that shipped without the binary — or lost its executable bit in packaging —
  is visible in the log rather than silently back to 360p-or-nothing.
- ⚠⚠ **An engine is only HALF of it, and the other half is TWO scripts from
  TWO packages.** yt-dlp runs a `lib` script and a `core` script through the
  engine. `yt_dlp` vendors the **core** plus bun/deno *import shims* — there is
  **no vendored `yt.solver.lib.js`**, so the `lib` script exists only in the
  separate **`yt_dlp_ejs`** package, which plain `yt-dlp` does not depend on.
  All of them are **data files**, which a freeze drops unless collected, and a
  missing one is reported by returning `None` **silently**. Missing either fails
  identically to having no engine: "This video is not available".
  So `requirements.txt` uses **`yt-dlp[default]`** (that extra pins
  `yt-dlp-ejs==0.8.0`, and yt-dlp validates the version at runtime — let yt-dlp
  own that pin) and the spec collects **both** `collect_data_files("yt_dlp")`
  and `collect_data_files("yt_dlp_ejs")`.
  **v1.6.1 shipped with neither script; v1.6.2 shipped with the core but no
  lib** — engine bundled, resolved and logged, still 360p.
- ⚠⚠ **Beware yt-dlp's solver CACHE when verifying.** `~/.cache/yt-dlp/challenge-solver/`
  is a script source in its own right, ranked above the vendored one. A single
  earlier run with `--remote-components ejs:github` populates it, and every
  later test then passes for the wrong reason — which is exactly how v1.6.2 was
  "proved" working. **Always pass an isolated, empty `cachedir`** (and move the
  user cache aside) when testing the solver, or you are measuring your own
  earlier experiment.
- ⚠ **Verify a packaging fix in a frozen build, never from source.** From a
  checkout those data files are always present, so the bug is invisible — two
  fixes passed every source-level test and still shipped broken. Freeze a probe
  (`PyInstaller` a script that calls `js_solver_status()` and downloads a kids
  video, with an isolated cachedir) and build a **negative control** too: a
  positive-only result cannot tell a real fix from a contaminated environment.
  See [[feedback_verify_which_build_operator_tested]].
- ⚠ **`js_runtimes` must be a dict** of `{runtime: {config}}`. A list raises a
  bare `ValueError` from `YoutubeDL.__init__` that names no option.
- ⚠ **yt-dlp auto-enables only `deno`.** Node can sit on `PATH` completely
  unused, which is what makes "no JS runtime" so easy to misdiagnose.

Dead ends, all measured — don't re-walk them:
- **PO tokens are irrelevant here.** `bgutil-ytdlp-pot-provider` minted a real
  GVS token and nothing changed.
- **Forcing `player_client=web` is SABR-only regardless**, so every web-client
  probe looks like a dead end and sends you chasing SABR (yt-dlp #12482).
- Upgrading yt-dlp changes nothing (stable 2026.08.19 == nightly 2026.08.30).
- The `android` client alone "works" but serves only muxed **360p** — a trap
  that looks like a fix.

### Player-client fallback

A safety net *behind* the JavaScript engine above, not a substitute for it: it
rescues a challenge-blocked video at 360p, where the engine gets 1080p. It
earns its place for the case where the bundled binary is missing or broken, and
for whatever YouTube does next.

`download_video` treats a failure as inconclusive: it retries **once** with
`extractor_args={"youtube": {"player_client": FALLBACK_PLAYER_CLIENTS}}`.
Notes on that list and the retry:
- `default` stays **first** in it. Without it the retry would trade a perfectly
  good 1080p stream for whatever the older clients happen to offer.
- The retry is deliberately **not** gated on the error text. YouTube's messages
  churn, and a fix that pattern-matches them is a fix that quietly stops
  working. The cost of an unnecessary retry is a few HTTP requests on a path
  that was already failing.
- The error handed back to the caller is the **first** attempt's, not the
  retry's: the retry ran against clients the user never chose, and its message
  would only mislead.
- A retry restarts from zero bytes, so it emits `PROGRESS_RESET_STATUS` first.
  `DownloadProgress` only ever moves forward, so without that the bar would sit
  at the abandoned attempt's high-water mark.
- Every download in the app (channels, "Others", link overrides) goes through
  `download_video`, so all of them get this.

### Video Overrides
A safety valve for the case the date matcher structurally cannot handle: the
uploader typed the wrong date. Real example (2026-08-15): ScoalaDeSabat titled
that Sabbath's video `15.08.2021 [SMV RO] - Centrul de ucenicie`. Right day and
month, wrong year — `find_video_url` returns `None`, and the ±1-day fuzzy
matcher can't bridge a five-year gap.

- **Scope**: an override always targets **one channel and one Sabbath**, and only
  ever applies to the client's *current* Sabbath (`get_current_sabbath_date()` —
  today if today is Saturday, otherwise the coming Saturday). It never applies
  retroactively to a past week. One override per channel (`UNIQUE(channel_key,
  sabbath_date)` server-side); the channels resolve independently, so one can be
  forced while the other goes through normal search.
- **Precedence** in `run_automatic_checks`:
  1. a pending **force** override — wins outright, and deletes the video already
     on disk for that Sabbath (respecting `keep_old_videos` for *other* weeks)
  2. otherwise the normal `find_video_url` search
  3. otherwise the override as a **fallback**, when the search found nothing
- **Force runs on any weekday.** The Fri/Sat gate still governs normal checks, but
  a force override is an explicit operator instruction, so it is honoured
  immediately rather than waiting for the window.
- **Applied-once bookkeeping**: `CONFIG_DIR/override_state.json`, shaped
  `{sabbath: {channel: {"sig": "<id>:<updated_at>", "file": "<filename>"}}}` and
  pruned to the current Sabbath. Deliberately **not** inside
  `auto_download_log.json`: that file's contract is `{date: {channel: status}}`
  and consumers (`scripts/dry_run_auto_download.py`) iterate every key as a
  channel — storing bookkeeping there broke CI on all five platforms.
  `load_auto_download_log()` now strips `_`-prefixed keys defensively.
  The signature stops a force override re-downloading on every check; it
  re-fires only when the override is edited.
  The filename matters because **an override's video is named after whatever it
  points at, which by definition does not carry the right date** — the existing
  file-existence pre-check matches on the date and would otherwise judge the
  video missing and re-download forever.
- **Quality variants (hosted files)**: a hosted override used to be one fixed
  file, so every client got the same bytes regardless of its `default_quality` —
  telemetry showed a 720p install pulling the full 1080p download. The manifest
  can now carry a `variants` map of `quality -> {target, filename, size}`, and
  `pick_variant()` in `overrides.py` chooses: exact match, else the closest **at
  or below** the request (someone on 480p wants a small file), else the smallest
  above. `mp3` sits outside that ladder deliberately — audio-only is never a
  substitute for video, nor the reverse. An override with no `variants` falls
  back to `target`, which is what dashboard-published overrides and pre-variant
  clients have. Server side: `ytw-telemetry/scripts/publish_override.py`.
- **Discovery without polling spam**: `GET /overrides` is guarded by an ETag over
  a server-side version counter that only moves on a mutation, so an unchanged
  poll is a bodyless 304 (~150 bytes). The client polls every 30 min on Fri/Sat
  and every 6 h otherwise (~115 requests/client/week). On top of that, `/ping`
  responses carry the current version (`ov`), so a telemetry ping the client was
  sending anyway flags staleness for free and short-circuits the wait.
- **GUI**: `_override_watch_loop` runs the poll and re-runs the automatic checks
  when the manifest changes — without it, an app sitting in the tray all week
  would never learn about a correction, since the startup check is the only
  thing that looks.
- **Server**: `overrides` + `meta` tables in `ytw-telemetry`, admin UI at
  `/ytw-telemetry/overrides-dashboard` (LAN/VPN only, nginx `allow`/`deny`).
  Hosted files live in `ytw-telemetry/data/override_files/` and are served by
  **nginx directly** (`/ytw-telemetry/override-file/`), not Flask — gunicorn runs
  a single worker and streaming a multi-GB file through it would stall telemetry
  for everyone. nginx needs traverse permission on `/home/thorsp`, granted as an
  ACL (`setfacl -m u:www-data:x /home/thorsp`) rather than `chmod o+x`, so
  `www-data` can traverse but not list the home directory.
- **Weekly health check**: `ytw-telemetry/scripts/weekly_check.py` runs the
  find-and-download of the **published release** (not `main`) every Friday and
  reports to Discord. It reads the bundled yt-dlp version out of the released
  binary's PyInstaller PYZ, because the thing that broke on 2026-08-22 was that
  frozen dependency, not the app code. See that repo's README.

### Video Player Integration
- Default: System default video player (`os.startfile` on Windows, `xdg-open` on Linux, `open` on macOS)
- Optional: Integrated mpv with custom arguments
- Supports fullscreen (via Lua script), volume (0–130), screen selection, and arbitrary mpv args

### Server hostname
The app calls `https://thorsp.net/ytw-telemetry/...` (telemetry, feedback, overrides). It used to use `thorsp.ddns.net`, and **releases already in the field still do** — both names resolve to the same nginx and are on the same certificate, so that hostname must keep working indefinitely rather than being retired. Admin pages (`/login`, `/feedback-dashboard`, `/feedback-detail/`, `/user/`, `/feedback/image/`) are restricted to LAN + WireGuard; the client API paths are deliberately public.

### Update Checking
- On startup, queries the GitHub releases API for newer versions
- Compares semantic version from `config.__version__` against the latest tag (skipped when `__version__ == "dev"`)
- Update flow: in-app prompt → silent download via `updater.download_update()` → hands off to `update_bootstrap` → relaunch
- `check_for_updates` and `auto_install_updates` settings let the user opt out or fully automate
- After a successful update, the next launch shows the changelog popup with a centered Quit button
- `last_run_version` in settings records the version that last ran, which is how the popup can cover **every** release the user skipped. The `.updated` marker only says *that* an update happened, never what it came from — and the bootstrap that performs an update is the **old** one from the installed version, so new CLI flags must never be added to it (an older `update_bootstrap` would reject them via argparse and break the update for everyone upgrading from that version)

### Feedback System
- Opened from a button on the main window
- Threaded conversation view with the developer; reply support; unread badge
- Up to multiple screenshots per message (drag-and-drop)
- System info (OS, version, hardware via `psutil`) is included with each thread to help diagnose issues
- Local cache at `CONFIG_DIR/feedback.json`; server at `https://thorsp.net/ytw-telemetry/feedback`

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
  "last_sabbath_checked": "2025-08-16",
  "last_run_version": null
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
- Progress hooks must be thread-safe and schedule UI updates on the main thread via `self.after(0, ...)`. Note the GUI test fixture patches `__init__` and mocks `after`, so anything wrapped in `self.after(0, ...)` **never runs under test** — terminal status messages are set straight from the worker thread (as the rest of those workers do) and only widget updates are marshalled
- Window icons are set once on the root via `iconphoto(True, ...)`, which makes every later Toplevel inherit them. `iconbitmap` only dresses the window it's called on (and raises on X11 for a `.ico`), which is why Settings/folder/help windows used to show Tk's default feather
- Configuration changes should trigger automatic reloading in the GUI
- System tray behavior varies by platform — test thoroughly
- The `config/` directory in the repo contains defaults; runtime configs live in the OS-specific app data dir
- `__version__` is `"dev"` in source checkouts. Code paths that depend on the real version (update check, telemetry payload) must handle the dev case — tests mock `__version__` where relevant
- Telemetry/feedback share an anonymous install ID. IP-based geo resolution is done on the client; do not move it server-side
- The auto-update flow relies on the separate `update_bootstrap` binary. Don't try to swap the running executable in-process
