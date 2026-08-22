"""In-app feedback system for YoutubeWeekly."""

import io
import json
import os
import platform
import subprocess
from datetime import datetime, timezone

import psutil
import requests
from PIL import Image

from app.backend.config import CONFIG_DIR, __version__
from app.backend.telemetry import _get_install_id, _get_location, _sanitize_settings

# thorsp.net, not thorsp.ddns.net: same nginx, same certificate (the cert
# covers thorsp.ddns.net, thorsp.net and www.thorsp.net), but a real domain
# rather than a DDNS hostname. Builds already in the field keep calling the
# thorsp.ddns.net form, so **that hostname has to keep working indefinitely**
# - it cannot be retired once a release has shipped with it baked in.
FEEDBACK_URL = "https://thorsp.net/ytw-telemetry/feedback"
FEEDBACK_FILE = os.path.join(CONFIG_DIR, "feedback.json")


def load_local_feedback():
    """Load feedback threads from local cache."""
    try:
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        pass
    return []


def save_local_feedback(threads):
    """Save feedback threads to local cache."""
    try:
        os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(threads, f, indent=2)
    except (IOError, OSError):
        pass


def compress_screenshot(image_path, max_size=(1280, 720), max_bytes=500_000):
    """Resize and compress a screenshot to JPEG bytes."""
    img = Image.open(image_path)
    img.thumbnail(max_size, Image.LANCZOS)
    if img.mode == "RGBA":
        img = img.convert("RGB")

    quality = 85
    while quality >= 30:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        if buffer.tell() <= max_bytes:
            buffer.seek(0)
            return buffer.read()
        quality -= 10

    buffer.seek(0)
    return buffer.read()


def _get_cpu_name():
    """Get CPU model name cross-platform."""
    name = platform.processor()
    if name:
        return name
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["wmic", "cpu", "get", "name"], text=True, timeout=5
            )
            lines = [l.strip() for l in out.strip().splitlines() if l.strip() and l.strip() != "Name"]
            if lines:
                return lines[0]
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        elif platform.system() == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=5
            )
            return out.strip()
    except Exception:
        pass
    return "Unknown"


def get_system_stats():
    """Gather CPU and RAM stats for feedback."""
    try:
        proc = psutil.Process(os.getpid())
        mem = psutil.virtual_memory()
        freq = psutil.cpu_freq()
        return {
            "cpu_name": _get_cpu_name(),
            "cpu_cores": psutil.cpu_count(logical=True),
            "cpu_freq_mhz": round(freq.current) if freq else None,
            "cpu_freq_max_mhz": round(freq.max) if freq and freq.max else None,
            "ram_total_gb": round(mem.total / (1024 ** 3), 1),
            "ram_used_gb": round(mem.used / (1024 ** 3), 1),
            "ram_used_pct": mem.percent,
            "app_ram_mb": round(proc.memory_info().rss / (1024 ** 2), 1),
        }
    except Exception:
        return {}


def submit_feedback(category, message, image_paths=None, settings=None):
    """Submit feedback to server. Returns (success, feedback_id or error message)."""
    try:
        location = _get_location()
        form_data = {
            "install_id": _get_install_id(),
            "category": category,
            "message": message,
            "app_version": __version__,
            "platform": f"{platform.system()} {platform.release()}",
            "city": location["city"],
            "country": location["country"],
        }
        if settings:
            form_data["settings"] = json.dumps(_sanitize_settings(settings))

        system_stats = get_system_stats()
        if system_stats:
            form_data["system_stats"] = json.dumps(system_stats)

        files = []
        if image_paths:
            for i, path in enumerate(image_paths):
                if path and os.path.exists(path):
                    img_bytes = compress_screenshot(path)
                    files.append(("screenshots", (f"screenshot_{i}.jpg", img_bytes, "image/jpeg")))

        r = requests.post(FEEDBACK_URL, data=form_data, files=files or None, timeout=15)
        if r.status_code == 200:
            data = r.json()
            feedback_id = data.get("feedback_id")

            # Save locally
            threads = load_local_feedback()
            threads.append({
                "id": feedback_id,
                "category": category,
                "message": message,
                "has_image": bool(image_paths),
                "status": "sent",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "replies": [],
            })
            save_local_feedback(threads)
            return True, feedback_id
        elif r.status_code == 429:
            return False, "Rate limited. Please wait before sending more feedback."
        else:
            return False, f"Server error ({r.status_code})"
    except requests.ConnectionError:
        return False, "Could not connect to server. Check your internet connection."
    except Exception as e:
        return False, str(e)


def reply_to_feedback(feedback_id, message):
    """Send a user reply to a feedback thread. Returns (success, error message or None)."""
    try:
        install_id = _get_install_id()
        r = requests.post(
            f"{FEEDBACK_URL}/{feedback_id}/reply",
            json={"install_id": install_id, "message": message},
            timeout=10,
        )
        if r.status_code == 200:
            return True, None
        elif r.status_code == 429:
            return False, "Rate limited. Please wait before sending another reply."
        else:
            return False, f"Server error ({r.status_code})"
    except requests.ConnectionError:
        return False, "Could not connect to server. Check your internet connection."
    except Exception as e:
        return False, str(e)


def fetch_feedback():
    """Fetch feedback threads from server and merge with local cache."""
    try:
        install_id = _get_install_id()
        r = requests.get(f"{FEEDBACK_URL}/{install_id}", timeout=10)
        if r.status_code == 200:
            threads = r.json()
            save_local_feedback(threads)
            return threads
    except Exception as e:
        print(f"[Feedback] Failed to fetch from server: {e}")
    # Fall back to local cache
    return load_local_feedback()
