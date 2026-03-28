import os
import sys
import subprocess
import shlex


def build_mpv_args(settings, file_path, script_path=None):
    """Build the argument list for launching mpv."""
    mpv_path = settings.get("mpv_path")
    mpv_args = [mpv_path, file_path]

    if settings.get("mpv_fullscreen", False) and script_path:
        mpv_args.append(f"--script={script_path}")

    if settings.get("mpv_volume") is not None:
        mpv_args.append(f"--volume={settings.get('mpv_volume')}")

    if settings.get("mpv_screen") != "Default":
        mpv_args.append(f"--screen={settings.get('mpv_screen')}")

    custom_args = settings.get("mpv_custom_args", "").strip()
    if custom_args:
        mpv_args.extend(shlex.split(custom_args))

    return mpv_args


def play_video(settings, file_path, script_path=None):
    """Play a video using mpv (if configured) or the system default player.

    Returns None on success, or an error message string on failure.
    """
    try:
        if settings.get("use_mpv", False) and settings.get("mpv_path"):
            mpv_args = build_mpv_args(settings, file_path, script_path)

            if os.name == 'nt':
                process = subprocess.Popen(mpv_args, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            else:
                process = subprocess.Popen(mpv_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

            stdout, stderr = process.communicate()
            if process.returncode != 0:
                return stderr.decode().strip() if stderr else "Unknown MPV error."
        else:
            if os.name == 'nt':
                os.startfile(file_path)
            elif os.name == 'posix':
                subprocess.call(['open', file_path] if sys.platform == 'darwin' else ['xdg-open', file_path])
    except Exception as e:
        return str(e)

    return None
