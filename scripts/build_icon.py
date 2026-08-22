#!/usr/bin/env python3
"""Regenerate app/frontend/assets/icon4.ico from the .icns master.

The shipped .ico used to contain **a single 32x32 image**, so Windows scaled it
up everywhere it wanted something bigger - shortcuts and toast notifications ask
for 256, Explorer for 48 - and the icon looked soft in every one of those
places. The .icns beside it holds real renders up to 1024, so the fix is simply
to emit the sizes Windows actually asks for.

Native .icns entries are preferred at each size; only 16, 24 and 48 have no
native entry and are resampled from the 1024 bitmap.

    venv/bin/python scripts/build_icon.py
"""

import os
import sys

from PIL import Image, IcnsImagePlugin

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "app", "frontend", "assets")
ICNS = os.path.join(ASSETS, "icon4.icns")
ICO = os.path.join(ASSETS, "icon4.ico")

# 16 tray/menus, 24+32 taskbar and title bar, 48 Explorer, 64/128 large icons,
# 256 shortcuts and notification toasts.
SIZES = [16, 24, 32, 48, 64, 128, 256]


def main():
    if not os.path.isfile(ICNS):
        sys.exit(f"missing master icon: {ICNS}")

    with open(ICNS, "rb") as f:
        icns = IcnsImagePlugin.IcnsFile(f)
        native = {}
        for key in icns.itersizes():
            img = icns.getimage(key).convert("RGBA")
            native.setdefault(img.size[0], img)
    if not native:
        sys.exit("no images found in the .icns")

    biggest = native[max(native)]
    frames, notes = [], []
    for size in SIZES:
        if size in native:
            frames.append(native[size])
            notes.append(f"{size}=native")
        else:
            frames.append(biggest.resize((size, size), Image.LANCZOS))
            notes.append(f"{size}=scaled")

    frames[-1].save(ICO, format="ICO", sizes=[(s, s) for s in SIZES])
    print("  ".join(notes))

    written = sorted(Image.open(ICO).ico.sizes())
    print(f"wrote {ICO}: {written}")
    assert written == sorted((s, s) for s in SIZES), written
    return 0


if __name__ == "__main__":
    sys.exit(main())
