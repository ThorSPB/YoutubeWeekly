#!/usr/bin/env python3
"""
Dry-run simulation of the auto-update flow.
Tests platform detection, asset matching, download (mocked), and bootstrap invocation.

Usage: python scripts/dry_run_update.py
"""
import os
import sys
import tempfile
import zipfile
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backend.updater import (
    check_for_updates,
    get_platform_asset_name,
    get_asset_download_url,
    download_update,
)
from app.backend.config import __version__, UPDATE_DIR


def run_dry_run():
    print("=" * 60)
    print("YoutubeWeekly Auto-Update Dry-Run")
    print("=" * 60)

    # Step 1: Version detection
    print(f"\n[1/6] Current version: {__version__}")

    # Step 2: Platform asset name
    print("\n[2/6] Platform detection...")
    asset_name = get_platform_asset_name("99.0.0")
    if not asset_name:
        print("  FAIL: Could not determine platform asset name")
        return 1
    print(f"  OK - Platform asset: {asset_name}")

    # Step 3: Check for updates (mocked)
    print("\n[3/6] Simulating update check...")
    mock_assets = [
        {"name": f"YoutubeWeekly-v99.0.0-win64.zip", "browser_download_url": "https://example.com/win.zip"},
        {"name": f"YoutubeWeekly-v99.0.0-macos-arm64.zip", "browser_download_url": "https://example.com/mac-arm.zip"},
        {"name": f"YoutubeWeekly-v99.0.0-macos-intel.zip", "browser_download_url": "https://example.com/mac-intel.zip"},
        {"name": f"YoutubeWeekly-v99.0.0-linux-x64.zip", "browser_download_url": "https://example.com/linux.zip"},
    ]
    mock_release = {
        "tag_name": "v99.0.0",
        "html_url": "https://github.com/ThorSPB/YoutubeWeekly/releases/tag/v99.0.0",
        "assets": mock_assets,
    }

    mock_response = MagicMock()
    mock_response.json.return_value = mock_release
    mock_response.raise_for_status = MagicMock()

    with patch("app.backend.updater.requests.get", return_value=mock_response):
        is_new, version, url, assets = check_for_updates()

    if not is_new:
        print("  FAIL: Expected update to be available")
        return 1
    print(f"  OK - Update available: v{version}")
    print(f"  OK - Release URL: {url}")
    print(f"  OK - Assets count: {len(assets)}")

    # Step 4: Asset URL matching
    print("\n[4/6] Finding platform-specific download URL...")
    asset_url = get_asset_download_url(assets, version)
    if not asset_url:
        print(f"  FAIL: No matching asset for {asset_name}")
        return 1
    print(f"  OK - Download URL: {asset_url}")

    # Step 5: Download simulation
    print("\n[5/6] Simulating download with progress...")
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = os.path.join(tmpdir, "test_update.zip")

        # Create a fake ZIP to "download"
        fake_zip_content = b"PK" + b"\x00" * 100  # Minimal ZIP-like content
        mock_dl_response = MagicMock()
        mock_dl_response.headers = {"content-length": str(len(fake_zip_content))}
        mock_dl_response.iter_content.return_value = [fake_zip_content]
        mock_dl_response.raise_for_status = MagicMock()

        progress_values = []
        with patch("app.backend.updater.requests.get", return_value=mock_dl_response):
            result = download_update(asset_url, dest, progress_callback=progress_values.append)

        if not os.path.exists(result):
            print("  FAIL: Download file not created")
            return 1
        print(f"  OK - Downloaded to: {result}")
        print(f"  OK - Progress callbacks: {len(progress_values)} (final: {progress_values[-1]:.0f}%)")

    # Step 6: Bootstrap validation
    print("\n[6/6] Validating bootstrap script...")
    bootstrap_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'backend', 'update_bootstrap.py')
    if not os.path.exists(bootstrap_path):
        print(f"  FAIL: Bootstrap script not found at {bootstrap_path}")
        return 1

    # Verify it can be imported (syntax check)
    import importlib.util
    spec = importlib.util.spec_from_file_location("update_bootstrap", bootstrap_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        # Don't actually execute main(), just verify it loads
        with patch("sys.argv", ["update_bootstrap"]):
            spec.loader.exec_module(mod)
        print("  OK - Bootstrap script loads without errors")
    except SystemExit:
        print("  OK - Bootstrap script loads (argparse exit expected without args)")
    except Exception as e:
        print(f"  FAIL: Bootstrap script error: {e}")
        return 1

    # Verify key functions exist
    for func_name in ["wait_for_process_exit", "backup_install", "restore_backup", "extract_zip", "main"]:
        if not hasattr(mod, func_name):
            print(f"  FAIL: Missing function: {func_name}")
            return 1
    print("  OK - All required functions present")

    print(f"\n  UPDATE_DIR would be: {UPDATE_DIR}")

    print("\n" + "=" * 60)
    print("DRY RUN PASSED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(run_dry_run())
