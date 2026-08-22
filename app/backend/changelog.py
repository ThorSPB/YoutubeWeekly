"""Reading the release notes and working out which of them are new to a user.

Kept in the backend so the parsing is testable without a display, and shared by
the post-update dialog and the Settings reader rather than duplicated.

The notes a user has not seen are *every* version between the one they were
running and the one they are running now - not just the newest. Someone
updating 1.4.0 -> 1.5.1 skipped 1.5.0 entirely, and showing them only the
1.5.1 section hides a whole release.
"""

import os
import re
import sys

from app.backend.config import get_base_path

# "## v1.5.1", tolerating a missing "v" and trailing text like "(2026-08-22)".
_HEADING_RE = re.compile(r"^##\s+v?(\d+(?:\.\d+)*)\b")


def parse_version(text):
    """`"1.5.1"` or `"v1.5.1"` -> `(1, 5, 1)`. None if it isn't a version."""
    if not text:
        return None
    m = re.match(r"^v?(\d+(?:\.\d+)*)$", str(text).strip())
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def changelog_candidates(language="en"):
    """Where the changelog might live, best bet first.

    The build drops CHANGELOG.md beside the executable and the spec bundles
    docs/ into _internal, so both are checked - plus the source tree for a dev
    run. A localized file wins when the UI is not in English.
    """
    names = []
    if language and language != "en":
        names.append(f"CHANGELOG_{language}.md")
    names.append("CHANGELOG.md")

    roots = [get_base_path(), os.path.join(get_base_path(), "_internal")]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(meipass)

    paths = []
    for name in names:
        for root in roots:
            paths.append(os.path.join(root, name))
            paths.append(os.path.join(root, "docs", name))
    return paths


def load_changelog(language="en"):
    """Contents of the best available changelog, or None."""
    for path in changelog_candidates(language):
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        except OSError:
            continue
    return None


def split_sections(content):
    """Split a changelog into its ``## `` sections, in file order.

    Returns dicts of ``{"version": str|None, "key": tuple|None, "lines": [...]}``.
    A section whose heading isn't a version - "## Unreleased" - gets a None key
    so it can be excluded from "what's new for you" while still being readable
    in full.
    """
    sections = []
    current = None
    for line in (content or "").split("\n"):
        if line.startswith("## "):
            m = _HEADING_RE.match(line)
            version = m.group(1) if m else None
            current = {
                "version": version,
                "key": parse_version(version) if version else None,
                "lines": [line],
            }
            sections.append(current)
        elif current is not None:
            current["lines"].append(line)
    return sections


def notes_since(content, previous_version, current_version):
    """The sections a user moving `previous_version` -> `current_version` missed.

    Inclusive of the current version, exclusive of the one they had. Returns
    markdown, or "" if there is nothing to show. With no usable previous
    version we can only honestly show the current release's own section.
    """
    sections = split_sections(content)
    if not sections:
        return ""

    current = parse_version(current_version)
    previous = parse_version(previous_version)

    if current is None:
        return ""

    if previous is None:
        chosen = [s for s in sections if s["key"] == current]
    else:
        chosen = [
            s for s in sections
            if s["key"] is not None and previous < s["key"] <= current
        ]

    # Newest first, matching how the file itself reads.
    chosen.sort(key=lambda s: s["key"], reverse=True)
    return "\n".join("\n".join(s["lines"]).rstrip() for s in chosen).strip()


def all_notes(content, include_unreleased=False):
    """The whole changelog as markdown, optionally minus an Unreleased section.

    Users get released versions only; an Unreleased heading describes something
    they are not running.
    """
    sections = split_sections(content)
    if not include_unreleased:
        sections = [s for s in sections if s["key"] is not None]
    return "\n".join("\n".join(s["lines"]).rstrip() for s in sections).strip()
