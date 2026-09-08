# Changelog

## Unreleased
- **Children's Videos Really Do Arrive in Full Quality Now**: The last release said it had fixed this and hadn't — those videos still came down at 360p instead of the quality you picked. YouTube's check needs two pieces of code to run, and the app was only carrying one. It now ships both, so they download at the full 1080p

## v1.6.2
- **Children's Videos Download Again, in Full Quality**: Videos marked "Made for Kids" on YouTube — children's songs, Bible stories and the like — all failed with "This video is not available", even though they play perfectly in a browser. YouTube holds those back unless the app can run a piece of its code, so the app now carries the small engine needed. They download at full 1080p again, and any link that still refuses is retried a second way before the app gives up

## v1.6.1
- **Sharper App Icon**: The icon shipped at a single small size, so Windows stretched it for shortcuts, folder views and notifications — it looked fuzzy nearly everywhere. It now includes every size Windows asks for, up to 256px

## v1.6.0
- **Progress Bar No Longer Sticks at 50%**: Downloads that come as a single file — an mp3, or a video served directly by the developer — used to leave the bar stuck at half forever, even though the download had finished. Fixed
- **Accurate Progress Bar**: The bar now tracks how many bytes are actually left, instead of giving the video and the audio half each. A 1080p download's audio is a small part of the total, so the bar no longer crawls and then jumps
- **Failed Downloads Stop Looking Like Frozen Ones**: When a download fails, the progress bar is now cleared away instead of being left part-filled on screen
- **Download Button Keeps Your Video Too**: The same fix as the automatic download — pressing Download no longer deletes last week's video before fetching the new one, so a failure can't leave you with nothing
- **Release Notes Cover Everything You Missed**: Updating across more than one version used to show only the newest release's notes — skipping from 1.4.0 to 1.5.1 hid everything 1.5.0 changed. Now you see every release since the one you were running
- **Release Notes in Romanian**: The release notes are now translated, and follow the app's language setting
- **Release Notes Button**: Settings → Advanced → Release Notes opens the full history in a scrollable reader
- **Opens in Front After Updating**: Updating while the app was on screen used to bring it back minimized to the tray. It now returns the way you left it — and an update that installs itself while the app sits in the tray stays there, showing you the notes when you next open it
- **File Type Column**: Folder views now have their own Type column, so you can always tell an MP4 from an MP3 without widening the window
- **App Icon on Every Window**: Settings, folder views and help windows showed a generic icon instead of the app's own. Fixed
- **Downloads Match Your Quality Setting**: When the developer serves a video directly (used when YouTube titles break the app's search), it now comes in the quality you picked instead of always the largest one

## v1.5.1
- **Downloads Work Again**: YouTube changed something in August that the app's downloader couldn't handle any more, so every download failed. Updated it — downloads work again
- **Your Video Stays Until the New One Arrives**: The app used to delete last week's video *before* fetching the new one, so a failed download left you with nothing at all. It now only removes the old video once the new one is safely downloaded
- **No More Silent Videos**: A download that stopped halfway left behind a file with picture but no sound, and the app offered it as if it were finished. Unfinished downloads are now cleaned up and never listed or played
- **Retries Actually Retry**: A leftover half-finished file used to make the app think the video was already downloaded, so it refused to try again. Fixed

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
