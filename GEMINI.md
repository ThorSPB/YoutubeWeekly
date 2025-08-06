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
