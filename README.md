# YoutubeWeekly

📽️ **YoutubeWeekly** is a simple, self-sufficient desktop app designed to automatically download weekly videos from two specific YouTube channels.  
It finds the correct video for the current or upcoming Sabbath and saves it into organized folders for easy playback — no copy-pasting links or hunting through YouTube necessary.

---

## 🔧 Features

- ✅ Automatically detects and downloads the correct video for the next Sabbath
- 🎯 Custom date selection for downloading older Sabbath videos
- 🎞️ Quality selector (1080p, 720p, 480p, mp3)
- 🧠 Smart video checking (won’t redownload if the correct file already exists)
- 🧹 Automatically deletes old videos (optional)
- 🔗 Manual link input to download any video from any YouTube channel
- 🧭 Clean and responsive GUI
- 🗂️ Downloads are sorted by channel into folders like `colecta/`, `scoala_de_sabat/`, and `other/`
- 💾 Open-source and portable (no installation required once built)
- 🚀 Option to start the app at system startup
- 📝 File viewer windows, for selecting which video to play and deleting videos if necessary
- 📺 **mpv** media player bundled for easy playback
- 📊 **ffmpeg** bundled for video conversion

---

## 🚀 Getting Started

This app is written in **Python** using `tkinter`, `yt-dlp`, and is intended to be packaged into a standalone executable using `PyInstaller`.

---
### Recommendations and Instructions
- The release version will come with the recommended settings, which are the following:
    * "Enable Automatic Downloads" - checked
    * "Enable Notifications" - checked
    * "Start with System (minimized to tray)" - checked

With these 3 settings you just need to run the app once and afterwards every time you turn on the computer it will start automatically and sit quietly in the system tray. If it's Friday or Saturday it will automatically download the Sabbath videos if they exists, a notification will pop up when that process starts and at the end of the process another will pop up to let you know if the download was successful or not, with specific details, like which video was downloaded and which wasn't.

The play buttons next to each download button will play play the latest video downloaded, in the file viewer windows you can select which video to play if you want a specific one. The play buttons will also you your default player so any settings made in that player will be available to these videos as well. If you opted to use the bundled "MPV" you have the options to select the screen to which the video will be played on, fullscreen, and volume. For those familiar with MPV you also have a filed in which you can add any command arguments.



---
  > This project bundles [MPV](https://mpv.io) (GPL v2+) and [FFmpeg](https://ffmpeg.org) (GPL v3 or later). These components are licensed under their respective licenses.
  > Source code for MPV and FFmpeg is available at their official repositories:
  >
  > * MPV: [https://github.com/mpv-player/mpv](https://github.com/mpv-player/mpv)
  > * FFmpeg: [https://github.com/FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg)

---
