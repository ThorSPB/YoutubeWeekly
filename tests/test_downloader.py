import pytest
import os
import json
import yt_dlp
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from app.backend.progress import PROGRESS_PLAN_STATUS, PROGRESS_RESET_STATUS
from app.backend.downloader import (
    FALLBACK_PLAYER_CLIENTS,
    load_protected_videos,
    add_protected_video,
    get_next_saturday,
    format_romanian_date,
    find_video_url,
    delete_old_videos,
    download_video,
    get_recent_sabbaths,
    is_partial_download,
    list_playable_files,
    purge_partial_downloads,
    build_download_plan,
    folder_snapshot,
    newly_downloaded_file,
)

# Fixture for mocking settings.json
@pytest.fixture
def mock_settings_file(tmp_path):
    settings_dir = tmp_path / "config"
    settings_dir.mkdir()
    settings_path = settings_dir / "settings.json"
    initial_settings = {
        "protected_videos": {
            "channel1": ["video_a.mp4"]
        }
    }
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(initial_settings, f)

    with patch('app.backend.downloader.SETTINGS_FILE', str(settings_path)):
        yield settings_path

# Test for load_protected_videos
def test_load_protected_videos(mock_settings_file):
    protected = load_protected_videos()
    assert protected == {"channel1": ["video_a.mp4"]}

# Test for add_protected_video
def test_add_protected_video_new_video(mock_settings_file):
    add_protected_video("channel1", "video_b.mp4")
    with open(mock_settings_file, "r", encoding="utf-8") as f:
        settings = json.load(f)
    assert "video_b.mp4" in settings["protected_videos"]["channel1"]

def test_add_protected_video_existing_video(mock_settings_file):
    add_protected_video("channel1", "video_a.mp4") # Add existing video
    with open(mock_settings_file, "r", encoding="utf-8") as f:
        settings = json.load(f)
    assert settings["protected_videos"]["channel1"].count("video_a.mp4") == 1

def test_add_protected_video_new_channel(mock_settings_file):
    add_protected_video("channel2", "video_c.mp4")
    with open(mock_settings_file, "r", encoding="utf-8") as f:
        settings = json.load(f)
    assert "video_c.mp4" in settings["protected_videos"]["channel2"]

# Test for get_next_saturday
@pytest.mark.parametrize("today_weekday, expected_days_ahead", [
    (0, 5), # Monday
    (1, 4), # Tuesday
    (2, 3), # Wednesday
    (3, 2), # Thursday
    (4, 1), # Friday
    (5, 0), # Saturday
    (6, 6), # Sunday
])
def test_get_next_saturday(monkeypatch, today_weekday, expected_days_ahead):
    mock_today = datetime(2024, 7, 15) + timedelta(days=today_weekday - datetime(2024, 7, 15).weekday())
    class MockDatetime(datetime):
        @classmethod
        def today(cls):
            return mock_today
    monkeypatch.setattr('app.backend.downloader.datetime', MockDatetime)
    
    expected_date = (mock_today + timedelta(days=expected_days_ahead)).strftime("%d.%m.%Y")
    assert get_next_saturday() == expected_date

# Test for format_romanian_date
@pytest.mark.parametrize("date_obj, expected_format", [
    (datetime(2024, 1, 1), "1 ianuarie 2024"),
    (datetime(2024, 7, 15), "15 iulie 2024"),
    (datetime(2024, 12, 25), "25 decembrie 2024"),
])
def test_format_romanian_date(date_obj, expected_format):
    assert format_romanian_date(date_obj) == expected_format

# Test for find_video_url
def test_find_video_url_found(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"id": "video1", "title": "Video Title 15.07.2024"},
                {"id": "video2", "title": "Another Video 15 iulie 2024"},
                {"id": "video3", "title": "Some other video"},
            ]
        }
        url, match_info = find_video_url("http://example.com/channel", "15.07.2024")
        assert url == "https://www.youtube.com/watch?v=video1"
        assert match_info["type"] == "exact"

def test_find_video_url_not_found(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"id": "video1", "title": "Video Title 10.07.2024"},
            ]
        }
        url, _ = find_video_url("http://example.com/channel", "15.07.2024")
        assert url is None

def test_find_video_url_diaspora_excluded(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"id": "video1", "title": "Video Title 15.07.2024 diaspora"},
            ]
        }
        url, _ = find_video_url("http://example.com/channel", "15.07.2024")
        assert url is None

def test_find_video_url_extraction_error(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.side_effect = Exception("Extraction failed")
        url, _ = find_video_url("http://example.com/channel", "15.07.2024")
        assert url is None

def test_find_video_url_invalid_date_format(monkeypatch):
    url, _ = find_video_url("http://example.com/channel", "invalid-date")
    assert url is None

# Test for delete_old_videos
def test_delete_old_videos_no_keep_old(monkeypatch, tmp_path):
    video_folder = tmp_path / "test_channel"
    video_folder.mkdir()
    (video_folder / "old_video.mp4").write_text("content")
    (video_folder / "protected_video.mp4").write_text("content")
    (video_folder / "other_file.txt").write_text("content")

    monkeypatch.setattr('app.backend.downloader.os.listdir', lambda x: ["old_video.mp4", "protected_video.mp4", "other_file.txt"])
    monkeypatch.setattr('app.backend.downloader.os.path.basename', lambda x: "test_channel")
    mock_os_remove = MagicMock()
    monkeypatch.setattr('app.backend.downloader.os.remove', mock_os_remove)
    monkeypatch.setattr('app.backend.downloader.load_protected_videos', lambda: {"test_channel": ["protected_video.mp4"]})

    delete_old_videos(str(video_folder), keep_old=False)
    # delete_old_videos deletes ALL .mp4 files when keep_old=False (ignores protected)
    assert mock_os_remove.call_count == 2
    called_with_files = [args[0] for args, kwargs in mock_os_remove.call_args_list]
    assert str(video_folder / "old_video.mp4") in called_with_files
    assert str(video_folder / "protected_video.mp4") in called_with_files

def test_delete_old_videos_keep_old(monkeypatch, tmp_path):
    video_folder = tmp_path / "test_channel"
    video_folder.mkdir()
    (video_folder / "old_video.mp4").write_text("content")

    monkeypatch.setattr('app.backend.downloader.os.listdir', lambda x: ["old_video.mp4"])
    monkeypatch.setattr('app.backend.downloader.os.path.basename', lambda x: "test_channel")
    mock_os_remove = MagicMock()
    monkeypatch.setattr('app.backend.downloader.os.remove', mock_os_remove)
    monkeypatch.setattr('app.backend.downloader.load_protected_videos', lambda: {})

    delete_old_videos(str(video_folder), keep_old=True)
    mock_os_remove.assert_not_called()

def test_delete_old_videos_no_videos(monkeypatch, tmp_path):
    video_folder = tmp_path / "test_channel"
    video_folder.mkdir()

    monkeypatch.setattr('app.backend.downloader.os.listdir', lambda x: [])
    monkeypatch.setattr('app.backend.downloader.os.path.basename', lambda x: "test_channel")
    mock_os_remove = MagicMock()
    monkeypatch.setattr('app.backend.downloader.os.remove', mock_os_remove)
    monkeypatch.setattr('app.backend.downloader.load_protected_videos', lambda: {})

    delete_old_videos(str(video_folder), keep_old=False)
    mock_os_remove.assert_not_called()

# Test for download_video
@pytest.fixture
def mock_download_dependencies(monkeypatch):
    mock_os_path_exists = MagicMock(return_value=False)
    mock_os_listdir = MagicMock(return_value=[])
    mock_os_makedirs = MagicMock()
    mock_add_protected_video = MagicMock()
    mock_ydl = MagicMock()
    mock_ydl_instance = MagicMock()
    mock_ydl.return_value.__enter__.return_value = mock_ydl_instance
    
    monkeypatch.setattr('app.backend.downloader.os.path.exists', mock_os_path_exists)
    monkeypatch.setattr('app.backend.downloader.os.listdir', mock_os_listdir)
    monkeypatch.setattr('app.backend.downloader.os.makedirs', mock_os_makedirs)
    monkeypatch.setattr('app.backend.downloader.add_protected_video', mock_add_protected_video)
    monkeypatch.setattr('app.backend.downloader.yt_dlp.YoutubeDL', mock_ydl)
    monkeypatch.setattr('app.backend.downloader.load_settings', lambda: ({"ffmpeg_path": "/usr/bin/ffmpeg"}, []))

    return {
        "mock_os_path_exists": mock_os_path_exists,
        "mock_os_listdir": mock_os_listdir,
        "mock_os_makedirs": mock_os_makedirs,
        "mock_add_protected_video": mock_add_protected_video,
        "mock_ydl": mock_ydl,
        "mock_ydl_instance": mock_ydl_instance
    }

def test_download_video_invalid_folder(mock_download_dependencies):
    download_video("http://example.com/video", "")
    mock_download_dependencies["mock_os_makedirs"].assert_not_called()
    mock_download_dependencies["mock_ydl"].assert_not_called()

def test_download_video_already_exists(mock_download_dependencies):
    mock_download_dependencies["mock_os_path_exists"].return_value = True
    mock_download_dependencies["mock_os_listdir"].return_value = ["some_video_id.mp4"]
    download_video("http://example.com/video?v=some_video_id", "/tmp/videos")
    mock_download_dependencies["mock_os_makedirs"].assert_not_called()
    mock_download_dependencies["mock_ydl"].assert_not_called()

def test_download_video_1080p(mock_download_dependencies):
    download_video("http://example.com/video", "/tmp/videos", quality_pref="1080p")
    mock_download_dependencies["mock_os_makedirs"].assert_any_call("/tmp/videos", exist_ok=True)
    args, kwargs = mock_download_dependencies["mock_ydl"].call_args
    assert args[0]['format'] == 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
    assert args[0]['merge_output_format'] == 'mp4'
    mock_download_dependencies["mock_ydl_instance"].download.assert_called_once_with(["http://example.com/video"])

def test_download_video_mp3(mock_download_dependencies):
    download_video("http://example.com/video", "/tmp/videos", quality_pref="mp3")
    mock_download_dependencies["mock_os_makedirs"].assert_any_call("/tmp/videos", exist_ok=True)
    args, kwargs = mock_download_dependencies["mock_ydl"].call_args
    assert args[0]['format'] == 'bestaudio/best'
    assert args[0]['merge_output_format'] == 'mp3'
    assert args[0]['postprocessors'][0]['key'] == 'FFmpegExtractAudio'
    mock_download_dependencies["mock_ydl_instance"].download.assert_called_once_with(["http://example.com/video"])

def test_download_video_protect(mock_download_dependencies):
    mock_download_dependencies["mock_os_listdir"].return_value = ["video_to_protect.mp4"]
    mock_download_dependencies["mock_ydl_instance"].extract_info.return_value = {
        'title': 'video_to_protect',
        'ext': 'mp4'
    }
    download_video("http://example.com/video?v=video_to_protect", "/tmp/videos", protect=True)
    mock_download_dependencies["mock_add_protected_video"].assert_called_once_with("videos", "video_to_protect.mp4")

def test_download_video_download_failure(mock_download_dependencies):
    mock_download_dependencies["mock_ydl_instance"].download.side_effect = Exception("Download error")
    error = download_video("http://example.com/video", "/tmp/videos")
    # Two runs: the plain one, then the wider-player-client retry.
    assert mock_download_dependencies["mock_ydl_instance"].download.call_count == 2
    # The message the user sees describes the download they asked for, not the
    # fallback clients they never chose.
    assert error == "Download error"


def _player_clients_of(call):
    """The player_client list a YoutubeDL(...) call was given, if any."""
    args, _ = call
    return (args[0].get("extractor_args") or {}).get("youtube", {}).get("player_client")


def test_download_video_no_retry_when_the_first_attempt_works(mock_download_dependencies):
    assert download_video("http://example.com/video", "/tmp/videos") is None
    calls = mock_download_dependencies["mock_ydl"].call_args_list
    assert len(calls) == 1
    # A working download must not pay for extra InnerTube round-trips.
    assert _player_clients_of(calls[0]) is None


def test_download_video_retries_across_more_player_clients(mock_download_dependencies):
    """A channel YouTube hides from yt-dlp's default clients still downloads.

    Reproduces the 2026-09-07 report: `visionos` answers UNPLAYABLE for the
    whole channel, so the first attempt fails with YouTube's misleading "This
    video is not available" - and `android`, in the fallback list, serves it.
    """
    instance = mock_download_dependencies["mock_ydl_instance"]
    instance.download.side_effect = [
        yt_dlp.utils.DownloadError("ERROR: [youtube] X: This video is not available"),
        None,
    ]

    assert download_video("http://example.com/video", "/tmp/videos") is None

    calls = mock_download_dependencies["mock_ydl"].call_args_list
    assert len(calls) == 2
    assert _player_clients_of(calls[0]) is None
    assert _player_clients_of(calls[1]) == list(FALLBACK_PLAYER_CLIENTS)
    # The default has to stay in the list, or the retry would trade a 1080p
    # stream for whatever the older clients happen to offer.
    assert "default" in FALLBACK_PLAYER_CLIENTS


def test_download_video_retry_restarts_the_progress_bar(mock_download_dependencies):
    """The failed attempt's high-water mark must not stick.

    DownloadProgress only ever moves forward, so a retry that starts from zero
    bytes needs an explicit reset or the bar reports the abandoned attempt.
    """
    instance = mock_download_dependencies["mock_ydl_instance"]
    instance.download.side_effect = [Exception("boom"), None]
    statuses = []

    download_video("http://example.com/video", "/tmp/videos",
                   progress_hook=lambda d: statuses.append(d.get("status")))

    assert PROGRESS_RESET_STATUS in statuses
    # It has to land between the two attempts' plans, not after them.
    assert statuses.index(PROGRESS_RESET_STATUS) < len(statuses) - 1
    assert statuses[statuses.index(PROGRESS_RESET_STATUS) + 1] == PROGRESS_PLAN_STATUS

# Test for get_recent_sabbaths
@pytest.mark.parametrize("n, expected_sabbaths", [
    (1, ["13.07.2024"]), # Assuming today is 15.07.2024 (Monday)
    (2, ["13.07.2024", "06.07.2024"]),
])
def test_get_recent_sabbaths(monkeypatch, n, expected_sabbaths):
    mock_today = datetime(2024, 7, 15) # A Monday
    class MockDatetime(datetime):
        @classmethod
        def today(cls):
            return mock_today
    monkeypatch.setattr('app.backend.downloader.datetime', MockDatetime)
    
    sabbaths = get_recent_sabbaths(n=n)
    assert sabbaths == expected_sabbaths


def test_find_video_url_fuzzy_one_day_off(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"id": "video1", "title": "Video Title 14.07.2024"},  # One day before 15.07.2024
            ]
        }
        url, match_info = find_video_url("http://example.com/channel", "15.07.2024")
        assert url == "https://www.youtube.com/watch?v=video1"
        assert match_info["type"] == "fuzzy"
        assert "1 day" in match_info["reason"]

def test_find_video_url_fuzzy_delimiter_mismatch(monkeypatch):
    with patch('app.backend.downloader.yt_dlp.YoutubeDL') as MockYoutubeDL:
        MockYoutubeDL.return_value.__enter__.return_value.extract_info.return_value = {
            "entries": [
                {"id": "video1", "title": "Video Title 15 07.2024"},  # Space instead of dot
            ]
        }
        url, match_info = find_video_url("http://example.com/channel", "15.07.2024")
        assert url == "https://www.youtube.com/watch?v=video1"
        assert match_info["type"] == "fuzzy"
        assert "delimiter" in match_info["reason"]


# ---------------------------------------------------------------------------
# Unfinished downloads
#
# A 1080p download fetches video and audio as two separate streams and merges
# them at the end. If it dies in between, the ".part" left behind holds only the
# video half - it plays as picture with no sound. It must never be listed as
# playable, must never satisfy an "already downloaded" check, and must be
# cleaned up. (Regression: the 2026-08-22 church outage.)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, expected", [
    ("Studiu 15.08.2026.f137.mp4.part", True),
    ("Studiu 15.08.2026.f399.mp4.part", True),
    ("Studiu 15.08.2026.mp4.ytdl", True),
    ("Studiu 15.08.2026.temp", True),
    ("STUDIU.MP4.PART", True),          # case-insensitive
    ("Studiu 15.08.2026.mp4", False),
    ("Studiu 15.08.2026.mp3", False),
    ("partial_notes.mp4", False),       # "part" in the name is not a suffix
])
def test_is_partial_download(name, expected):
    assert is_partial_download(name) is expected


def test_list_playable_files_excludes_partials(tmp_path):
    (tmp_path / "good.mp4").write_text("v")
    (tmp_path / "audio.mp3").write_text("a")
    (tmp_path / "half.f137.mp4.part").write_text("v-only")
    (tmp_path / "scratch.mp4.ytdl").write_text("x")
    (tmp_path / "subdir").mkdir()

    assert sorted(list_playable_files(str(tmp_path))) == ["audio.mp3", "good.mp4"]


def test_list_playable_files_on_missing_folder_is_empty(tmp_path):
    assert list_playable_files(str(tmp_path / "nope")) == []


def test_purge_partial_downloads_removes_only_partials(tmp_path):
    keep = tmp_path / "good.mp4"
    keep.write_text("v")
    part = tmp_path / "half.f399.mp4.part"
    part.write_text("v-only")
    ytdl = tmp_path / "half.mp4.ytdl"
    ytdl.write_text("x")

    removed = purge_partial_downloads(str(tmp_path))

    assert sorted(removed) == ["half.f399.mp4.part", "half.mp4.ytdl"]
    assert keep.exists()
    assert not part.exists()
    assert not ytdl.exists()


def test_purge_partial_downloads_on_missing_folder_is_empty(tmp_path):
    assert purge_partial_downloads(str(tmp_path / "nope")) == []


def test_delete_old_videos_spares_the_keep_list(tmp_path):
    """Re-fetching a video already on disk must not delete its own result."""
    produced = tmp_path / "Studiu 15.08.2026.mp4"
    produced.write_text("the video we just confirmed")
    stale = tmp_path / "Studiu 08.08.2026.mp4"
    stale.write_text("last week")

    delete_old_videos(str(tmp_path), False, keep=[produced.name])

    assert produced.exists(), "the file named in keep= must survive"
    assert not stale.exists(), "everything else still goes"


def test_delete_old_videos_without_keep_is_unchanged(tmp_path):
    video = tmp_path / "Studiu 15.08.2026.mp4"
    video.write_text("v")
    delete_old_videos(str(tmp_path), False)
    assert not video.exists()


def test_download_video_failure_purges_partials(tmp_path, monkeypatch):
    """A failed download takes its half-written leftovers with it."""
    part = tmp_path / "Studiu 15.08.2026.f137.mp4.part"
    part.write_text("video-only bytes")
    survivor = tmp_path / "Studiu 08.08.2026.mp4"
    survivor.write_text("last week")

    mock_ydl = MagicMock()
    mock_ydl.return_value.__enter__.return_value.download.side_effect = \
        Exception("ERROR: unable to download video data: HTTP Error 403: Forbidden")
    monkeypatch.setattr("app.backend.downloader.yt_dlp.YoutubeDL", mock_ydl)
    monkeypatch.setattr("app.backend.downloader.load_settings",
                        lambda: ({"ffmpeg_path": "/usr/bin/ffmpeg"}, []))

    error = download_video("http://example.com/watch?v=abc", str(tmp_path))

    assert "403" in error
    assert not part.exists(), "the partial must not be left behind to be played"
    assert survivor.exists(), "a failure must not touch the existing video"


# ---------------------------------------------------------------------------
# Sizing a download up front, so a progress bar can be weighted by real bytes
# ---------------------------------------------------------------------------

def _ydl_returning(info):
    ydl = MagicMock()
    ydl.extract_info.return_value = info
    return ydl


def test_build_download_plan_sums_a_merge():
    ydl = _ydl_returning({"requested_formats": [
        {"format_id": "399", "filesize": 29410017},
        {"format_id": "251", "filesize": 4167744},
    ]})
    assert build_download_plan(ydl, "u") == {"streams": 2, "total_bytes": 33577761}


def test_build_download_plan_handles_a_single_format():
    ydl = _ydl_returning({"format_id": "251", "filesize": 4167744})
    assert build_download_plan(ydl, "u") == {"streams": 1, "total_bytes": 4167744}


def test_build_download_plan_accepts_approximate_sizes():
    ydl = _ydl_returning({"requested_formats": [
        {"filesize_approx": 100}, {"filesize": 20},
    ]})
    assert build_download_plan(ydl, "u") == {"streams": 2, "total_bytes": 120}


def test_build_download_plan_gives_up_rather_than_guessing():
    """A partial total would make the bar lie, so return nothing instead."""
    ydl = _ydl_returning({"requested_formats": [
        {"filesize": 100}, {"format_id": "251"},   # size unknown
    ]})
    assert build_download_plan(ydl, "u") is None


def test_build_download_plan_never_raises():
    """A cosmetic progress bar must never be able to fail a download."""
    ydl = MagicMock()
    ydl.extract_info.side_effect = Exception("network went away")
    assert build_download_plan(ydl, "u") is None
    assert build_download_plan(_ydl_returning(None), "u") is None
    # Shapes that would blow up naive attribute access
    assert build_download_plan(_ydl_returning({"requested_formats": "nonsense"}), "u") is None
    assert build_download_plan(_ydl_returning({"requested_formats": [None]}), "u") is None
    assert build_download_plan(_ydl_returning({}), "u") is None
    assert build_download_plan(_ydl_returning({"filesize": 0}), "u") is None


def test_folder_snapshot_and_newly_downloaded_file(tmp_path):
    before = folder_snapshot(str(tmp_path))
    assert before == set()
    (tmp_path / "small.mp4").write_bytes(b"x" * 10)
    (tmp_path / "big.mp4").write_bytes(b"x" * 100)
    (tmp_path / "half.mp4.part").write_bytes(b"x" * 1000)

    # Largest non-partial wins; the .part is ignored even though it is biggest.
    assert newly_downloaded_file(str(tmp_path), before) == "big.mp4"
    assert newly_downloaded_file(str(tmp_path), folder_snapshot(str(tmp_path))) is None
    assert folder_snapshot(str(tmp_path / "nope")) == set()
