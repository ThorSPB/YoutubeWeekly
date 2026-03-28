import os
import platform
import requests
import logging
from app.backend.config import __version__

GITHUB_REPO_URL = "https://api.github.com/repos/ThorSPB/YoutubeWeekly/releases/latest"


def get_platform_asset_name(version):
    """Return the expected ZIP filename for this platform."""
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows":
        return f"YoutubeWeekly-v{version}-win64.zip"
    elif system == "Darwin":
        if "arm" in machine:
            return f"YoutubeWeekly-v{version}-macos-arm64.zip"
        else:
            return f"YoutubeWeekly-v{version}-macos-intel.zip"
    elif system == "Linux":
        return f"YoutubeWeekly-v{version}-linux-x64.zip"
    return None


def get_asset_download_url(assets, version):
    """Find the direct download URL for this platform's ZIP from release assets."""
    expected_name = get_platform_asset_name(version)
    if not expected_name:
        return None
    for asset in assets:
        if asset.get("name") == expected_name:
            return asset.get("browser_download_url")
    return None


def check_for_updates():
    """Check GitHub for a newer release.

    Returns: (is_new, latest_version, release_page_url, assets)
    - assets is the list of release asset dicts (empty list on error)
    """
    try:
        response = requests.get(GITHUB_REPO_URL, timeout=5)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release["tag_name"].lstrip('vV')
        download_url = latest_release["html_url"]
        assets = latest_release.get("assets", [])

        current_version_parts = list(map(int, __version__.split('.')))
        latest_version_parts = list(map(int, latest_version.split('.')))

        if latest_version_parts > current_version_parts:
            return True, latest_version, download_url, assets
        else:
            return False, None, None, []
    except requests.exceptions.RequestException as e:
        logging.error(f"Update check failed: {e}")
        return False, None, None, []
    except (KeyError, ValueError) as e:
        logging.error(f"Unexpected response format from GitHub API: {e}")
        return False, None, None, []


def download_update(asset_url, dest_path, progress_callback=None):
    """Download an update ZIP with progress reporting.

    Args:
        asset_url: Direct download URL for the ZIP asset
        dest_path: Full path to save the ZIP file
        progress_callback: Optional callable(percent: float) called during download

    Returns: dest_path on success

    Raises: Exception on failure
    """
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    response = requests.get(asset_url, stream=True, timeout=30)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0

    with open(dest_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if progress_callback and total_size > 0:
                progress_callback((downloaded / total_size) * 100)

    if progress_callback:
        progress_callback(100)

    return dest_path
