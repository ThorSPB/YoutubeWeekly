#!/usr/bin/env python3
"""Turn the `## Unreleased` section into `## v<version>` at release time.

Why this exists: `app/backend/changelog.py` deliberately ignores non-version
headings, so anything sitting under `## Unreleased` is invisible to users. Notes
are written under that heading as work lands, and nothing ever moved them - so
v1.6.1 shipped with every note still unreleased and showed its users no release
notes at all.

`release.yml` runs this in the `create-release` job *before* the tag is created,
and commits the result, so:
  * the tag - and therefore every built artifact - carries the stamped file, and
  * the notes leave `## Unreleased`, instead of being re-shipped verbatim under
    the next version too.

Deliberately does NOT re-add an empty `## Unreleased`: whoever writes the next
note adds the heading back. An empty section would only be a thing to explain.

Both language files are stamped identically, which is what keeps
`tests/test_changelog.py`'s structural-parity assertion true.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

UNRELEASED_RE = re.compile(r"^##\s+Unreleased\s*$", re.IGNORECASE | re.MULTILINE)
CHANGELOGS = ("CHANGELOG.md", "CHANGELOG_ro.md")


def section_body(content: str, start: int) -> str:
    """Text between the heading that starts at `start` and the next `## `."""
    rest = content[start:]
    nl = rest.find("\n")
    if nl == -1:
        return ""
    body = rest[nl + 1:]
    nxt = re.search(r"^##\s", body, re.MULTILINE)
    return body[:nxt.start()] if nxt else body


def stamp(content: str, version: str) -> tuple[str, str]:
    """Rename `## Unreleased` to `## v<version>`. Returns (new_content, note)."""
    heading = f"## v{version}"
    if re.search(rf"^{re.escape(heading)}\s*$", content, re.MULTILINE):
        return content, f"already has {heading}"

    match = UNRELEASED_RE.search(content)
    if not match:
        return content, "no Unreleased section"

    # An empty section must not become an empty version section - a release
    # with no user-visible change should list nothing, not a bare heading.
    if not section_body(content, match.start()).strip():
        return content, "Unreleased section is empty"

    return content[:match.start()] + heading + content[match.end():], f"stamped -> {heading}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("version", help="version being released, without a leading v")
    ap.add_argument("--root", default=".", help="repository root")
    ap.add_argument("--check", action="store_true",
                    help="report what would change, write nothing")
    args = ap.parse_args(argv)

    version = args.version.lstrip("vV")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        print(f"error: {args.version!r} is not a x.y.z version", file=sys.stderr)
        return 2

    changed = False
    for name in CHANGELOGS:
        path = os.path.join(args.root, name)
        if not os.path.exists(path):
            print(f"{name}: missing, skipped")
            continue
        with open(path, encoding="utf-8") as f:
            content = f.read()
        new, note = stamp(content, version)
        print(f"{name}: {note}")
        if new != content:
            changed = True
            if not args.check:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
    # Exit 1 with nothing to do, so the workflow can skip an empty commit.
    return 0 if changed else 1


if __name__ == "__main__":
    sys.exit(main())
