import winreg
import sys
import os

def add_to_startup(app_name="YoutubeWeekly", executable_path=None):
    """
    Adds the application to Windows startup.
    """
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
