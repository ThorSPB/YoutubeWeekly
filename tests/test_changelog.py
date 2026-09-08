"""Release notes: which sections a user is owed, and reading them all.

The rule that matters: someone updating 1.4.0 -> 1.5.1 skipped 1.5.0 entirely,
so showing them only the newest section hides a whole release.
"""

import os
import sys

import pytest

from app.backend import changelog as cl

SAMPLE = """# Changelog

## Unreleased
- not shipped yet

## v1.5.1
- fixed downloads
- fixed partials

## v1.5.0
- overrides

## v1.4.0
- romanian

## v1.0.4
- first release
"""


def _versions(markdown):
    return [
        line[3:].strip()
        for line in markdown.split("\n")
        if line.startswith("## ")
    ]


# --- version parsing ------------------------------------------------------

@pytest.mark.parametrize("text, expected", [
    ("1.5.1", (1, 5, 1)),
    ("v1.5.1", (1, 5, 1)),
    (" v1.5.1 ", (1, 5, 1)),
    ("1.4", (1, 4)),
    ("Unreleased", None),
    ("", None),
    (None, None),
    ("v1.5.1-beta", None),
])
def test_parse_version(text, expected):
    assert cl.parse_version(text) == expected


def test_version_ordering_is_numeric_not_lexical():
    """"1.10.0" must sort above "1.9.0", which string compare gets wrong."""
    assert cl.parse_version("1.10.0") > cl.parse_version("1.9.0")


# --- splitting ------------------------------------------------------------

def test_split_sections_keeps_order_and_flags_non_versions():
    sections = cl.split_sections(SAMPLE)
    assert [s["version"] for s in sections] == [None, "1.5.1", "1.5.0", "1.4.0", "1.0.4"]
    assert sections[0]["key"] is None, "Unreleased has no version key"
    assert sections[1]["key"] == (1, 5, 1)
    # Content travels with its heading
    assert "- fixed downloads" in sections[1]["lines"]


def test_split_sections_on_empty_input():
    assert cl.split_sections("") == []
    assert cl.split_sections(None) == []


# --- what's new for this user --------------------------------------------

def test_notes_since_spans_every_skipped_release():
    """The bug this fixes: 1.4.0 -> 1.5.1 used to show only the 1.5.1 notes."""
    out = cl.notes_since(SAMPLE, "1.4.0", "1.5.1")
    assert _versions(out) == ["v1.5.1", "v1.5.0"]
    assert "romanian" not in out, "the version they already had is excluded"
    assert "not shipped yet" not in out, "Unreleased is not a release"


def test_notes_since_is_inclusive_of_current_exclusive_of_previous():
    out = cl.notes_since(SAMPLE, "1.5.0", "1.5.1")
    assert _versions(out) == ["v1.5.1"]


def test_notes_since_covers_a_long_jump():
    out = cl.notes_since(SAMPLE, "1.0.4", "1.5.1")
    assert _versions(out) == ["v1.5.1", "v1.5.0", "v1.4.0"]


def test_notes_since_without_a_known_previous_shows_only_the_current():
    """All we can honestly claim is what this release changed."""
    for previous in (None, "", "dev", "garbage"):
        assert _versions(cl.notes_since(SAMPLE, previous, "1.5.1")) == ["v1.5.1"]


def test_notes_since_is_empty_when_nothing_is_new():
    assert cl.notes_since(SAMPLE, "1.5.1", "1.5.1") == ""


def test_notes_since_ignores_a_rollback():
    """Running older than last time: there is nothing new to announce."""
    assert cl.notes_since(SAMPLE, "1.5.1", "1.4.0") == ""


def test_notes_since_handles_a_missing_section_for_the_current_version():
    out = cl.notes_since(SAMPLE, "1.4.0", "1.9.9")
    assert _versions(out) == ["v1.5.1", "v1.5.0"]


def test_notes_since_needs_a_current_version():
    assert cl.notes_since(SAMPLE, "1.4.0", "dev") == ""


# --- the full reader ------------------------------------------------------

def test_all_notes_covers_every_release_but_not_unreleased():
    out = cl.all_notes(SAMPLE)
    assert _versions(out) == ["v1.5.1", "v1.5.0", "v1.4.0", "v1.0.4"]
    assert "not shipped yet" not in out


def test_all_notes_can_include_unreleased():
    assert "not shipped yet" in cl.all_notes(SAMPLE, include_unreleased=True)


# --- locating the file ----------------------------------------------------

def test_candidates_prefer_the_localized_file():
    paths = cl.changelog_candidates("ro")
    ro = [p for p in paths if "CHANGELOG_ro.md" in p]
    en = [p for p in paths if p.endswith("CHANGELOG.md")]
    assert ro, "a localized changelog must be looked for"
    assert paths.index(ro[0]) < paths.index(en[0]), "localized first, English as fallback"


def test_candidates_for_english_do_not_look_for_a_suffix():
    assert not any("CHANGELOG_en.md" in p for p in cl.changelog_candidates("en"))


def test_load_changelog_reads_a_real_file(tmp_path, monkeypatch):
    monkeypatch.setattr(cl, "get_base_path", lambda: str(tmp_path))
    (tmp_path / "CHANGELOG.md").write_text(SAMPLE, encoding="utf-8")
    assert "fixed downloads" in cl.load_changelog("en")


def test_load_changelog_picks_the_language_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(cl, "get_base_path", lambda: str(tmp_path))
    (tmp_path / "CHANGELOG.md").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "CHANGELOG_ro.md").write_text("## v1.5.1\n- reparat\n", encoding="utf-8")
    assert "reparat" in cl.load_changelog("ro")
    assert "fixed downloads" in cl.load_changelog("en")


def test_load_changelog_falls_back_to_english(tmp_path, monkeypatch):
    """A language with no translation still gets notes rather than nothing."""
    monkeypatch.setattr(cl, "get_base_path", lambda: str(tmp_path))
    (tmp_path / "CHANGELOG.md").write_text(SAMPLE, encoding="utf-8")
    assert "fixed downloads" in cl.load_changelog("de")


def test_load_changelog_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(cl, "get_base_path", lambda: str(tmp_path / "empty"))
    assert cl.load_changelog("en") is None


# --- the shipped files ----------------------------------------------------

def test_shipped_changelogs_agree_on_structure():
    """EN and RO must describe the same releases, or a Romanian user silently
    gets a different history."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    en = cl.split_sections(open(os.path.join(root, "CHANGELOG.md"), encoding="utf-8").read())
    ro = cl.split_sections(open(os.path.join(root, "CHANGELOG_ro.md"), encoding="utf-8").read())

    assert [s["version"] for s in en] == [s["version"] for s in ro]

    def bullets(section):
        return len([l for l in section["lines"] if l.strip().startswith("- ")])

    for a, b in zip(en, ro):
        assert bullets(a) == bullets(b), f"bullet count differs for {a['version']}"


# --- stamping a release ---------------------------------------------------
#
# Notes are written under `## Unreleased`, and this module deliberately ignores
# non-version headings - so a release that never stamps them shows its users no
# notes at all. That is what v1.6.1 did. `scripts/stamp_changelog.py` runs in
# release.yml before the tag is cut.

import subprocess

STAMP = os.path.join(os.path.dirname(__file__), "..", "scripts", "stamp_changelog.py")


def _write_pair(tmp_path, en, ro):
    (tmp_path / "CHANGELOG.md").write_text(en, encoding="utf-8")
    (tmp_path / "CHANGELOG_ro.md").write_text(ro, encoding="utf-8")


def _run(tmp_path, *args):
    return subprocess.run([sys.executable, STAMP, *args, "--root", str(tmp_path)],
                          capture_output=True, text=True)


def test_stamp_renames_unreleased_to_the_version(tmp_path):
    body = "# Changelog\n\n## Unreleased\n- did a thing\n\n## v1.0.0\n- first\n"
    _write_pair(tmp_path, body, body)
    r = _run(tmp_path, "1.6.2")
    assert r.returncode == 0, r.stderr
    for name in ("CHANGELOG.md", "CHANGELOG_ro.md"):
        out = (tmp_path / name).read_text(encoding="utf-8")
        assert "## v1.6.2\n- did a thing" in out
        assert "Unreleased" not in out
        # Everything else is untouched.
        assert "## v1.0.0\n- first" in out


def test_stamp_is_idempotent(tmp_path):
    """A re-run must not stamp a second time - it would swallow the next
    version's notes into an already-released section."""
    body = "# Changelog\n\n## Unreleased\n- new\n\n## v1.6.2\n- old\n"
    _write_pair(tmp_path, body, body)
    r = _run(tmp_path, "1.6.2")
    assert r.returncode == 1, "nothing should have changed"
    assert "already has" in r.stdout
    assert (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8") == body


def test_stamp_leaves_an_empty_unreleased_alone(tmp_path):
    """A release with no user-visible change must not get a bare heading."""
    body = "# Changelog\n\n## Unreleased\n\n## v1.0.0\n- first\n"
    _write_pair(tmp_path, body, body)
    r = _run(tmp_path, "1.6.2")
    assert r.returncode == 1
    assert "empty" in r.stdout
    assert (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8") == body


def test_stamp_rejects_a_bad_version(tmp_path):
    _write_pair(tmp_path, "## Unreleased\n- x\n", "## Unreleased\n- x\n")
    assert _run(tmp_path, "not-a-version").returncode == 2


def test_stamped_notes_become_visible_to_users(tmp_path):
    """The whole point: before stamping, notes_since() returns nothing."""
    body = "# Changelog\n\n## Unreleased\n- the fix\n\n## v1.6.1\n- older\n"
    _write_pair(tmp_path, body, body)
    before = cl.notes_since(body, "1.6.1", "1.6.2")
    assert "the fix" not in (before or ""), "unreleased notes must be invisible"
    _run(tmp_path, "1.6.2")
    after = cl.notes_since((tmp_path / "CHANGELOG.md").read_text(encoding="utf-8"),
                           "1.6.1", "1.6.2")
    assert "the fix" in after
