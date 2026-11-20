import os
import sys
import subprocess
import shlex

from app.i18n import t

#: Files that carry no picture. mpv opens no window for a file without a video
#: stream (its --force-window defaults to "no"), so an MP3 played with nothing on
#: screen to pause or close, and closing YoutubeWeekly did not stop it either:
#: mpv is its own process (church PC, 2026-11-20, a karaoke MP3 from "Other").
AUDIO_EXTENSIONS = frozenset({".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma"})

#: The window an audio file gets when "Also play audio files in MPV" is on: small,
#: with mpv's controls always showing. Off by default; audio then goes to the
#: system's default app.
AUDIO_WINDOW_ARGS = ("--force-window=immediate", "--geometry=600x140",
                     "--script-opts=osc-visibility=always")


def is_audio_file(file_path):
    return os.path.splitext(file_path)[1].lower() in AUDIO_EXTENSIONS


def build_mpv_args(settings, file_path, script_path=None):
    """Build the argument list for launching mpv.

    An audio file gets a small window with its controls instead of none, and it
    stays on the main screen: no fullscreen and no --screen, so a backing track
    started during a service never covers what the projector shows.
    """
    mpv_path = settings.get("mpv_path")
    mpv_args = [mpv_path, file_path]
    audio = is_audio_file(file_path)
    if audio:
        mpv_args.extend(AUDIO_WINDOW_ARGS)

    if settings.get("mpv_fullscreen", False) and script_path and not audio:
        mpv_args.append(f"--script={script_path}")

    if settings.get("mpv_volume") is not None:
        mpv_args.append(f"--volume={settings.get('mpv_volume')}")

    # Only pass --screen when a specific monitor index is selected. The default
    # is represented by anything that isn't a numeric index (empty string from
    # newer saves, legacy "Default", or translated labels like "Implicit").
    mpv_screen = str(settings.get("mpv_screen", "") or "")
    if mpv_screen.isdigit() and not audio:
        mpv_args.append(f"--screen={mpv_screen}")

    custom_args = settings.get("mpv_custom_args", "").strip()
    if custom_args:
        mpv_args.extend(shlex.split(custom_args))

    return mpv_args


def play_video(settings, file_path, script_path=None):
    """Play a video using mpv (if configured) or the system default player.

    Returns None on success, or an error message string on failure.
    """
    try:
        use_mpv = settings.get("use_mpv", False) and settings.get("mpv_path")
        # Audio goes to the system's default app (Windows Media Player) unless
        # "Also play audio files in MPV" is on: an mpv window is a source in the
        # church PC's OBS scene, so it would show on the projector (2026-11-20).
        if use_mpv and is_audio_file(file_path) and not settings.get("mpv_for_audio", False):
            use_mpv = False
        if use_mpv:
            mpv_args = build_mpv_args(settings, file_path, script_path)

            process = subprocess.Popen(mpv_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

            stdout, stderr = process.communicate()
            if process.returncode != 0:
                return stderr.decode().strip() if stderr else t("err_mpv_unknown")
        else:
            if os.name == 'nt':
                os.startfile(file_path)
            elif os.name == 'posix':
                subprocess.call(['open', file_path] if sys.platform == 'darwin' else ['xdg-open', file_path])
    except Exception as e:
        return str(e)

    return None
