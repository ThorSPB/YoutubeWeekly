import os
import subprocess
import plistlib

def get_launch_agent_path(app_name):
    return os.path.expanduser(f"~/Library/LaunchAgents/com.{app_name}.plist")

def add_to_startup(app_name="YoutubeWeekly", executable_path=None):
    if executable_path is None:
        print("Error: executable_path is required for macOS startup.")
        return False

    plist_path = get_launch_agent_path(app_name)
    label = f"com.{app_name}"

    # Create the plist content
    plist_content = {
        'Label': label,
        'ProgramArguments': [
            executable_path,
            '--start-minimized'
        ],
        'RunAtLoad': True,
        'KeepAlive': False,
        'StandardOutPath': os.path.expanduser(f"~/Library/Logs/{app_name}.log"),
        'StandardErrorPath': os.path.expanduser(f"~/Library/Logs/{app_name}.log"),
    }

    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(plist_path), exist_ok=True)
        with open(plist_path, 'wb') as fp:
            plistlib.dump(plist_content, fp)

        # Load the LaunchAgent to activate it immediately
        subprocess.run(['launchctl', 'load', plist_path], check=True)
        print(f"Added '{app_name}' to macOS startup.")
        return True
    except Exception as e:
        print(f"Error adding to macOS startup: {e}")
        return False

def remove_from_startup(app_name="YoutubeWeekly"):
    plist_path = get_launch_agent_path(app_name)

    try:
        if os.path.exists(plist_path):
            # Unload the LaunchAgent first
            subprocess.run(['launchctl', 'unload', plist_path], check=True)
            os.remove(plist_path)
            print(f"Removed '{app_name}' from macOS startup.")
        else:
            print(f"'{app_name}' not found in macOS startup (already removed or never added).")
        return True
    except Exception as e:
        print(f"Error removing from macOS startup: {e}")
        return False

def is_in_startup(app_name="YoutubeWeekly"):
    plist_path = get_launch_agent_path(app_name)
    return os.path.exists(plist_path)
