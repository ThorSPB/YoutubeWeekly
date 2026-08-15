"""How overrides steer the automatic download.

Precedence under test:
  1. a force override wins outright and replaces what is already on disk
  2. otherwise the normal title-date search
  3. otherwise a fallback override, if one is set

Plus the scoping rules: current Sabbath only, one override per channel, and the
channels resolving independently of each other.
"""

import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.backend.auto_downloader import (
    APPLIED_OVERRIDES_KEY,
    load_auto_download_log,
    run_automatic_checks,
    save_auto_download_log,
)

SABBATH = "2026-08-15"       # Saturday
SABBATH_DATE_STR = "15.08.2026"
PREV_SABBATH = "2026-08-08"

FRIDAY = datetime(2026, 8, 14)
SATURDAY = datetime(2026, 8, 15)
WEDNESDAY = datetime(2026, 8, 12)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def channels():
    return [
        {"name": "Colecta", "url": "http://example.com/colecta",
         "date_format": "%d.%m.%Y", "folder": "colecta"},
        {"name": "Scoala de Sabat", "url": "http://example.com/scoala",
         "date_format": "%d.%m.%Y", "folder": "scoala_de_sabat"},
    ]


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Settings file, log file and video folders wired to a temp dir."""
    settings_path = tmp_path / "settings.json"
    video_folder = tmp_path / "videos"
    settings = {
        "enable_auto_download": True,
        "enable_notifications": False,
        "video_folder": str(video_folder),
        "default_quality": "1080p",
        "keep_old_videos": False,
        "send_telemetry": False,
        "last_sabbath_checked": None,
    }
    settings_path.write_text(json.dumps(settings))

    monkeypatch.setattr("app.backend.config.SETTINGS_FILE", str(settings_path))
    monkeypatch.setattr("app.backend.auto_downloader.AUTO_DOWNLOAD_LOG_FILE",
                        str(tmp_path / "auto_download_log.json"))

    for folder in ("colecta", "scoala_de_sabat"):
        (video_folder / folder).mkdir(parents=True)

    return {"settings": settings, "video_folder": video_folder}


@pytest.fixture
def on_day(monkeypatch):
    """Pin the auto-downloader's idea of today."""
    def _set(day):
        class MockDatetime(datetime):
            @classmethod
            def now(cls):
                return day
        monkeypatch.setattr("app.backend.auto_downloader.datetime", MockDatetime)
    return _set


def override(channel, force=False, kind="url", target="https://youtu.be/correct",
             oid=1, updated_at="2026-08-14 10:00:00", date=SABBATH, filename=None):
    return {
        "id": oid, "channel": channel, "date": date, "kind": kind,
        "target": target, "filename": filename, "force": force,
        "note": "", "updated_at": updated_at,
    }


def run(channels, manifest, **kwargs):
    """Run the checks with a given manifest, returning the download mocks."""
    with patch("app.backend.auto_downloader.fetch_overrides", return_value=(manifest, False)), \
         patch("app.backend.auto_downloader.find_video_url") as find, \
         patch("app.backend.auto_downloader.download_video") as dl_video, \
         patch("app.backend.auto_downloader.download_override") as dl_override:

        find.side_effect = kwargs.get("find_result", lambda *a, **k: (None, None))
        dl_video.return_value = None
        dl_override.return_value = None

        run_automatic_checks({}, channels, MagicMock())
        return find, dl_video, dl_override


def run_producing(channels, manifest, folder, filename, find_result=None):
    """Like run(), but the override download actually lands a file on disk.

    Necessary whenever a test asserts what happens on the *next* launch: the
    pre-check verifies the video is still there, so a mock that downloads
    nothing legitimately gets retried.
    """
    def create(*args, **kwargs):
        (folder / filename).write_text("video bytes")
        return None

    with patch("app.backend.auto_downloader.fetch_overrides", return_value=(manifest, False)), \
         patch("app.backend.auto_downloader.find_video_url") as find, \
         patch("app.backend.auto_downloader.download_video", return_value=None), \
         patch("app.backend.auto_downloader.download_override", side_effect=create) as dl_override:
        find.side_effect = find_result or nothing_found
        run_automatic_checks({}, channels, MagicMock())
        return dl_override


def found(url="https://youtu.be/found"):
    return lambda *a, **k: (url, {"type": "exact", "title": "Video"})


def nothing_found(*a, **k):
    return (None, None)


# ---------------------------------------------------------------------------
# Fallback overrides (force off)
# ---------------------------------------------------------------------------

def test_fallback_used_when_search_finds_nothing(env, channels, on_day):
    on_day(FRIDAY)
    manifest = [override("scoala_de_sabat", force=False)]

    _find, dl_video, dl_override = run(channels, manifest, find_result=nothing_found)

    assert dl_override.call_count == 1
    assert dl_override.call_args[0][0]["channel"] == "scoala_de_sabat"
    dl_video.assert_not_called()

    log = load_auto_download_log()
    assert log[SABBATH]["scoala_de_sabat"] == "downloaded"
    assert log[SABBATH]["colecta"] == "not_found"  # no override for this one


def test_search_result_beats_a_fallback_override(env, channels, on_day):
    """The operator's stated rule: a fallback never competes with a real find."""
    on_day(FRIDAY)
    manifest = [override("scoala_de_sabat", force=False)]

    _find, dl_video, dl_override = run(channels, manifest, find_result=found())

    dl_override.assert_not_called()
    assert dl_video.call_count == 2


def test_fallback_does_not_touch_an_already_downloaded_channel(env, channels, on_day):
    on_day(FRIDAY)
    save_auto_download_log({SABBATH: {"colecta": "downloaded", "scoala_de_sabat": "downloaded"}})
    for folder in ("colecta", "scoala_de_sabat"):
        (env["video_folder"] / folder / f"Studiu {SABBATH_DATE_STR}.mp4").write_text("old")

    _find, dl_video, dl_override = run(
        channels, [override("scoala_de_sabat", force=False)], find_result=nothing_found
    )

    dl_override.assert_not_called()
    dl_video.assert_not_called()


# ---------------------------------------------------------------------------
# Force overrides
# ---------------------------------------------------------------------------

def test_force_wins_over_a_successful_search(env, channels, on_day):
    on_day(FRIDAY)
    manifest = [override("scoala_de_sabat", force=True)]

    find, dl_video, dl_override = run(channels, manifest, find_result=found())

    # scoala went straight to the override without searching at all
    assert dl_override.call_count == 1
    assert dl_override.call_args[0][0]["channel"] == "scoala_de_sabat"
    assert [c[0][0] for c in find.call_args_list] == ["http://example.com/colecta"]
    assert dl_video.call_count == 1  # colecta only


def test_force_replaces_an_already_downloaded_video(env, channels, on_day):
    """The case that motivated this: the week is already 'done' but wrong."""
    on_day(FRIDAY)
    folder = env["video_folder"] / "scoala_de_sabat"
    stale = folder / f"Studiu {SABBATH_DATE_STR}.mp4"
    stale.write_text("wrong video")
    save_auto_download_log({SABBATH: {"colecta": "downloaded", "scoala_de_sabat": "downloaded"}})

    _find, _dl_video, dl_override = run(
        channels, [override("scoala_de_sabat", force=True)], find_result=nothing_found
    )

    assert not stale.exists(), "the superseded video should have been deleted"
    assert dl_override.call_count == 1
    assert load_auto_download_log()[SABBATH]["scoala_de_sabat"] == "downloaded"


def test_force_applies_outside_the_friday_saturday_window(env, channels, on_day):
    """An explicit instruction shouldn't have to wait for the weekly window."""
    on_day(WEDNESDAY)

    _find, dl_video, dl_override = run(
        channels, [override("scoala_de_sabat", force=True)], find_result=found()
    )

    assert dl_override.call_count == 1
    # the other channel is left alone until its normal window
    dl_video.assert_not_called()


def test_force_fires_only_once_per_edit(env, channels, on_day):
    on_day(FRIDAY)
    folder = env["video_folder"] / "scoala_de_sabat"
    manifest = [override("scoala_de_sabat", force=True)]

    first = run_producing(channels, manifest, folder, "corrected.mp4")
    assert first.call_count == 1

    log = load_auto_download_log()
    record = log[SABBATH][APPLIED_OVERRIDES_KEY]["scoala_de_sabat"]
    assert record["sig"] == "1:2026-08-14 10:00:00"
    assert record["file"] == "corrected.mp4"

    # Same manifest, video still on disk -> nothing to do
    second = run_producing(channels, manifest, folder, "corrected.mp4")
    second.assert_not_called()


def test_editing_a_force_override_makes_it_fire_again(env, channels, on_day):
    on_day(FRIDAY)
    folder = env["video_folder"] / "scoala_de_sabat"

    run_producing(channels,
                  [override("scoala_de_sabat", force=True, updated_at="2026-08-14 10:00:00")],
                  folder, "first.mp4")

    again = run_producing(
        channels,
        [override("scoala_de_sabat", force=True, updated_at="2026-08-14 18:45:00",
                  target="https://youtu.be/corrected-again")],
        folder, "second.mp4",
    )

    assert again.call_count == 1
    assert again.call_args[0][0]["target"] == "https://youtu.be/corrected-again"
    assert not (folder / "first.mp4").exists(), "the superseded video should be gone"
    assert (folder / "second.mp4").exists()


def test_a_download_that_produced_nothing_is_retried(env, channels, on_day):
    """No file on disk means the week isn't done, whatever the log says."""
    on_day(FRIDAY)
    manifest = [override("scoala_de_sabat", force=True)]

    _f, _v, first = run(channels, manifest, find_result=nothing_found)
    assert first.call_count == 1

    _f, _v, second = run(channels, manifest, find_result=nothing_found)
    assert second.call_count == 1


def test_force_keeps_other_weeks_when_keep_old_is_on(env, channels, on_day, tmp_path):
    on_day(FRIDAY)
    settings_path = tmp_path / "settings.json"
    settings = json.loads(settings_path.read_text())
    settings["keep_old_videos"] = True
    settings_path.write_text(json.dumps(settings))

    folder = env["video_folder"] / "scoala_de_sabat"
    this_week = folder / f"Studiu {SABBATH_DATE_STR}.mp4"
    last_week = folder / "Studiu 08.08.2026.mp4"
    this_week.write_text("wrong")
    last_week.write_text("keep me")
    save_auto_download_log({SABBATH: {"colecta": "downloaded", "scoala_de_sabat": "downloaded"}})

    run(channels, [override("scoala_de_sabat", force=True)], find_result=nothing_found)

    assert not this_week.exists()
    assert last_week.exists(), "keep_old_videos must still protect other weeks"


# ---------------------------------------------------------------------------
# Scoping
# ---------------------------------------------------------------------------

def test_override_for_another_sabbath_is_ignored(env, channels, on_day):
    on_day(FRIDAY)
    manifest = [override("scoala_de_sabat", force=True, date=PREV_SABBATH)]

    _f, _v, dl_override = run(channels, manifest, find_result=nothing_found)

    dl_override.assert_not_called()
    assert load_auto_download_log()[SABBATH]["scoala_de_sabat"] == "not_found"


def test_a_future_override_waits_for_its_sabbath(env, channels, on_day):
    on_day(FRIDAY)
    manifest = [override("scoala_de_sabat", force=True, date="2026-08-22")]

    _f, _v, dl_override = run(channels, manifest, find_result=nothing_found)

    dl_override.assert_not_called()


def test_channels_are_independent(env, channels, on_day):
    """One channel forced, the other resolving normally, in the same run."""
    on_day(FRIDAY)
    manifest = [override("scoala_de_sabat", force=True, target="https://youtu.be/forced")]

    _find, dl_video, dl_override = run(channels, manifest, find_result=found())

    assert dl_override.call_count == 1
    assert dl_override.call_args[0][0]["channel"] == "scoala_de_sabat"
    assert dl_video.call_count == 1
    assert "colecta" in dl_video.call_args[0][1]

    log = load_auto_download_log()
    assert log[SABBATH]["colecta"] == "downloaded"
    assert log[SABBATH]["scoala_de_sabat"] == "downloaded"


def test_both_channels_can_be_overridden_at_once(env, channels, on_day):
    on_day(FRIDAY)
    manifest = [
        override("colecta", force=True, oid=1),
        override("scoala_de_sabat", force=True, oid=2),
    ]

    _find, dl_video, dl_override = run(channels, manifest, find_result=found())

    assert dl_override.call_count == 2
    dl_video.assert_not_called()


# ---------------------------------------------------------------------------
# Bookkeeping
# ---------------------------------------------------------------------------

def test_override_download_is_not_re_run_on_the_next_launch(env, channels, on_day):
    """An override's filename carries the wrong date by definition.

    The file-existence pre-check matches on the Sabbath's date, so without the
    recorded filename it would judge the video missing and download it again on
    every single launch.
    """
    on_day(FRIDAY)
    folder = env["video_folder"] / "scoala_de_sabat"

    def create_file(*args, **kwargs):
        (folder / "Studiu 15.08.2021.mp4").write_text("the video, misdated by the uploader")
        return None

    with patch("app.backend.auto_downloader.fetch_overrides",
               return_value=([override("scoala_de_sabat", force=True)], False)), \
         patch("app.backend.auto_downloader.find_video_url", side_effect=nothing_found), \
         patch("app.backend.auto_downloader.download_video", return_value=None), \
         patch("app.backend.auto_downloader.download_override", side_effect=create_file):
        run_automatic_checks({}, channels, MagicMock())

    record = load_auto_download_log()[SABBATH][APPLIED_OVERRIDES_KEY]["scoala_de_sabat"]
    assert record["file"] == "Studiu 15.08.2021.mp4"

    # Second launch: same manifest, file still present -> nothing happens
    _f, _v, second = run(channels, [override("scoala_de_sabat", force=True)],
                         find_result=nothing_found)
    second.assert_not_called()


def test_deleting_the_override_video_requeues_it(env, channels, on_day):
    on_day(FRIDAY)
    save_auto_download_log({
        SABBATH: {
            "colecta": "downloaded",
            "scoala_de_sabat": "downloaded",
            APPLIED_OVERRIDES_KEY: {
                "scoala_de_sabat": {"sig": "1:2026-08-14 10:00:00", "file": "gone.mp4"},
            },
        }
    })
    (env["video_folder"] / "colecta" / f"Studiu {SABBATH_DATE_STR}.mp4").write_text("x")

    _f, _v, dl_override = run(channels, [override("scoala_de_sabat", force=True)],
                              find_result=nothing_found)

    assert dl_override.call_count == 1


def test_no_manifest_behaves_exactly_as_before(env, channels, on_day):
    """Every existing path must be untouched when no override exists."""
    on_day(FRIDAY)

    _find, dl_video, dl_override = run(channels, [], find_result=found())

    dl_override.assert_not_called()
    assert dl_video.call_count == 2
    log = load_auto_download_log()
    assert log[SABBATH]["colecta"] == "downloaded"
    assert log[SABBATH]["scoala_de_sabat"] == "downloaded"


def test_a_failing_override_is_recorded_as_an_error(env, channels, on_day):
    on_day(FRIDAY)
    with patch("app.backend.auto_downloader.fetch_overrides",
               return_value=([override("scoala_de_sabat", force=True)], False)), \
         patch("app.backend.auto_downloader.find_video_url", side_effect=nothing_found), \
         patch("app.backend.auto_downloader.download_video", return_value=None), \
         patch("app.backend.auto_downloader.download_override", return_value="404 Not Found"):
        run_automatic_checks({}, channels, MagicMock())

    log = load_auto_download_log()
    assert log[SABBATH]["scoala_de_sabat"] == "error"
    # and it stays unapplied, so the next run retries it
    assert "scoala_de_sabat" not in log[SABBATH].get(APPLIED_OVERRIDES_KEY, {})
