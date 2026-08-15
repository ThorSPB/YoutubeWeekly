import sys
from unittest.mock import MagicMock

import pytest

# Mock pystray before any test imports gui.py, to avoid Xlib dependency in headless environments
if 'pystray' not in sys.modules:
    sys.modules['pystray'] = MagicMock()
    sys.modules['pystray._base'] = MagicMock()


@pytest.fixture(autouse=True)
def isolate_overrides(tmp_path, monkeypatch):
    """Keep override lookups off the network and out of the real config dir.

    The override manifest is consulted from run_automatic_checks and the GUI's
    download worker, so without this every test touching those paths would make
    a real HTTP request and scribble on the user's cache. Tests that exercise
    the manifest patch `app.backend.overrides.requests` themselves.

    Rebinding the name inside the overrides module leaves `requests` untouched
    for telemetry, feedback and the updater.
    """
    import app.backend.overrides as overrides

    blocked = MagicMock()
    blocked.get.side_effect = AssertionError(
        "unexpected network call: patch app.backend.overrides.requests in this test"
    )
    monkeypatch.setattr(overrides, "requests", blocked)

    # Telemetry too: test_auto_downloader drives run_automatic_checks without
    # stubbing send_telemetry_ping, so with a real version stamped in (as the
    # release workflow does) the suite posts live pings to the server.
    import app.backend.telemetry as telemetry
    monkeypatch.setattr(telemetry, "requests", blocked)
    monkeypatch.setattr(overrides, "OVERRIDES_CACHE_FILE", str(tmp_path / "overrides.json"))
    monkeypatch.setattr(overrides, "OVERRIDE_STATE_FILE", str(tmp_path / "override_state.json"))
    monkeypatch.setattr(overrides, "_ping_version", None)
    monkeypatch.setattr(overrides, "_current_version", None)
