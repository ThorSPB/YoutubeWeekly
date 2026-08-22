"""Server-driven video overrides.

When the uploader types the wrong date in a video title (a wrong *year*, say),
title-date matching can't find the video and the app reports "not found". An
override lets the operator point a channel straight at the right video for a
given Sabbath, from the telemetry dashboard.

Two modes:

* **fallback** (``force`` false) — only consulted when the app's own search
  comes up empty. Harmless to leave in place; a working search always wins.
* **force** (``force`` true) — authoritative. It beats the search, and if the
  client already downloaded something for that Sabbath it deletes it and pulls
  the override instead.

Sources are either a link (anything yt-dlp handles) or a video file hosted on
the Pi, which is fetched over plain HTTP with the same progress reporting.

Scope: an override only ever applies to the client's **current Sabbath** — the
coming Saturday, or today when today is Saturday. Overrides for other dates in
the manifest are ignored until that Sabbath comes around.

Network cost
------------
Discovery is a conditional GET against a single tiny manifest. The server's
ETag is derived from a version counter that only moves when an override
changes, so a poll that finds nothing new is a bodyless ``304`` — a few hundred
bytes. Polling is adaptive (see :func:`should_poll`): frequent on Friday and
Saturday when it matters, slow the rest of the week. On top of that, every
telemetry ping response carries the current version, so a client that pings for
any reason learns it is stale for free and refreshes immediately instead of
waiting for its next scheduled poll.

The manifest request carries no install ID and no identifying data, so it runs
regardless of the telemetry opt-out.
"""

import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlparse

import requests

from app.backend.config import CONFIG_DIR
from app.backend.progress import PROGRESS_PLAN_STATUS

# thorsp.net, not thorsp.ddns.net: same nginx, same certificate (the cert
# covers thorsp.ddns.net, thorsp.net and www.thorsp.net), but a real domain
# rather than a DDNS hostname. Builds already in the field keep calling the
# thorsp.ddns.net form, so **that hostname has to keep working indefinitely**
# - it cannot be retired once a release has shipped with it baked in.
OVERRIDES_URL = "https://thorsp.net/ytw-telemetry/overrides"
OVERRIDES_CACHE_FILE = os.path.join(CONFIG_DIR, "overrides.json")

# Which override produced which file, per Sabbath. Deliberately NOT stored in
# auto_download_log.json: that file's contract is {date: {channel: status}}, and
# anything else in there gets iterated as if it were a channel.
OVERRIDE_STATE_FILE = os.path.join(CONFIG_DIR, "override_state.json")

# Poll cadence. Overrides only matter for the current Sabbath, so we check often
# on Friday/Saturday and rarely otherwise. Roughly 115 requests per client per
# week, nearly all of them 304s.
POLL_INTERVAL_SABBATH = 30 * 60       # Fri/Sat: every 30 minutes
POLL_INTERVAL_NORMAL = 6 * 60 * 60    # rest of the week: every 6 hours

REQUEST_TIMEOUT = 10
DOWNLOAD_CHUNK = 1024 * 256

_cache_lock = threading.Lock()

# Manifest version last advertised by a telemetry ping response. When this runs
# ahead of the version we hold, we know we're stale without polling.
_ping_version = None
# Version of the manifest we currently hold, mirrored in memory so the watcher
# thread's staleness check costs nothing (no disk read, no network).
_current_version = None
_version_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def _empty_cache():
    return {"version": 0, "etag": None, "overrides": [], "fetched_at": None}


def load_cache():
    """Load the last manifest we successfully fetched."""
    global _current_version
    with _cache_lock:
        cache = _empty_cache()
        try:
            with open(OVERRIDES_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("overrides"), list):
                cache = data
        except (FileNotFoundError, json.JSONDecodeError, IOError, OSError):
            pass
    with _version_lock:
        _current_version = cache.get("version", 0)
    return cache


def save_cache(cache):
    global _current_version
    with _cache_lock:
        try:
            os.makedirs(os.path.dirname(OVERRIDES_CACHE_FILE), exist_ok=True)
            with open(OVERRIDES_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except (IOError, OSError) as e:
            logging.warning(f"[Overrides] Could not write cache: {e}")
    with _version_lock:
        _current_version = cache.get("version", 0)


def load_applied_overrides(sabbath_date):
    """Which override was applied for each channel this Sabbath.

    Returns ``{channel: {"sig": ..., "file": ...}}``. The signature stops a force
    override re-firing on every check; the filename is how the caller recognises
    the downloaded video, whose name does not carry the Sabbath's date.
    """
    try:
        with open(OVERRIDE_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        entry = data.get(sabbath_date)
        return entry if isinstance(entry, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, IOError, OSError):
        return {}


def save_applied_overrides(sabbath_date, applied):
    """Persist this Sabbath's records, discarding every earlier Sabbath."""
    try:
        os.makedirs(os.path.dirname(OVERRIDE_STATE_FILE), exist_ok=True)
        with open(OVERRIDE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({sabbath_date: applied}, f, indent=2)
    except (IOError, OSError) as e:
        logging.warning(f"[Overrides] Could not write override state: {e}")


def note_ping_version(version):
    """Record the manifest version a /ping response advertised."""
    global _ping_version
    if version is None:
        return
    try:
        version = int(version)
    except (TypeError, ValueError):
        return
    with _version_lock:
        _ping_version = version


def is_stale():
    """True when a ping told us about a manifest newer than the one we hold.

    Deliberately cheap — no disk, no network — so the watcher thread can check
    it on every tick.
    """
    with _version_lock:
        seen, held = _ping_version, _current_version
    if seen is None:
        return False
    if held is None:
        held = load_cache().get("version", 0)
    return seen > held


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_overrides(force=False):
    """Refresh the manifest. Returns ``(overrides, changed)``.

    ``changed`` is True only when the server sent a manifest that differs from
    the cached one, which is the signal the GUI uses to re-run its checks. A
    network failure is not an error here — we simply keep using the cache.
    """
    cache = load_cache()
    headers = {}
    if cache.get("etag") and not force:
        headers["If-None-Match"] = cache["etag"]

    try:
        r = requests.get(OVERRIDES_URL, headers=headers, timeout=REQUEST_TIMEOUT)
    except Exception as e:
        logging.debug(f"[Overrides] Fetch failed, using cache: {e}")
        return cache.get("overrides", []), False

    if r.status_code == 304:
        cache["fetched_at"] = datetime.now(timezone.utc).isoformat()
        save_cache(cache)
        return cache.get("overrides", []), False

    if r.status_code != 200:
        logging.debug(f"[Overrides] Server returned {r.status_code}, using cache")
        return cache.get("overrides", []), False

    try:
        data = r.json()
        overrides = data["overrides"]
        version = int(data.get("version", 0))
        if not isinstance(overrides, list):
            raise ValueError("overrides is not a list")
    except Exception as e:
        logging.warning(f"[Overrides] Malformed manifest: {e}")
        return cache.get("overrides", []), False

    changed = overrides != cache.get("overrides", [])
    save_cache({
        "version": version,
        "etag": r.headers.get("ETag"),
        "overrides": overrides,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    })
    if changed:
        logging.info(f"[Overrides] Manifest updated to v{version}: {len(overrides)} active")
    return overrides, changed


def should_poll(last_poll_ts, now_ts, now=None):
    """Is another manifest poll due?

    Fast cadence on Friday and Saturday — the days an override can still change
    the outcome — and a slow heartbeat otherwise.
    """
    if last_poll_ts is None:
        return True
    now = now or datetime.now()
    interval = POLL_INTERVAL_SABBATH if now.weekday() in (4, 5) else POLL_INTERVAL_NORMAL
    return (now_ts - last_poll_ts) >= interval


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def get_override(channel_key, sabbath_date, overrides=None):
    """The active override for this channel and Sabbath, or None.

    ``sabbath_date`` is ``YYYY-MM-DD`` and must be the caller's *current*
    Sabbath — overrides never apply retroactively to an earlier week.
    """
    if overrides is None:
        overrides = load_cache().get("overrides", [])
    for o in overrides:
        if o.get("channel") == channel_key and o.get("date") == sabbath_date:
            if o.get("target"):
                return o
    return None


def override_signature(override):
    """Stable identity of an override's *content*.

    Recorded in the auto-download log once applied, so a force override fires
    exactly once per edit rather than re-downloading on every check.
    """
    if not override:
        return None
    return f"{override.get('id')}:{override.get('updated_at')}"


# ---------------------------------------------------------------------------
# Downloading
# ---------------------------------------------------------------------------

_FILENAME_STAR_RE = re.compile(r"filename\*=(?:UTF-8'')?([^;]+)", re.IGNORECASE)
_FILENAME_RE = re.compile(r'filename="?([^";]+)"?', re.IGNORECASE)


def _safe_filename(name, fallback="override_video.mp4"):
    """Reduce an arbitrary name to a bare filename.

    Both separators are handled explicitly rather than leaning on
    os.path.basename, which ignores backslashes off Windows — the app runs on
    all three platforms and should behave identically on each.
    """
    name = unquote(name or "").replace("\\", "/")
    name = name.rsplit("/", 1)[-1].strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(". ")
    return name or fallback


def _filename_for(override, response):
    """Best available name for a hosted file: manifest, then header, then URL."""
    if override.get("filename"):
        return _safe_filename(override["filename"])

    disposition = response.headers.get("Content-Disposition", "")
    m = _FILENAME_STAR_RE.search(disposition) or _FILENAME_RE.search(disposition)
    if m:
        return _safe_filename(m.group(1))

    return _safe_filename(os.path.basename(urlparse(override["target"]).path))


def download_hosted_file(override, folder, progress_hook=None, quality_pref=None):
    """Stream a Pi-hosted video into ``folder``.

    Returns None on success or an error string, matching ``download_video``.
    Emits yt-dlp-shaped progress events so the GUI's existing hook works
    unchanged. Downloads to a ``.part`` file and renames on completion, so an
    interrupted transfer can never be mistaken for this week's video.
    """
    url, wanted_name = (
        pick_variant(override, quality_pref) if quality_pref
        else (override["target"], override.get("filename"))
    )
    try:
        os.makedirs(folder, exist_ok=True)
        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as r:
            if r.status_code != 200:
                return f"Server returned {r.status_code} for override file"

            filename = _filename_for(
                dict(override, filename=wanted_name) if wanted_name else override, r)
            final_path = os.path.join(folder, filename)
            part_path = final_path + ".part"

            total = r.headers.get("Content-Length")
            total = int(total) if total and total.isdigit() else None
            downloaded = 0

            if progress_hook:
                # One stream, already merged - say so, or a UI that assumes the
                # yt-dlp video+audio pair waits forever for a second stream.
                try:
                    progress_hook({
                        "status": PROGRESS_PLAN_STATUS,
                        "streams": 1,
                        "total_bytes": total,
                    })
                except Exception:
                    pass

            with open(part_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=DOWNLOAD_CHUNK):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_hook:
                        try:
                            progress_hook({
                                "status": "downloading",
                                "downloaded_bytes": downloaded,
                                "total_bytes": total,
                                "filename": final_path,
                            })
                        except Exception:
                            pass

        os.replace(part_path, final_path)
        if progress_hook:
            try:
                progress_hook({"status": "finished", "filename": final_path})
            except Exception:
                pass

        logging.info(f"[Overrides] Downloaded hosted file to {final_path}")
        return None

    except Exception as e:
        logging.error(f"[Overrides] Hosted file download failed: {e}")
        try:
            if os.path.exists(part_path):
                os.remove(part_path)
        except (OSError, UnboundLocalError, NameError):
            pass
        return str(e)


# Best first. Mirrors the GUI's quality selector; "mp3" is deliberately not on
# this ladder - it is audio only, so it is never a substitute for a video and a
# video is never a substitute for it.
QUALITY_LADDER = ("max", "4k", "2k", "1080p", "720p", "480p")


def pick_variant(override, quality_pref="1080p"):
    """Choose which hosted file to fetch for the user's quality setting.

    A hosted override used to be one fixed file, so everybody got the same bytes
    no matter what quality they had chosen - a 720p user was handed the full
    1080p download. The manifest can now carry a `variants` map, and the client
    picks from it.

    Returns `(url, filename)`. Falls back to the override's own target, which is
    what an override published without variants has - and what a client that
    predates this got anyway.
    """
    default = (override.get("target"), override.get("filename"))
    variants = override.get("variants") or {}
    if not isinstance(variants, dict) or not variants:
        return default

    def resolve(key):
        entry = variants.get(key)
        if not isinstance(entry, dict) or not entry.get("target"):
            return None
        return entry["target"], entry.get("filename") or override.get("filename")

    # mp3 stands apart: only an actual audio variant will do.
    if quality_pref == "mp3":
        return resolve("mp3") or default

    if quality_pref in variants:
        exact = resolve(quality_pref)
        if exact:
            return exact

    available = [q for q in QUALITY_LADDER if q in variants]
    if not available:
        return default

    if quality_pref not in QUALITY_LADDER:
        # An unknown setting: hand over the best we have rather than nothing.
        return resolve(available[0]) or default

    wanted = QUALITY_LADDER.index(quality_pref)
    # Prefer the closest one *at or below* what they asked for - someone who
    # chose 480p wants a small file - then the smallest thing above it.
    below = [q for q in available if QUALITY_LADDER.index(q) >= wanted]
    if below:
        return resolve(below[0]) or default
    return resolve(available[-1]) or default


def download_override(override, folder, quality_pref="1080p", progress_hook=None,
                      protect=False):
    """Download whatever an override points at. Returns None or an error string."""
    # Imported here: downloader imports tkinter, and this module is also used by
    # headless code paths and tests.
    from app.backend.downloader import download_video

    if override.get("kind") == "file":
        return download_hosted_file(override, folder, progress_hook=progress_hook,
                                    quality_pref=quality_pref)

    return download_video(
        override["target"], folder, quality_pref,
        protect=protect, progress_hook=progress_hook,
    )


# ---------------------------------------------------------------------------
# Replacing an existing download
# ---------------------------------------------------------------------------

def clear_channel_videos(folder, date_strings=None, exclude=None):
    """Remove the videos a force override is replacing.

    ``date_strings`` narrows deletion to files carrying one of those date
    spellings; without it every media file in the channel folder goes.
    ``exclude`` spares specific filenames - the file the current download just
    produced, so forcing an override onto a video already on disk cannot delete
    the result it just fetched. Returns the list of deleted filenames.
    """
    if not folder or not os.path.isdir(folder):
        return []

    media_ext = (".mp4", ".mkv", ".webm", ".mov", ".avi", ".m4v", ".mp3", ".m4a", ".part")
    needles = [d.lower() for d in (date_strings or []) if d]
    spared = {e for e in (exclude or []) if e}
    deleted = []

    for name in os.listdir(folder):
        if not name.lower().endswith(media_ext):
            continue
        if name in spared:
            continue
        if needles and not any(n in name.lower() for n in needles):
            continue
        try:
            os.remove(os.path.join(folder, name))
            deleted.append(name)
            logging.info(f"[Overrides] Removed superseded video: {name}")
        except OSError as e:
            logging.warning(f"[Overrides] Could not remove {name}: {e}")

    return deleted
