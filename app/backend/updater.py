import requests
import json
import logging
from app.backend.config import __version__

GITHUB_REPO_URL = "https://api.github.com/repos/ThorSPB/YoutubeWeekly/releases/latest"

def check_for_updates():
    try:
        response = requests.get(GITHUB_REPO_URL, timeout=5)
        response.raise_for_status() # Raise an exception for HTTP errors
        latest_release = response.json()
        latest_version = latest_release["tag_name"].lstrip('vV') # Remove 'v' or 'V' prefix
        download_url = latest_release["html_url"]

        current_version_parts = list(map(int, __version__.split('.')))
        latest_version_parts = list(map(int, latest_version.split('.')))

        if latest_version_parts > current_version_parts:
            return True, latest_version, download_url
        else:
            return False, None, None
    except requests.exceptions.RequestException as e:
        logging.error(f"Update check failed: {e}")
        return False, None, None
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse update response: {e}")
        return False, None, None
    except KeyError as e:
        logging.error(f"Unexpected response format from GitHub API: {e}")
        return False, None, None
