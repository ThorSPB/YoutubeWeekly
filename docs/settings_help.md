# Settings - Configuration Guide

## 📁 File & Folder Settings

### Video Folder
- **Default**: `data/videos/`
- **Purpose**: Where all downloaded videos are stored

### Keep Old Videos
- **Enabled**: Prevents automatic deletion of previous week's videos
- **Disabled**: Only keeps the most recent video per channel (saves space) - Recommended

## ⚡ Download Settings

### Default Quality
- **1080p**: Best quality, largest files
- **720p**: Good quality, moderate size
- **480p**: Lower quality, smaller files
- **mp3**: Audio only

### Enable Automatic Downloads - Recommended
- **When**: Runs on Fridays and Saturdays
- **What**: Automatically downloads next Saturday's videos
- **Requirement**: Must be enabled for hands-free operation

## 🔔 System Settings

### Enable Notifications - Recommended
- Shows system notifications when downloads complete or fail

### Start with Windows (minimized to tray) - Recommended
- **Enabled**: App starts when Windows boots (minimized to tray)
- **Uses**: Windows registry to manage startup
- **Perfect for**: Automatic background operation

## 🎵 Media Player Settings

### Use MPV Player - Recommended
- **Default**: Uses system default video player
- **MPV**: Uses bundled MPV player with custom options
- **Benefits**: Better codec support, custom settings

### MPV Configuration
- **Fullscreen**: Start videos in fullscreen mode
- **Volume**: Set default playback volume (0-130)
- **Screen**: Choose which monitor for fullscreen (multi-monitor setups)
- **Custom Args**: Advanced MPV command-line arguments

## 💾 Advanced Options

### Reset to Defaults
- Restores all settings to original values
- **Warning**: Cannot be undone
- Use if settings become corrupted or you want a fresh start

### Executable Paths
- **MPV/FFmpeg paths**: Automatically managed
- **Custom paths**: Advanced users can specify custom installations - Not recommended

## 🔧 Troubleshooting

### Downloads Failing
1. Check internet connection
2. Check manually the channels to see if the videos have been uploaded

### Player Issues
1. Try disabling "Use MPV Player" to use system default
2. Check that video files aren't corrupted
3. Verify MPV settings in advanced options

### Startup Problems
1. Check Windows registry permissions
2. Disable/re-enable "Start with Windows"
3. Run as administrator if needed