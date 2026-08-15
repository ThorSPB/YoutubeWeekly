# Changelog

## v1.5.0
- **Video Overrides**: When a channel uploads a video with the wrong date in the title, the app can no longer find it. The developer can now point the app straight at the correct video, and it downloads normally — no update or reinstall needed
- **Self-Hosted Videos**: An override can also serve a video file hosted directly, not just a YouTube link
- **Corrections While Running**: The app now notices a correction published after it started, instead of only checking once at launch. A forced correction replaces a video already downloaded for that Sabbath
- **Light on the Network**: Checks are cheap (a few hundred bytes when nothing changed), frequent only on Friday and Saturday, and slow the rest of the week

## v1.4.0
- **Romanian Language**: Full Romanian translation — switch from Settings → General → Language
- **Language Toggle**: Choose between English and Română, applies immediately
- **Start with System Fix**: After updating from older versions, the app sometimes wouldn't actually start on boot even though the setting was on — fixed, now refreshes itself on every launch
- **Sort by Date**: Downloaded video lists are now sorted newest-first instead of alphabetically — much better for the Others folder
- **Settings Migration**: New settings from app updates now appear automatically without needing to open the settings window

## v1.3.1
- **Reply to Developer**: You can now respond to developer messages directly in the feedback window
- **Multiple Screenshots**: Attach multiple images to your feedback
- **Notification Badge**: A red badge on the 💬 button shows when the developer has replied
- **Improved Thread View**: See the latest message in each thread and green highlights for new replies
- **Scroll Fix**: Mouse scroll now works properly anywhere in the feedback window
- **Rollback Fix**: Version rollback button is now properly visible

## v1.3.0
- **In-App Feedback**: Send bug reports, feature requests, or general feedback directly from the app
- **Screenshots**: Attach screenshots to your feedback for easier troubleshooting
- **Conversation**: See replies from the developer and track your feedback status
- **System Info**: Hardware details are included with feedback to help diagnose issues

## v1.2.0
- **Usage Analytics**: Anonymous usage data helps improve the app — see how many people use it and which features are popular
- **Opt-Out**: Easily disable analytics from Settings → General → "Send anonymous usage data"
- **Others Tracking**: "Others" custom URL downloads now tracked separately with quality selection
- **Privacy First**: Location is resolved on your device — your IP address is never sent to us

## v1.1.3
- **Version Rollback**: Roll back to any previous version from Settings → Advanced → Rollback
- **Auto-Install Updates**: Automatically install updates on startup (no popup, just updates)
- **Disable Update Checks**: Option to turn off automatic update checking
- **Tabbed Settings**: Settings reorganized into General, Player, and Advanced tabs

## v1.1.2
- **Auto-Updates on Startup**: Automatically install updates when running in system tray
- **Update Check Button**: Check for updates anytime with the ↻ button
- **Post-Update Changelog**: See what's new after each update
- **Update Status**: "Update complete!" message shown on first launch after an update

## v1.1.1
- **Version Display**: Current version shown in the bottom-left corner of the app
- **Video Path Fix**: Video folder path now resets correctly when app is moved to a new location
- **Auto-Update Fixes**: Improved reliability of the update process on Windows

## v1.1.0
- **Auto-Updates**: The app now updates itself automatically — just click "Update Now" when prompted
- **Higher Quality Options**: Added max, 4K, and 2K quality options alongside existing 1080p/720p/480p/mp3
- **Smarter Video Matching**: Handles common title errors (wrong date by 1 day, formatting issues) and asks for confirmation
- **Version Display**: Current version is now shown in the bottom-left corner

## v1.0.4
- Initial public release
- Automatic downloads on Fridays and Saturdays
- Multi-channel support (Departamentul Ispravnicie, ScoalaDeSabat)
- System tray integration with start-with-system support
- MPV player integration with custom settings
