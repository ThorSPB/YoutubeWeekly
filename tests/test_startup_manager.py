import pytest
from unittest.mock import patch, MagicMock
from app.backend.linux_startup import (
    add_to_startup as linux_add,
    remove_from_startup as linux_remove,
    is_in_startup as linux_is_in,
    get_desktop_file_path,
)


# --- linux_startup tests ---

def test_get_desktop_file_path():
    path = get_desktop_file_path("TestApp")
    assert path.endswith(".config/autostart/TestApp.desktop")


def test_linux_add_to_startup(tmp_path, monkeypatch):
    desktop_path = tmp_path / "TestApp.desktop"
    monkeypatch.setattr("app.backend.linux_startup.get_desktop_file_path", lambda name: str(desktop_path))

    result = linux_add("TestApp", "/usr/bin/testapp")
    assert result is True
    assert desktop_path.exists()
    content = desktop_path.read_text()
    assert "/usr/bin/testapp --start-minimized" in content
    assert "Name=TestApp" in content


def test_linux_add_to_startup_no_executable():
    result = linux_add("TestApp", None)
    assert result is False


def test_linux_remove_from_startup(tmp_path, monkeypatch):
    desktop_path = tmp_path / "TestApp.desktop"
    desktop_path.write_text("[Desktop Entry]")
    monkeypatch.setattr("app.backend.linux_startup.get_desktop_file_path", lambda name: str(desktop_path))

    result = linux_remove("TestApp")
    assert result is True
    assert not desktop_path.exists()


def test_linux_remove_from_startup_not_exists(tmp_path, monkeypatch):
    desktop_path = tmp_path / "TestApp.desktop"
    monkeypatch.setattr("app.backend.linux_startup.get_desktop_file_path", lambda name: str(desktop_path))

    result = linux_remove("TestApp")
    assert result is True  # Should succeed even if file doesn't exist


def test_linux_is_in_startup_true(tmp_path, monkeypatch):
    desktop_path = tmp_path / "TestApp.desktop"
    desktop_path.write_text("[Desktop Entry]")
    monkeypatch.setattr("app.backend.linux_startup.get_desktop_file_path", lambda name: str(desktop_path))

    assert linux_is_in("TestApp") is True


def test_linux_is_in_startup_false(tmp_path, monkeypatch):
    desktop_path = tmp_path / "TestApp.desktop"
    monkeypatch.setattr("app.backend.linux_startup.get_desktop_file_path", lambda name: str(desktop_path))

    assert linux_is_in("TestApp") is False


# --- startup_manager dispatch tests ---

@patch("app.backend.startup_manager.sys")
def test_get_executable_path_frozen(mock_sys):
    mock_sys.frozen = True
    mock_sys.executable = "/opt/YoutubeWeekly/YoutubeWeekly"
    from app.backend.startup_manager import get_executable_path
    path = get_executable_path()
    assert path == "/opt/YoutubeWeekly/YoutubeWeekly"
