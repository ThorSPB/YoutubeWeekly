import sys
import os

# Dynamically import OS-specific modules
if sys.platform == "win32":
    import app.backend.windows_startup as windows_startup
elif sys.platform == "darwin":
    import app.backend.macos_startup as macos_startup
elif sys.platform.startswith("linux"): # Covers linux and possibly other unix-like systems
    import app.backend.linux_startup as linux_startup
else:
    windows_startup = None
    macos_startup = None
    linux_startup = None

def get_executable_path():
    """
    Returns the path to the current executable or the command to run the script.
    Handles both PyInstaller bundled applications and regular Python execution.
    """
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        return sys.executable
    else:
        # Running in a normal Python environment
        # This assumes the main script is app/frontend/gui.py relative to the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        gui_script_path = os.path.join(project_root, 'app', 'frontend', 'gui.py')
        return f'"{sys.executable}" "{gui_script_path}"'

def add_to_startup(app_name="YoutubeWeekly"):
    executable_path = get_executable_path()
    if sys.platform == "win32" and windows_startup:
        return windows_startup.add_to_startup(app_name, executable_path)
    elif sys.platform == "darwin" and macos_startup:
        return macos_startup.add_to_startup(app_name, executable_path)
    elif sys.platform.startswith("linux") and linux_startup:
        return linux_startup.add_to_startup(app_name, executable_path)
    else:
        print(f"Startup management not supported on {sys.platform}")
        return False

def remove_from_startup(app_name="YoutubeWeekly"):
    if sys.platform == "win32" and windows_startup:
        return windows_startup.remove_from_startup(app_name)
    elif sys.platform == "darwin" and macos_startup:
        return macos_startup.remove_from_startup(app_name)
    elif sys.platform.startswith("linux") and linux_startup:
        return linux_startup.remove_from_startup(app_name)
    else:
        print(f"Startup management not supported on {sys.platform}")
        return False

def is_in_startup(app_name="YoutubeWeekly"):
    if sys.platform == "win32" and windows_startup:
        return windows_startup.is_in_startup(app_name)
    elif sys.platform == "darwin" and macos_startup:
        return macos_startup.is_in_startup(app_name)
    elif sys.platform.startswith("linux") and linux_startup:
        return linux_startup.is_in_startup(app_name)
    else:
        return False
