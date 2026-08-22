"""Folding a download's progress events into one honest percentage.

Lives in the backend so it can be tested without a display, and outside
``downloader`` so headless callers don't drag in tkinter to use it.

yt-dlp reports progress per *stream*. A 1080p download is two of them - a
video-only stream and an audio-only stream, merged by ffmpeg afterwards - while
an mp3, a pre-merged format, or a Pi-hosted override file is a single stream.
Turning that into one bar needs to know how many streams are coming and how big
they are, and guessing either is what produced the two bugs this replaces:

* Splitting the bar evenly per stream made a 1080p download crawl through the
  video and then leap through the audio - for the videos this app fetches the
  audio is well under a fifth of the bytes, but it owned half the bar.
* Assuming two streams left a single-stream download stuck at 50% forever: the
  one "finished" event was read as "video done, audio next", and no second
  stream ever arrived.
"""

# Synthetic progress event a downloader emits before any bytes move, carrying
# the stream count and byte total it is about to fetch. yt-dlp never emits this
# status itself.
PROGRESS_PLAN_STATUS = "ytw_plan"


def streams_implied_by(info):
    """How many streams a download will fetch, judged from its first one.

    A video-only stream means yt-dlp will fetch the audio separately and merge
    the two. Anything else - audio-only, or a format that already carries both -
    is the whole download on its own.
    """
    info = info or {}
    vcodec = info.get("vcodec")
    acodec = info.get("acodec")
    if vcodec and vcodec != "none" and acodec == "none":
        return 2
    return 1


class DownloadProgress:
    """Accumulates progress events and reports a single 0-100 percentage.

    Percentages only ever move forward: yt-dlp restarts at 0% for each stream,
    and the totals can be revised mid-flight, so a raw reading would jump
    backwards.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.planned_total = None      # bytes across every stream, if known
        self.expected_streams = None   # how many streams to expect, if known
        self.streams = {}              # filename -> [downloaded, total]
        self.finished = set()          # filenames that reported "finished"
        self.percent = 0.0
        self.complete = False

    # -- events ---------------------------------------------------------

    def plan(self, streams=None, total_bytes=None):
        """Record what a downloader says it is about to fetch."""
        if streams:
            self.expected_streams = streams
        if total_bytes:
            self.planned_total = total_bytes

    def downloading(self, filename, downloaded_bytes, total_bytes=None, info=None):
        if self.expected_streams is None:
            self.expected_streams = streams_implied_by(info)
        key = filename or ""
        entry = self.streams.setdefault(key, [0, None])
        entry[0] = downloaded_bytes or 0
        if total_bytes:
            entry[1] = total_bytes
        return self._recompute()

    def finished_stream(self, filename, total_bytes=None):
        """One stream completed. Counts it whole, and completes the download
        once every expected stream has reported in."""
        key = filename or ""
        entry = self.streams.setdefault(key, [0, None])
        total = total_bytes or entry[1] or entry[0]
        entry[0] = total
        entry[1] = total
        self.finished.add(key)

        if self.expected_streams and len(self.finished) >= self.expected_streams:
            return self.mark_complete()
        return self._recompute()

    def mark_complete(self):
        """Declare the whole download done.

        The caller knows this for certain - its download call returned without
        an error - so it is the backstop for any stream arrangement this model
        did not predict. Without it, an unexpected shape leaves the bar parked
        short of the end.
        """
        self.complete = True
        self.percent = 100.0
        return self.percent

    # -- rendering ------------------------------------------------------

    def _recompute(self):
        raw = self._raw_percent()
        # Clamp below 100 so only completion shows a full bar.
        raw = max(0.0, min(raw, 99.9))
        self.percent = max(self.percent, raw)
        return self.percent

    def _raw_percent(self):
        downloaded = sum(s[0] for s in self.streams.values())

        if self.planned_total:
            return downloaded / self.planned_total * 100.0

        # No byte plan: give each expected stream an equal share of the bar and
        # fill the current one by its own progress.
        expected = self.expected_streams or 1
        share = 100.0 / expected
        done = min(len(self.finished), expected)
        current = 0.0
        for name, (got, total) in self.streams.items():
            if name in self.finished or not total:
                continue
            current = max(current, min(got / total, 1.0))
        return min(done + current, float(expected)) * share
