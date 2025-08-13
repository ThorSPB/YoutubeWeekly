import winreg
import sys
import os

def get_executable_path():
    """
    Returns the path to the current executable.
    Handles both PyInstaller bundled applications and regular Python execution.
    """
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        return sys.executable
    else:
        # Running in a normal Python environment
        # This assumes the main script is gui.py and the project root is two levels up
        # from app/frontend/gui.py or one level up from app/backend/windows_startup.py
        # For development, we want to run the python interpreter with gui.py
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        gui_script_path = os.path.join(project_root, 'app', 'frontend', 'gui.py')
        return f'"{sys.executable}" "{gui_script_path}"'

def add_to_startup(app_name="YoutubeWeekly", executable_path=None):
    """
    Adds the application to Windows startup.
    """
    if sys.platform != "win32":
        return False

    if executable_path is None:
        executable_path = get_executable_path()

    # The command to run on startup, including the --start-minimized flag
    command = f'{executable_path} --start-minimized'

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        print(f"Added '{app_name}' to startup with command: {command}")
        return True
    except Exception as e:
        print(f"Error adding to startup: {e}")
        return False

def remove_from_startup(app_name="YoutubeWeekly"):
    """
    Removes the application from Windows startup.
    """
    if sys.platform != "win32":
        return False

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        print(f"Removed '{app_name}' from startup.")
        return True
    except FileNotFoundError:
        print(f"'{app_name}' not found in startup (already removed or never added).")
        return True # Already removed, so consider it a success
    except Exception as e:
        print(f"Error removing from startup: {e}")
        return False

def is_in_startup(app_name="YoutubeWeekly"):
    """
    Checks if the application is currently in Windows startup.
    """
    if sys.platform != "win32":
        return False

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_READ)
        winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"Error checking startup status: {e}")
        return False
