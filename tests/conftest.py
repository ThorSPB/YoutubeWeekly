import sys
from unittest.mock import MagicMock

# Mock pystray before any test imports gui.py, to avoid Xlib dependency in headless environments
if 'pystray' not in sys.modules:
    sys.modules['pystray'] = MagicMock()
    sys.modules['pystray._base'] = MagicMock()
