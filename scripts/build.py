#!/usr/bin/env python3
"""
Build script for YoutubeWeekly.

Usage:
  python scripts/build.py                    # Build with current version
  python scripts/build.py --bump patch       # Bump patch version and build
  python scripts/build.py --bump minor       # Bump minor version and build
  python scripts/build.py --skip-tests       # Skip tests before building
"""
import argparse
import os
import re
import subprocess
import sys
import shutil
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'app', 'backend', 'config.py')
SPEC_FILE = os.path.join(PROJECT_ROOT, 'youtubeweekly.spec')
DIST_DIR = os.path.join(PROJECT_ROOT, 'dist')


def get_version():
    with open(CONFIG_FILE, 'r') as f:
        content = f.read()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not match:
        print("ERROR: Could not find __version__ in config.py")
        sys.exit(1)
    return match.group(1)


def set_version(new_version):
    with open(CONFIG_FILE, 'r') as f:
        content = f.read()
    content = re.sub(
        r'__version__\s*=\s*"[^"]+"',
        f'__version__ = "{new_version}"',
        content,
    )
    with open(CONFIG_FILE, 'w') as f:
        f.write(content)


def bump_version(current, part):
    parts = list(map(int, current.split('.')))
    while len(parts) < 3:
        parts.append(0)

    if part == 'major':
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif part == 'minor':
        parts[1] += 1
        parts[2] = 0
    elif part == 'patch':
        parts[2] += 1
    else:
        print(f"ERROR: Unknown bump type '{part}'. Use major, minor, or patch.")
        sys.exit(1)

    return '.'.join(map(str, parts))


def run_tests():
    print("\n--- Running tests ---")
    result = subprocess.run(
        [sys.executable, '-m', 'pytest',
         '--ignore=tests/test_gui.py', '--ignore=tests/test_player_logic.py',
         '--tb=short', '-q'],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        print("\nERROR: Tests failed. Fix them before building.")
        sys.exit(1)
    print("Tests passed.\n")


def build():
    print("--- Building with PyInstaller ---")
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', SPEC_FILE, '--noconfirm'],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        print("\nERROR: PyInstaller build failed.")
        sys.exit(1)
    print("Build complete.\n")


def get_git_commit():
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, cwd=PROJECT_ROOT,
        )
        return result.stdout.strip()
    except Exception:
        return 'unknown'


def main():
    parser = argparse.ArgumentParser(description='Build YoutubeWeekly')
    parser.add_argument('--bump', choices=['major', 'minor', 'patch'],
                        help='Bump version before building')
    parser.add_argument('--skip-tests', action='store_true',
                        help='Skip running tests before build')
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)

    version = get_version()

    if args.bump:
        new_version = bump_version(version, args.bump)
        print(f"Bumping version: {version} -> {new_version}")
        set_version(new_version)
        version = new_version

    print(f"Building YoutubeWeekly v{version}")
    print(f"  Commit: {get_git_commit()}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not args.skip_tests:
        run_tests()

    build()

    # Print build info
    output_dir = os.path.join(DIST_DIR, 'YoutubeWeekly')
    if os.path.exists(output_dir):
        print(f"\nBuild output: {output_dir}")
        total_size = sum(
            os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, _, filenames in os.walk(output_dir)
            for filename in filenames
        )
        print(f"Total size: {total_size / (1024 * 1024):.1f} MB")
    else:
        print(f"\nWARNING: Expected output not found at {output_dir}")

    print(f"\nBuild metadata:")
    print(f"  Version: {version}")
    print(f"  Commit: {get_git_commit()}")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
