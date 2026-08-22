"""Anonymous telemetry for YoutubeWeekly usage analytics."""

import json
import os
import platform
import threading
import uuid
from datetime import datetime, timezone

import requests

from app.backend.config import CONFIG_DIR, __version__, load_settings

# thorsp.net, not thorsp.ddns.net: same nginx, same certificate (the cert
# covers thorsp.ddns.net, thorsp.net and www.thorsp.net), but a real domain
# rather than a DDNS hostname. Builds already in the field keep calling the
# thorsp.ddns.net form, so **that hostname has to keep working indefinitely**
# - it cannot be retired once a release has shipped with it baked in.
TELEMETRY_URL = "https://thorsp.net/ytw-telemetry/ping"
INSTALL_ID_FILE = os.path.join(CONFIG_DIR, "install_id")
GEO_API_URL = "http://ip-api.com/json/?fields=city,country"  # Free tier requires HTTP

_location_cache = None
_location_lock = threading.Lock()


def _get_install_id():
    """Get or create a persistent anonymous install ID."""
    try:
        if os.path.exists(INSTALL_ID_FILE):
            with open(INSTALL_ID_FILE, "r") as f:
                install_id = f.read().strip()
                if install_id:
                    return install_id
        install_id = str(uuid.uuid4())
        os.makedirs(os.path.dirname(INSTALL_ID_FILE), exist_ok=True)
        with open(INSTALL_ID_FILE, "w") as f:
            f.write(install_id)
        return install_id
    except (IOError, OSError):
        return str(uuid.uuid4())


def _get_location():
    """Resolve approximate location from IP (client-side, IP never sent to our server)."""
    global _location_cache
    with _location_lock:
        if _location_cache is not None:
            return _location_cache
    try:
        r = requests.get(GEO_API_URL, timeout=5)
        data = r.json()
        loc = {"city": data.get("city", "Unknown"), "country": data.get("country", "Unknown")}
    except Exception:
        loc = {"city": "Unknown", "country": "Unknown"}
    with _location_lock:
        _location_cache = loc
    return loc


def _sanitize_settings(settings):
    """Extract only non-sensitive boolean/string settings for analytics."""
    keys = [
        "keep_old_videos",
        "default_quality",
        "enable_auto_download",
        "enable_notifications",
        "start_with_system",
        "check_for_updates",
        "auto_install_updates",
        "use_mpv",
        "mpv_fullscreen",
        "language",
    ]
    return {k: settings.get(k) for k in keys if k in settings}


def _is_ci():
    """True when running on a build agent rather than a user's machine.

    The release workflow stamps the real version into config.py before running
    the test suite, which defeats the `__version__ == "dev"` guard below. The
    tests exercise run_automatic_checks without stubbing this function, so every
    release used to register each build runner as a brand-new install — ten fake
    users and twenty phantom downloads across v1.3.1 to v1.5.0, counted as real
    on the dashboard.
    """
    return any(os.environ.get(v) for v in ("CI", "GITHUB_ACTIONS", "BUILD_NUMBER"))


def send_telemetry_ping(settings, videos_downloaded, session_type="manual",
                        others_quality=None):
    """Fire-and-forget telemetry ping. Runs in a daemon thread, never blocks."""
    if __version__ == "dev":
        return
    if _is_ci():
        return
    if not settings.get("send_telemetry", True):
        return

    def _send():
        try:
            location = _get_location()
            payload = {
                "install_id": _get_install_id(),
                "app_version": __version__,
                "platform": f"{platform.system()} {platform.release()}",
                "city": location["city"],
                "country": location["country"],
                "settings": _sanitize_settings(settings),
                "videos_downloaded": videos_downloaded,
                "session_type": session_type,
                "others_quality": others_quality,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            r = requests.post(TELEMETRY_URL, json=payload, timeout=5)
            # The response advertises the current override-manifest version, so
            # a ping we were sending anyway tells us for free whether our cached
            # manifest is stale. Imported lazily to avoid a circular import.
            try:
                from app.backend.overrides import note_ping_version
                note_ping_version(r.json().get("ov"))
            except Exception:
                pass
        except Exception:
            pass

    t = threading.Thread(target=_send, daemon=True)
    t.start()
