#!/usr/bin/env python3
"""
Update bootstrap — runs after the main app exits to replace files with a new version.

This script is compiled to a standalone PyInstaller exe and ships alongside
YoutubeWeekly.exe. It uses only stdlib (no external deps).

Usage:
    update_bootstrap --zip <path> --target <install_dir> --exe <exe_name> --pid <pid>
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
import zipfile


def wait_for_process_exit(pid, timeout=30):
    """Wait for a process to exit, polling every 0.5s."""
    start = time.time()

    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        SYNCHRONIZE = 0x100000
        ERROR_INVALID_PARAMETER = 87

    while time.time() - start < timeout:
        try:
            if sys.platform == "win32":
                handle = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
                if handle:
                    kernel32.CloseHandle(handle)
                else:
                    if ctypes.get_last_error() == ERROR_INVALID_PARAMETER:
                        return True
            else:
                os.kill(pid, 0)  # Signal 0 checks if process exists
        except (OSError, ProcessLookupError):
            return True  # Process has exited
        time.sleep(0.5)
    return False  # Timeout


def backup_install(target_dir, exe_name):
    """Rename existing files to .bak for rollback.

    Preserves user data directories (data/) that may contain downloaded videos.
    """
    # Directories that contain user data and should not be touched during update
    PRESERVE_DIRS = {"data", "logs"}

    backed_up = []
    for item in os.listdir(target_dir):
        # Don't back up the bootstrap itself, existing backups, or user data
        if item.startswith("update_bootstrap") or item.endswith(".bak"):
            continue
        if item in PRESERVE_DIRS:
            continue
        src = os.path.join(target_dir, item)
        dst = src + ".bak"
        try:
            os.rename(src, dst)
            backed_up.append((dst, src))
        except OSError as e:
            # If we can't rename something, restore what we already backed up
            restore_backup(backed_up)
            raise RuntimeError(f"Failed to backup {item}: {e}")
    return backed_up


def restore_backup(backed_up):
    """Restore .bak files to their original names."""
    for bak_path, orig_path in backed_up:
        try:
            if os.path.exists(orig_path):
                if os.path.isdir(orig_path):
                    shutil.rmtree(orig_path)
                else:
                    os.remove(orig_path)
            os.rename(bak_path, orig_path)
        except OSError as e:
            print(f"CRITICAL: Failed to restore backup {bak_path} -> {orig_path}: {e}", file=sys.stderr)


def cleanup_backup(backed_up):
    """Delete .bak files after successful update."""
    for bak_path, _ in backed_up:
        try:
            if os.path.isdir(bak_path):
                shutil.rmtree(bak_path)
            else:
                os.remove(bak_path)
        except OSError:
            pass  # Best effort, will be cleaned on next launch


def extract_zip(zip_path, target_dir):
    """Extract ZIP to target directory."""
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(target_dir)


def show_error(title, message):
    """Show an error dialog using tkinter (available on all platforms)."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        # If tkinter fails, print to stderr
        print(f"ERROR: {title}: {message}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="YoutubeWeekly Update Bootstrap")
    parser.add_argument("--zip", required=True, help="Path to the update ZIP file")
    parser.add_argument("--target", required=True, help="Installation directory to update")
    parser.add_argument("--exe", required=True, help="Main executable name (e.g., YoutubeWeekly.exe)")
    parser.add_argument("--pid", required=True, type=int, help="PID of the main app to wait for")
    args = parser.parse_args()

    zip_path = args.zip
    target_dir = args.target
    exe_name = args.exe
    pid = args.pid

    # Step 1: Wait for main app to exit
    if not wait_for_process_exit(pid):
        show_error("Update Failed", "The application did not close in time. Please close it manually and try again.")
        sys.exit(1)

    # Give a moment for file handles to release
    time.sleep(1)

    # Step 2: Validate inputs
    if not os.path.exists(zip_path):
        show_error("Update Failed", f"Update file not found: {zip_path}")
        sys.exit(1)

    if not os.path.isdir(target_dir):
        show_error("Update Failed", f"Installation directory not found: {target_dir}")
        sys.exit(1)

    # Step 3: Backup existing installation
    try:
        backed_up = backup_install(target_dir, exe_name)
    except RuntimeError as e:
        show_error("Update Failed", str(e))
        sys.exit(1)

    # Step 4: Extract new version
    try:
        extract_zip(zip_path, target_dir)
    except (zipfile.BadZipFile, OSError) as e:
        restore_backup(backed_up)
        show_error("Update Failed", f"Failed to extract update: {e}\n\nYour previous version has been restored.")
        sys.exit(1)

    # Step 5: Verify new exe exists
    new_exe = os.path.join(target_dir, exe_name)
    if not os.path.exists(new_exe) or os.path.getsize(new_exe) == 0:
        restore_backup(backed_up)
        show_error("Update Failed", f"Update verification failed: {exe_name} not found after extraction.\n\nYour previous version has been restored.")
        sys.exit(1)

    # Step 6: Success — clean up backups and old ZIP
    cleanup_backup(backed_up)
    try:
        os.remove(zip_path)
    except OSError:
        pass

    # Step 7: Launch new version
    try:
        if sys.platform == "win32":
            subprocess.Popen([new_exe], cwd=target_dir)
        else:
            os.chmod(new_exe, 0o755)
            subprocess.Popen([new_exe], cwd=target_dir)
    except OSError as e:
        show_error("Update Complete", f"Update installed successfully but failed to launch the app: {e}\n\nPlease start YoutubeWeekly manually.")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
