# YoutubeWeekly

## Project Overview

**YoutubeWeekly** is a Python-based desktop application designed to automate the download of weekly videos from specified YouTube channels. It features a graphical user interface (GUI) built with `tkinter` and utilizes the `yt-dlp` library to handle video downloads. The application is intended to be packaged into a standalone executable using `PyInstaller`, making it portable and easy to use without a Python installation.

The core functionality revolves around automatically identifying and downloading the correct video for the upcoming Sabbath, but it also supports downloading older videos by selecting a specific date. Users can also manually input any YouTube video link to download.

## Building and Running

### Dependencies

The project's Python dependencies are listed in the `requirements.txt` file. To install them, run:

```bash
pip install -r requirements.txt
```

### Running the Application

To run the application directly from the source code, execute the following command from the project's root directory:

```bash
python app/frontend/gui.py
```

### Running Tests

The project uses `pytest` for testing. To run the test suite, use the following command:

```bash
pytest
```

### Building the Executable

The `README.md` mentions that `PyInstaller` is used to create a standalone executable. While a specific build command is not provided, a typical `PyInstaller` command for a `tkinter` application would be:

```bash
# TODO: Verify and update this command as needed.
pyinstaller --onefile --windowed --name YoutubeWeekly main.py
```

## Development Conventions

*   **Configuration:** Application settings are managed through a `config.json` file, which is loaded and saved by the functions in `config/config.py`.
*   **Structure:** The application is structured into frontend (`app/frontend/gui.py`) and backend (`app/backend/`) components. The backend handles the core logic of video downloading and configuration management.
*   **GUI:** The user interface is built using Python's standard `tkinter` library.
*   **Dependencies:** The project uses `yt-dlp` for YouTube video downloading, which is a fork of `youtube-dl` with additional features and fixes.

## Background Mode Implementation Plan

### Goal
Implement a background mode for the YoutubeWeekly application, allowing it to run minimized to the system tray and start automatically with the operating system.

### Key Features
1.  **System Tray Integration:** The application will minimize to the system tray instead of closing, providing an icon for quick access.
2.  **Minimize to Tray:** When the main window is closed, the application will hide the window and move to the system tray.
3.  **Restore from Tray:** Clicking the system tray icon or selecting an option from its context menu will restore the main application window.
4.  **Exit from Tray:** A context menu option in the system tray will allow users to fully exit the application.
5.  **Startup Minimization:** An option to start the application directly in the system tray upon system startup.

### Technical Approach

1.  **Dependencies:**
    *   `pystray`: For creating and managing the system tray icon and its context menu.
    *   `Pillow`: A dependency for `pystray` to handle image processing for the tray icon.
    *   `pyinstaller`: Ensure compatibility with `pystray` when building the executable.

2.  **GUI Modifications (`app/frontend/gui.py`):**
    *   **Window Close Protocol:** Override the `WM_DELETE_WINDOW` protocol to hide the window and show the system tray icon instead of destroying the window.
    *   **System Tray Icon:** Initialize `pystray.Icon` with an appropriate icon (e.g., a simple image file or generated icon).
    *   **Context Menu:** Define a menu for the system tray icon with options like "Show Window" and "Exit".
    *   **Event Handling:** Implement callbacks for menu actions (e.g., showing the window, quitting the application).

3.  **Configuration (`config/config.py` and `config.json`):**
    *   Add a new setting, e.g., `"start_minimized_to_tray": false`, to `config.json`.
    *   Modify `config.py` to load and save this new setting.

4.  **Command-Line Arguments:**
    *   Implement argument parsing (e.g., using `argparse`) to detect a `--start-minimized` flag.
    *   If this flag is present, the application will start directly in the system tray without displaying the main window initially.

5.  **OS-Specific Startup (Documentation/Instructions):**
    *   Provide instructions for users on how to add the application to their system's startup programs for Windows, macOS, and Linux. This will typically involve creating a shortcut with the `--start-minimized` argument.

### Implementation Steps

1.  **Install Dependencies:** (Already done) Ensure `pystray` and `Pillow` are installed.
2.  **Create System Tray Icon:** Design or find a suitable icon for the system tray.
3.  **Integrate `pystray`:**
    *   Modify `app/frontend/gui.py` to import `pystray` and `PIL.Image`.
    *   Create a `pystray.Icon` instance.
    *   Define the menu for the icon.
    *   Implement functions to show/hide the main window and quit the application.
    *   Start the `pystray` icon in a separate thread to avoid blocking the `tkinter` main loop.
4.  **Handle Window Close:**
    *   Modify the `WM_DELETE_WINDOW` protocol to hide the window and display the tray icon.
5.  **Add Configuration Option:**
    *   Update `config.json` and `config/config.py` with the `start_minimized_to_tray` setting.
6.  **Implement Command-Line Parsing:**
    *   Add `argparse` to `app/frontend/gui.py` (or `main.py` if it's the entry point) to handle the `--start-minimized` argument.
7.  **Test:** Thoroughly test the new functionality, including minimizing, restoring, exiting, and starting minimized.
8.  **Update PyInstaller Build:** Ensure the PyInstaller build process correctly bundles `pystray` and `Pillow` and handles the new startup behavior.