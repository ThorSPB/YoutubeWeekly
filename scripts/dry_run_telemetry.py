"""Dry-run script to test telemetry ping without downloading anything."""

import sys
import os
import time
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock version so dev check is bypassed
with patch("app.backend.config.__version__", "1.1.3"):
    # Re-import after patching
    import importlib
    import app.backend.telemetry as telemetry
    importlib.reload(telemetry)

    print("Sending test telemetry ping...")
    telemetry.send_telemetry_ping(
        settings={
            "send_telemetry": True,
            "keep_old_videos": False,
            "default_quality": "1080p",
            "enable_auto_download": True,
            "enable_notifications": True,
            "start_with_system": True,
            "check_for_updates": True,
            "auto_install_updates": False,
            "use_mpv": False,
            "mpv_fullscreen": True,
        },
        videos_downloaded=1,
        session_type="manual",
    )

    # Wait for the daemon thread to finish
    time.sleep(5)
    print("Done! Check the telemetry dashboard or DB for the ping.")
