import pytest
import requests
from unittest.mock import patch, MagicMock
from app.backend.updater import (
    check_for_updates,
    get_platform_asset_name,
    get_asset_download_url,
    download_update,
)


# --- check_for_updates tests ---

@patch("app.backend.updater.requests.get")
def test_check_for_updates_new_version(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tag_name": "v99.0.0",
        "html_url": "https://github.com/ThorSPB/YoutubeWeekly/releases/tag/v99.0.0",
        "assets": [{"name": "YoutubeWeekly-v99.0.0-win64.zip", "browser_download_url": "https://example.com/win.zip"}],
    }
    mock_get.return_value = mock_response

    is_new, version, url, assets = check_for_updates()
    assert is_new is True
    assert version == "99.0.0"
    assert len(assets) == 1


@patch("app.backend.updater.requests.get")
def test_check_for_updates_up_to_date(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tag_name": "v0.0.1",
        "html_url": "https://example.com",
        "assets": [],
    }
    mock_get.return_value = mock_response

    is_new, version, url, assets = check_for_updates()
    assert is_new is False
    assert version is None
    assert assets == []


@patch("app.backend.updater.requests.get")
def test_check_for_updates_network_error(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

    is_new, version, url, assets = check_for_updates()
    assert is_new is False
    assert assets == []


@patch("app.backend.updater.requests.get")
def test_check_for_updates_malformed_response(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"no_tag": "missing"}
    mock_get.return_value = mock_response

    is_new, version, url, assets = check_for_updates()
    assert is_new is False


@patch("app.backend.updater.requests.get")
def test_check_for_updates_version_prefix_stripping(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tag_name": "V99.0.0",
        "html_url": "https://example.com",
        "assets": [],
    }
    mock_get.return_value = mock_response

    is_new, version, url, assets = check_for_updates()
    assert is_new is True
    assert version == "99.0.0"


# --- get_platform_asset_name tests ---

@patch("app.backend.updater.platform.system", return_value="Windows")
@patch("app.backend.updater.platform.machine", return_value="AMD64")
def test_platform_asset_name_windows(mock_machine, mock_system):
    assert get_platform_asset_name("1.1.0") == "YoutubeWeekly-v1.1.0-win64.zip"


@patch("app.backend.updater.platform.system", return_value="Darwin")
@patch("app.backend.updater.platform.machine", return_value="arm64")
def test_platform_asset_name_macos_arm(mock_machine, mock_system):
    assert get_platform_asset_name("1.1.0") == "YoutubeWeekly-v1.1.0-macos-arm64.zip"


@patch("app.backend.updater.platform.system", return_value="Darwin")
@patch("app.backend.updater.platform.machine", return_value="x86_64")
def test_platform_asset_name_macos_intel(mock_machine, mock_system):
    assert get_platform_asset_name("1.1.0") == "YoutubeWeekly-v1.1.0-macos-intel.zip"


@patch("app.backend.updater.platform.system", return_value="Linux")
@patch("app.backend.updater.platform.machine", return_value="x86_64")
def test_platform_asset_name_linux(mock_machine, mock_system):
    assert get_platform_asset_name("1.1.0") == "YoutubeWeekly-v1.1.0-linux-x64.zip"


# --- get_asset_download_url tests ---

def test_get_asset_download_url_found():
    assets = [
        {"name": "YoutubeWeekly-v1.1.0-win64.zip", "browser_download_url": "https://example.com/win.zip"},
        {"name": "YoutubeWeekly-v1.1.0-linux-x64.zip", "browser_download_url": "https://example.com/linux.zip"},
    ]
    with patch("app.backend.updater.get_platform_asset_name", return_value="YoutubeWeekly-v1.1.0-win64.zip"):
        url = get_asset_download_url(assets, "1.1.0")
    assert url == "https://example.com/win.zip"


def test_get_asset_download_url_not_found():
    assets = [
        {"name": "YoutubeWeekly-v1.1.0-linux-x64.zip", "browser_download_url": "https://example.com/linux.zip"},
    ]
    with patch("app.backend.updater.get_platform_asset_name", return_value="YoutubeWeekly-v1.1.0-win64.zip"):
        url = get_asset_download_url(assets, "1.1.0")
    assert url is None


# --- download_update tests ---

@patch("app.backend.updater.requests.get")
def test_download_update_success(mock_get, tmp_path):
    mock_response = MagicMock()
    mock_response.headers = {"content-length": "100"}
    mock_response.iter_content.return_value = [b"x" * 50, b"x" * 50]
    mock_get.return_value = mock_response

    progress_values = []
    dest = str(tmp_path / "update.zip")
    result = download_update("https://example.com/update.zip", dest, progress_callback=progress_values.append)

    assert result == dest
    assert len(progress_values) >= 2
    assert progress_values[-1] == 100


@patch("app.backend.updater.requests.get")
def test_download_update_failure(mock_get, tmp_path):
    mock_get.side_effect = requests.exceptions.RequestException("Network error")

    dest = str(tmp_path / "update.zip")
    with pytest.raises(requests.exceptions.RequestException):
        download_update("https://example.com/update.zip", dest)
