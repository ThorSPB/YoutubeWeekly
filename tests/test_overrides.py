"""Tests for the server-driven video override mechanism."""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock

import pytest

import app.backend.overrides as overrides
from app.backend.overrides import (
    _safe_filename,
    clear_channel_videos,
    download_hosted_file,
    fetch_overrides,
    get_override,
    is_stale,
    load_cache,
    note_ping_version,
    override_signature,
    save_cache,
    should_poll,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_override(channel="scoala_de_sabat", date="2026-08-15", force=False,
                  kind="url", target="https://youtu.be/abc", oid=1,
                  updated_at="2026-08-15 09:00:00", filename=None):
    return {
        "id": oid,
        "channel": channel,
        "date": date,
        "kind": kind,
        "target": target,
        "filename": filename,
        "force": force,
        "note": "",
        "updated_at": updated_at,
    }


def fake_requests(status_code=200, payload=None, etag='W/"ov-2"', capture=None):
    """A stand-in for the requests module used inside overrides.py."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"ETag": etag} if etag else {}
    resp.json.return_value = payload if payload is not None else {}

    mod = MagicMock()

    def _get(url, headers=None, timeout=None, **kwargs):
        if capture is not None:
            capture.append({"url": url, "headers": headers or {}})
        return resp

    mod.get.side_effect = _get
    return mod


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def test_cache_starts_empty():
    cache = load_cache()
    assert cache["overrides"] == []
    assert cache["version"] == 0
    assert cache["etag"] is None


def test_cache_round_trip():
    save_cache({"version": 5, "etag": 'W/"ov-5"', "overrides": [make_override()], "fetched_at": None})
    cache = load_cache()
    assert cache["version"] == 5
    assert cache["etag"] == 'W/"ov-5"'
    assert len(cache["overrides"]) == 1


def test_corrupt_cache_is_survivable(monkeypatch):
    with open(overrides.OVERRIDES_CACHE_FILE, "w", encoding="utf-8") as f:
        f.write("{not json")
    assert load_cache()["overrides"] == []


# ---------------------------------------------------------------------------
# Fetching / conditional GET
# ---------------------------------------------------------------------------

def test_fetch_stores_manifest_and_reports_change(monkeypatch):
    payload = {"version": 2, "overrides": [make_override()]}
    monkeypatch.setattr(overrides, "requests", fake_requests(200, payload))

    result, changed = fetch_overrides()

    assert changed is True
    assert len(result) == 1
    assert load_cache()["version"] == 2
    assert load_cache()["etag"] == 'W/"ov-2"'


def test_fetch_sends_if_none_match_when_etag_cached(monkeypatch):
    save_cache({"version": 2, "etag": 'W/"ov-2"', "overrides": [], "fetched_at": None})
    capture = []
    monkeypatch.setattr(overrides, "requests", fake_requests(304, etag='W/"ov-2"', capture=capture))

    fetch_overrides()

    assert capture[0]["headers"]["If-None-Match"] == 'W/"ov-2"'


def test_304_keeps_cache_and_reports_no_change(monkeypatch):
    cached = [make_override()]
    save_cache({"version": 2, "etag": 'W/"ov-2"', "overrides": cached, "fetched_at": None})
    monkeypatch.setattr(overrides, "requests", fake_requests(304))

    result, changed = fetch_overrides()

    assert changed is False
    assert result == cached
    assert load_cache()["version"] == 2


def test_identical_manifest_is_not_a_change(monkeypatch):
    """A 200 that happens to carry the same content must not retrigger work."""
    same = [make_override()]
    save_cache({"version": 2, "etag": 'W/"ov-2"', "overrides": same, "fetched_at": None})
    monkeypatch.setattr(overrides, "requests", fake_requests(200, {"version": 3, "overrides": same}))

    _result, changed = fetch_overrides()

    assert changed is False


def test_force_refresh_skips_conditional_header(monkeypatch):
    save_cache({"version": 2, "etag": 'W/"ov-2"', "overrides": [], "fetched_at": None})
    capture = []
    monkeypatch.setattr(overrides, "requests", fake_requests(200, {"version": 3, "overrides": []}, capture=capture))

    fetch_overrides(force=True)

    assert "If-None-Match" not in capture[0]["headers"]


def test_network_failure_falls_back_to_cache(monkeypatch):
    cached = [make_override()]
    save_cache({"version": 2, "etag": 'W/"ov-2"', "overrides": cached, "fetched_at": None})

    mod = MagicMock()
    mod.get.side_effect = OSError("no route to host")
    monkeypatch.setattr(overrides, "requests", mod)

    result, changed = fetch_overrides()

    assert result == cached
    assert changed is False


def test_server_error_falls_back_to_cache(monkeypatch):
    save_cache({"version": 2, "etag": 'W/"ov-2"', "overrides": [make_override()], "fetched_at": None})
    monkeypatch.setattr(overrides, "requests", fake_requests(500))

    result, changed = fetch_overrides()

    assert len(result) == 1
    assert changed is False


def test_malformed_manifest_does_not_clobber_cache(monkeypatch):
    cached = [make_override()]
    save_cache({"version": 2, "etag": 'W/"ov-2"', "overrides": cached, "fetched_at": None})
    monkeypatch.setattr(overrides, "requests", fake_requests(200, {"version": 3, "overrides": "nonsense"}))

    result, changed = fetch_overrides()

    assert result == cached
    assert changed is False
    assert load_cache()["version"] == 2


# ---------------------------------------------------------------------------
# Ping-driven staleness
# ---------------------------------------------------------------------------

def test_not_stale_without_a_ping():
    save_cache({"version": 4, "etag": None, "overrides": [], "fetched_at": None})
    assert is_stale() is False


def test_ping_advertising_newer_version_marks_stale():
    save_cache({"version": 4, "etag": None, "overrides": [], "fetched_at": None})
    note_ping_version(5)
    assert is_stale() is True


def test_ping_advertising_same_version_is_not_stale():
    save_cache({"version": 4, "etag": None, "overrides": [], "fetched_at": None})
    note_ping_version(4)
    assert is_stale() is False


def test_garbage_ping_version_is_ignored():
    save_cache({"version": 4, "etag": None, "overrides": [], "fetched_at": None})
    note_ping_version("not-a-number")
    note_ping_version(None)
    assert is_stale() is False


# ---------------------------------------------------------------------------
# Poll cadence
# ---------------------------------------------------------------------------

def test_first_poll_is_always_due():
    assert should_poll(None, 1000.0) is True


@pytest.mark.parametrize("day, interval_ok, interval_short", [
    (datetime(2026, 8, 14), 30 * 60, 29 * 60),      # Friday
    (datetime(2026, 8, 15), 30 * 60, 29 * 60),      # Saturday
])
def test_sabbath_days_poll_every_30_minutes(day, interval_ok, interval_short):
    assert should_poll(0.0, interval_ok, now=day) is True
    assert should_poll(0.0, interval_short, now=day) is False


@pytest.mark.parametrize("day", [
    datetime(2026, 8, 16),  # Sunday
    datetime(2026, 8, 12),  # Wednesday
])
def test_other_days_poll_every_6_hours(day):
    assert should_poll(0.0, 6 * 60 * 60, now=day) is True
    assert should_poll(0.0, 5 * 60 * 60, now=day) is False


def test_weekly_request_count_stays_small():
    """Guard against someone tightening the cadence into a spam loop."""
    weekly = 2 * (24 * 3600 // overrides.POLL_INTERVAL_SABBATH) \
        + 5 * (24 * 3600 // overrides.POLL_INTERVAL_NORMAL)
    assert weekly < 200


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def test_get_override_matches_channel_and_date():
    manifest = [
        make_override(channel="colecta", date="2026-08-15", oid=1),
        make_override(channel="scoala_de_sabat", date="2026-08-15", oid=2),
    ]
    assert get_override("scoala_de_sabat", "2026-08-15", manifest)["id"] == 2


def test_get_override_ignores_other_dates():
    manifest = [make_override(channel="scoala_de_sabat", date="2026-08-08")]
    assert get_override("scoala_de_sabat", "2026-08-15", manifest) is None


def test_get_override_ignores_other_channels():
    manifest = [make_override(channel="colecta", date="2026-08-15")]
    assert get_override("scoala_de_sabat", "2026-08-15", manifest) is None


def test_get_override_reads_cache_when_manifest_not_passed():
    save_cache({"version": 1, "etag": None, "overrides": [make_override()], "fetched_at": None})
    assert get_override("scoala_de_sabat", "2026-08-15") is not None


def test_override_without_target_is_ignored():
    manifest = [make_override(target="")]
    assert get_override("scoala_de_sabat", "2026-08-15", manifest) is None


def test_signature_changes_when_override_is_edited():
    a = make_override(updated_at="2026-08-15 09:00:00")
    b = make_override(updated_at="2026-08-15 11:30:00")
    assert override_signature(a) != override_signature(b)
    assert override_signature(a) == override_signature(make_override())
    assert override_signature(None) is None


# ---------------------------------------------------------------------------
# Hosted file download
# ---------------------------------------------------------------------------

class FakeStream:
    def __init__(self, chunks, status_code=200, headers=None):
        self.chunks = chunks
        self.status_code = status_code
        self.headers = headers if headers is not None else {}

    def iter_content(self, chunk_size=None):
        return iter(self.chunks)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_hosted_file_is_written_and_named_from_manifest(tmp_path, monkeypatch):
    mod = MagicMock()
    mod.get.return_value = FakeStream([b"abc", b"def"], headers={"Content-Length": "6"})
    monkeypatch.setattr(overrides, "requests", mod)

    o = make_override(kind="file", target="https://pi/override-file/sabat.mp4", filename="sabat.mp4")
    error = download_hosted_file(o, str(tmp_path))

    assert error is None
    assert (tmp_path / "sabat.mp4").read_bytes() == b"abcdef"
    assert not list(tmp_path.glob("*.part"))


def test_hosted_file_reports_progress(tmp_path, monkeypatch):
    mod = MagicMock()
    mod.get.return_value = FakeStream([b"a" * 100, b"b" * 100], headers={"Content-Length": "200"})
    monkeypatch.setattr(overrides, "requests", mod)

    events = []
    o = make_override(kind="file", filename="v.mp4")
    download_hosted_file(o, str(tmp_path), progress_hook=events.append)

    downloading = [e for e in events if e["status"] == "downloading"]
    assert [e["downloaded_bytes"] for e in downloading] == [100, 200]
    assert all(e["total_bytes"] == 200 for e in downloading)
    assert events[-1]["status"] == "finished"


def test_hosted_file_http_error_returns_message(tmp_path, monkeypatch):
    mod = MagicMock()
    mod.get.return_value = FakeStream([], status_code=404)
    monkeypatch.setattr(overrides, "requests", mod)

    error = download_hosted_file(make_override(kind="file", filename="v.mp4"), str(tmp_path))

    assert error and "404" in error
    assert list(tmp_path.iterdir()) == []


def test_interrupted_download_leaves_no_usable_file(tmp_path, monkeypatch):
    """A partial transfer must never be mistaken for this week's video."""
    def exploding_chunks():
        yield b"start"
        raise IOError("connection reset")

    mod = MagicMock()
    mod.get.return_value = FakeStream(exploding_chunks(), headers={"Content-Length": "999"})
    monkeypatch.setattr(overrides, "requests", mod)

    error = download_hosted_file(make_override(kind="file", filename="v.mp4"), str(tmp_path))

    assert error is not None
    assert list(tmp_path.iterdir()) == []


def test_filename_falls_back_to_url_when_manifest_has_none(tmp_path, monkeypatch):
    mod = MagicMock()
    mod.get.return_value = FakeStream([b"x"])
    monkeypatch.setattr(overrides, "requests", mod)

    o = make_override(kind="file", target="https://pi/override-file/from%20url.mp4", filename=None)
    download_hosted_file(o, str(tmp_path))

    assert (tmp_path / "from url.mp4").exists()


@pytest.mark.parametrize("hostile, expected", [
    ("../../etc/passwd", "passwd"),
    ("/absolute/path.mp4", "path.mp4"),
    ("..\\..\\windows\\system32.mp4", "system32.mp4"),
    ("", "override_video.mp4"),
])
def test_filenames_cannot_escape_the_target_folder(hostile, expected):
    assert _safe_filename(hostile) == expected


def test_hostile_filename_stays_inside_folder(tmp_path, monkeypatch):
    mod = MagicMock()
    mod.get.return_value = FakeStream([b"x"])
    monkeypatch.setattr(overrides, "requests", mod)

    o = make_override(kind="file", filename="../../escaped.mp4")
    download_hosted_file(o, str(tmp_path))

    assert (tmp_path / "escaped.mp4").exists()
    assert not (tmp_path.parent.parent / "escaped.mp4").exists()


# ---------------------------------------------------------------------------
# Replacing existing videos
# ---------------------------------------------------------------------------

def test_clear_removes_every_video_when_no_dates_given(tmp_path):
    for name in ("a.mp4", "b.mkv", "notes.txt"):
        (tmp_path / name).write_text("x")

    deleted = clear_channel_videos(str(tmp_path))

    assert sorted(deleted) == ["a.mp4", "b.mkv"]
    assert (tmp_path / "notes.txt").exists()  # non-media untouched


def test_clear_narrows_to_matching_dates(tmp_path):
    (tmp_path / "Studiu 15.08.2026.mp4").write_text("x")
    (tmp_path / "Studiu 08.08.2026.mp4").write_text("x")

    deleted = clear_channel_videos(str(tmp_path), ["15.08.2026"])

    assert deleted == ["Studiu 15.08.2026.mp4"]
    assert (tmp_path / "Studiu 08.08.2026.mp4").exists()


def test_clear_removes_stale_partials(tmp_path):
    (tmp_path / "half.mp4.part").write_text("x")
    assert clear_channel_videos(str(tmp_path)) == ["half.mp4.part"]


def test_clear_on_missing_folder_is_harmless(tmp_path):
    assert clear_channel_videos(str(tmp_path / "nope")) == []
    assert clear_channel_videos(None) == []


def test_clear_channel_videos_spares_excluded(tmp_path):
    """The file the download just produced survives its own replacement sweep."""
    produced = tmp_path / "Corectat 15.08.2026.mp4"
    produced.write_text("the replacement")
    stale = tmp_path / "Studiu 15.08.2026.mp4"
    stale.write_text("the wrong video")

    deleted = clear_channel_videos(
        str(tmp_path), ["15.08.2026"], exclude=[produced.name]
    )

    assert deleted == ["Studiu 15.08.2026.mp4"]
    assert produced.exists()
    assert not stale.exists()
