import os

def get_desktop_file_path(app_name):
    return os.path.expanduser(f"~/.config/autostart/{app_name}.desktop")

def add_to_startup(app_name="YoutubeWeekly", executable_path=None):
    if executable_path is None:
        print("Error: executable_path is required for Linux startup.")
        return False

    desktop_file_path = get_desktop_file_path(app_name)

    # Create the .desktop file content
    desktop_content = f"""
[Desktop Entry]
Type=Application
Exec={executable_path} --start-minimized
Hidden=false
NoDisplay=false
Name={app_name}
Comment=YoutubeWeekly Downloader
X-GNOME-Autostart-enabled=true
"""

    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(desktop_file_path), exist_ok=True)
        with open(desktop_file_path, 'w') as f:
            f.write(desktop_content)
        os.chmod(desktop_file_path, 0o755) # Make it executable
        print(f"Added '{app_name}' to Linux startup.")
        return True
    except Exception as e:
        print(f"Error adding to Linux startup: {e}")
        return False

def remove_from_startup(app_name="YoutubeWeekly"):
    desktop_file_path = get_desktop_file_path(app_name)

    try:
        if os.path.exists(desktop_file_path):
            os.remove(desktop_file_path)
            print(f"Removed '{app_name}' from Linux startup.")
        else:
            print(f"'{app_name}' not found in Linux startup (already removed or never added).")
        return True
    except Exception as e:
        print(f"Error removing from Linux startup: {e}")
        return False

def is_in_startup(app_name="YoutubeWeekly"):
    desktop_file_path = get_desktop_file_path(app_name)
    return os.path.exists(desktop_file_path)
