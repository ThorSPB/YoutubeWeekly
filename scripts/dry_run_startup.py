#!/usr/bin/env python3
"""
Read-only check of startup registration status.
Does NOT modify any startup settings.

Usage: python scripts/dry_run_startup.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.backend.startup_manager import is_in_startup, get_executable_path


def run_dry_run():
    print("=" * 60)
    print("YoutubeWeekly Startup Registration Check (read-only)")
    print("=" * 60)

    print(f"\n  Platform: {sys.platform}")

    # Check current status
    print("\n[1/2] Checking startup registration...")
    registered = is_in_startup()
    print(f"  Registered: {registered}")

    if sys.platform.startswith("linux"):
        from app.backend.linux_startup import get_desktop_file_path
        desktop_path = get_desktop_file_path("YoutubeWeekly")
        print(f"  Desktop file: {desktop_path}")
        if os.path.exists(desktop_path):
            with open(desktop_path, "r") as f:
                content = f.read()
            print(f"  Content preview:")
            for line in content.strip().split("\n")[:5]:
                print(f"    {line}")
        else:
            print("  File does not exist (not registered)")
    elif sys.platform == "win32":
        print("  (Windows Registry check — read-only)")
    elif sys.platform == "darwin":
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.YoutubeWeekly.plist")
        print(f"  Plist path: {plist_path}")
        print(f"  Exists: {os.path.exists(plist_path)}")

    # Check executable path
    print("\n[2/2] Checking executable path...")
    exe_path = get_executable_path()
    print(f"  Executable: {exe_path}")

    is_frozen = getattr(sys, 'frozen', False)
    print(f"  Frozen (PyInstaller): {is_frozen}")

    print("\n" + "=" * 60)
    print("CHECK COMPLETE (no changes made)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(run_dry_run())
