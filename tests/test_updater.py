import pytest
from unittest.mock import patch, MagicMock
from app.backend.updater import check_for_updates


@patch("app.backend.updater.requests.get")
def test_check_for_updates_new_version(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tag_name": "v2.0.0",
        "html_url": "https://github.com/ThorSPB/YoutubeWeekly/releases/tag/v2.0.0"
    }
    mock_get.return_value = mock_response

    is_new, version, url = check_for_updates()
    assert is_new is True
    assert version == "2.0.0"
    assert url == "https://github.com/ThorSPB/YoutubeWeekly/releases/tag/v2.0.0"


@patch("app.backend.updater.requests.get")
def test_check_for_updates_up_to_date(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tag_name": "v0.0.1",
        "html_url": "https://github.com/ThorSPB/YoutubeWeekly/releases/tag/v0.0.1"
    }
    mock_get.return_value = mock_response

    is_new, version, url = check_for_updates()
    assert is_new is False
    assert version is None
    assert url is None


@patch("app.backend.updater.requests.get")
def test_check_for_updates_network_error(mock_get):
    import requests
    mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

    is_new, version, url = check_for_updates()
    assert is_new is False
    assert version is None
    assert url is None


@patch("app.backend.updater.requests.get")
def test_check_for_updates_malformed_response(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"no_tag": "missing"}
    mock_get.return_value = mock_response

    is_new, version, url = check_for_updates()
    assert is_new is False


@patch("app.backend.updater.requests.get")
def test_check_for_updates_version_prefix_stripping(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "tag_name": "V99.0.0",
        "html_url": "https://example.com"
    }
    mock_get.return_value = mock_response

    is_new, version, url = check_for_updates()
    assert is_new is True
    assert version == "99.0.0"
