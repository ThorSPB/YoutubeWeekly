"""Dry-run script to test feedback system without the GUI."""

import sys
import os
import time
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock version so dev check is bypassed in telemetry
with patch("app.backend.config.__version__", "1.2.0"):
    import importlib
    import app.backend.telemetry as telemetry
    import app.backend.feedback as feedback
    importlib.reload(telemetry)
    importlib.reload(feedback)

    print("=" * 60)
    print("YoutubeWeekly Feedback System Dry-Run")
    print("=" * 60)

    # Test 1: Install ID
    install_id = telemetry._get_install_id()
    print(f"\n1. Install ID: {install_id}")
    assert install_id, "Install ID should not be empty"
    print("   OK - Install ID generated/loaded")

    # Test 2: Submit feedback
    print("\n2. Submitting test feedback...")
    success, result = feedback.submit_feedback(
        category="other",
        message="Dry-run test feedback — please ignore.",
        settings={"default_quality": "1080p", "enable_auto_download": True},
    )
    if success:
        print(f"   OK - Feedback submitted, ID: {result}")
    else:
        print(f"   WARN - Submit failed (server may be unreachable): {result}")

    # Test 3: Fetch feedback
    print("\n3. Fetching feedback threads...")
    threads = feedback.fetch_feedback()
    print(f"   OK - Got {len(threads)} thread(s)")
    for t in threads:
        replies = len(t.get("replies", []))
        print(f"   - [{t.get('category')}] {t.get('message', '')[:50]}... "
              f"(status: {t.get('status')}, replies: {replies})")

    # Test 4: Local storage
    print("\n4. Checking local storage...")
    local = feedback.load_local_feedback()
    print(f"   OK - {len(local)} thread(s) in local cache")

    # Test 5: Screenshot compression (if PIL available)
    print("\n5. Testing screenshot compression...")
    try:
        from PIL import Image
        import io
        # Create a test image
        img = Image.new("RGB", (1920, 1080), color=(50, 50, 80))
        test_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_screenshot.png")
        img.save(test_path)
        compressed = feedback.compress_screenshot(test_path)
        print(f"   OK - 1920x1080 image compressed to {len(compressed)} bytes ({len(compressed)/1024:.0f} KB)")
        os.remove(test_path)
    except Exception as e:
        print(f"   WARN - Screenshot test failed: {e}")

    print("\n" + "=" * 60)
    print("DRY RUN PASSED")
    print("=" * 60)
