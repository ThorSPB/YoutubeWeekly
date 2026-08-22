"""The download progress model.

Event shapes here are copied from real yt-dlp payloads captured against
YouTube (see the merge/mp3 probes): a 1080p download reports two streams, the
first video-only (`acodec: none`), and an mp3 reports one audio-only stream.
"""

import pytest

from app.backend.progress import (
    PROGRESS_PLAN_STATUS,
    DownloadProgress,
    streams_implied_by,
)

VIDEO_ONLY = {"format_id": "399", "vcodec": "av01.0.08M.08", "acodec": "none"}
AUDIO_ONLY = {"format_id": "251", "vcodec": "none", "acodec": "opus"}
COMBINED = {"format_id": "18", "vcodec": "avc1.42001E", "acodec": "mp4a.40.2"}

# Real byte sizes from the captured probe.
VIDEO_BYTES = 29410017
AUDIO_BYTES = 4167744


def test_streams_implied_by_first_stream():
    assert streams_implied_by(VIDEO_ONLY) == 2      # audio follows, then a merge
    assert streams_implied_by(AUDIO_ONLY) == 1      # mp3: that is the whole job
    assert streams_implied_by(COMBINED) == 1        # already has both
    assert streams_implied_by(None) == 1            # hosted file: no info dict
    assert streams_implied_by({}) == 1


# ---------------------------------------------------------------------------
# The bug this replaces: a single-stream download stuck at 50% forever.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("info, label", [
    (AUDIO_ONLY, "mp3"),
    (COMBINED, "pre-merged format"),
    (None, "Pi-hosted override file"),
])
def test_single_stream_download_reaches_100(info, label):
    p = DownloadProgress()
    p.downloading("v", 500, 1000, info)
    assert 40 < p.percent < 60, f"{label}: halfway through should read ~50%"
    p.downloading("v", 1000, 1000, info)
    p.finished_stream("v", 1000)
    assert p.complete, f"{label}: must complete"
    assert p.percent == 100.0


def test_single_stream_is_not_left_at_50_after_finishing():
    """Regression: one 'finished' used to be read as 'video done, audio next'."""
    p = DownloadProgress()
    p.downloading("song.webm", AUDIO_BYTES, AUDIO_BYTES, AUDIO_ONLY)
    p.finished_stream("song.webm", AUDIO_BYTES)
    assert p.percent == 100.0
    assert p.complete


# ---------------------------------------------------------------------------
# Two-stream merge
# ---------------------------------------------------------------------------

def test_merge_without_a_plan_splits_evenly_and_completes():
    p = DownloadProgress()
    p.downloading("v.f399.mp4", VIDEO_BYTES // 2, VIDEO_BYTES, VIDEO_ONLY)
    assert 20 < p.percent < 30, "half the video is a quarter of two even stages"
    p.finished_stream("v.f399.mp4", VIDEO_BYTES)
    assert 45 <= p.percent <= 55
    assert not p.complete, "audio is still to come"

    p.downloading("v.f251.webm", AUDIO_BYTES // 2, AUDIO_BYTES, AUDIO_ONLY)
    assert 70 < p.percent < 80
    p.finished_stream("v.f251.webm", AUDIO_BYTES)
    assert p.complete
    assert p.percent == 100.0


def test_a_byte_plan_weights_the_bar_by_real_sizes():
    """With a plan the bar tracks bytes, so the small audio stream stays small.

    Without it, audio owned half the bar despite being ~12% of the bytes.
    """
    total = VIDEO_BYTES + AUDIO_BYTES
    p = DownloadProgress()
    p.plan(streams=2, total_bytes=total)

    p.downloading("v.f399.mp4", VIDEO_BYTES, VIDEO_BYTES, VIDEO_ONLY)
    p.finished_stream("v.f399.mp4", VIDEO_BYTES)
    # The video really is ~88% of the download, and now says so.
    assert 85 < p.percent < 90, p.percent
    assert not p.complete

    p.downloading("v.f251.webm", AUDIO_BYTES, AUDIO_BYTES, AUDIO_ONLY)
    p.finished_stream("v.f251.webm", AUDIO_BYTES)
    assert p.complete and p.percent == 100.0


def test_plan_overrides_the_codec_inference():
    """An explicit stream count wins over what the first stream implies."""
    p = DownloadProgress()
    p.plan(streams=1, total_bytes=1000)
    p.downloading("only.mp4", 1000, 1000, VIDEO_ONLY)  # looks like a merge
    p.finished_stream("only.mp4", 1000)
    assert p.complete, "the plan said one stream, so one finish is the end"


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

def test_percent_never_goes_backwards():
    """Each stream restarts at 0%, and totals get revised mid-flight."""
    p = DownloadProgress()
    p.downloading("a", 900, 1000, VIDEO_ONLY)
    high = p.percent
    p.downloading("b", 1, 1000, AUDIO_ONLY)   # second stream starts near zero
    assert p.percent >= high


def test_percent_stays_under_100_until_completion():
    p = DownloadProgress()
    p.plan(streams=1, total_bytes=100)
    p.downloading("v", 100, 100, None)
    assert p.percent < 100.0, "only completion may show a full bar"
    p.finished_stream("v", 100)
    assert p.percent == 100.0


def test_missing_totals_do_not_crash_or_lie():
    p = DownloadProgress()
    p.downloading("v", 1234, None, VIDEO_ONLY)   # live streams report no total
    assert p.percent == 0.0
    p.finished_stream("v")
    p.downloading("a", 10, None, AUDIO_ONLY)
    p.finished_stream("a")
    assert p.complete and p.percent == 100.0


def test_mark_complete_is_the_backstop():
    """The caller knows the download returned clean, whatever the events did."""
    p = DownloadProgress()
    p.downloading("v.f399.mp4", 10, VIDEO_BYTES, VIDEO_ONLY)
    p.finished_stream("v.f399.mp4", VIDEO_BYTES)   # audio never arrives
    assert not p.complete
    p.mark_complete()
    assert p.complete and p.percent == 100.0


def test_reset_clears_everything():
    p = DownloadProgress()
    p.plan(streams=2, total_bytes=500)
    p.downloading("v", 250, 500, VIDEO_ONLY)
    p.reset()
    assert p.percent == 0.0 and not p.complete
    assert p.planned_total is None and p.expected_streams is None
    assert p.streams == {} and p.finished == set()


def test_plan_status_constant_is_not_a_yt_dlp_status():
    assert PROGRESS_PLAN_STATUS not in ("downloading", "finished", "error")
