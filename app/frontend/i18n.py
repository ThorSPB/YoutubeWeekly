"""Internationalization (i18n) for YoutubeWeekly."""

_current_lang = "en"

TRANSLATIONS = {
    "en": {
        # === Main Window ===
        "app_title": "YoutubeWeekly Downloader",
        "status_ready": "Ready to download weekly videos, or any custom videos. Select quality and date, then click Download.",
        "status_update_complete": "Update complete! Now running v{version}.",
        "btn_download": "Download",
        "btn_download_channel": "Download {name}",
        "btn_quit": "Quit",
        "placeholder_paste_link": "Paste YouTube link...",

        # Tray
        "tray_show": "Show",
        "tray_quit": "Quit",

        # Status messages
        "status_download_in_progress": "A download for {name} is already in progress.",
        "status_others_in_progress": "A download for 'others' is already in progress.",
        "status_enter_link": "Please enter a YouTube link.",
        "status_starting_download": "Starting download...",
        "status_error_starting": "Error starting download thread: {error}",
        "status_download_complete": "Download complete.",
        "status_error_downloading": "Error downloading: {error}",
        "status_error_downloading_name": "Error downloading {name}: {error}",
        "status_finding_video": "Finding video for {name}...",
        "status_date_parse_error": "Date parse error: {error}",
        "status_no_video_found": "No video found for {name} on {date}.",
        "status_download_cancelled": "Download cancelled for {name}.",
        "status_already_exists": "Video for {name} already exists: {titles}",
        "status_downloading": "Downloading from {name} ({quality})...",
        "status_downloading_percent": "Downloading... {percent}%",
        "status_searching_latest": "Searching for latest video in {name}...",
        "status_no_videos_yet": "No videos downloaded for {name} yet.",
        "status_no_videos_found": "No videos found for {name}.",
        "status_playing": "Playing {filename}...",
        "status_play_error": "Error playing video: {error}",
        "status_launched_player": "Launched video player for {name}.",
        "status_checking_updates": "Checking for updates...",
        "status_latest_version": "You're running the latest version.",
        "status_downloading_update": "Downloading update v{version}...",
        "status_downloading_update_percent": "Downloading update... {percent}%",
        "status_installing_update": "Installing update...",
        "status_update_download_failed": "Update download failed: {error}",
        "status_updater_launch_failed": "Could not launch updater: {error}",

        # Dialogs
        "dlg_config_warnings": "Configuration Warnings",
        "dlg_possible_match": "Possible Match Found",
        "dlg_possible_match_msg": "No exact match for {name} on {date}.\n\nFound a similar video:\n\"{title}\"\n\nReason: {reason}\n\nDownload this video?",
        "dlg_download_error": "Download Error",
        "dlg_download_failed": "Failed to download video:\n{error}",
        "dlg_download_failed_name": "Failed to download {name}:\n{error}",
        "dlg_playback_error": "Playback Error",
        "dlg_playback_failed": "Could not play video:\n{error}",
        "dlg_error": "Error",
        "dlg_folder_error": "Could not open folder: {error}",
        "dlg_update_available": "Update Available",
        "dlg_version_available": "Version {version} is available!",
        "dlg_update_question": "Would you like to update now?",
        "dlg_update_now": "Update Now",
        "dlg_later": "Later",
        "dlg_manual_update": "Manual Update Required",
        "dlg_manual_update_msg": "This is a one-time manual update to v{version}.\n\nDownload and extract the ZIP to replace your current installation.\nFuture updates will be automatic.",
        "dlg_update_failed": "Update Failed",
        "dlg_update_no_write": "Cannot write to the installation directory:\n{path}\n\nTry running the app as administrator, or move it to a user-writable location.",
        "dlg_manual_download": "Manual Download Required",
        "dlg_manual_download_msg": "No matching download found for your platform.\nOpening the release page in your browser.",
        "dlg_update_download_failed": "Download failed:\n{error}",
        "dlg_updater_failed": "Could not launch updater:\n{error}",
        "dlg_whats_new": "What's New in v{version}",
        "dlg_updated_fallback": "Updated to the latest version.",
        "btn_got_it": "Got it!",
        "dlg_instance_error": "Could not connect to the running instance.",

        # Notifications
        "notif_video_not_found": "Video Not Found",
        "notif_download_error": "Download Error",
        "notif_download_complete": "Download Complete",
        "notif_finished_downloading": "Finished downloading video for {name}.",
        "notif_finished_link": "Finished downloading video from link: {link}",
        "notif_failed_link": "Failed to download video from link: {link}\n{error}",
        "notif_failed_name": "Failed to download video for {name}: {error}",
        "notif_update_detected": "Update Detected",
        "notif_installing_auto": "Installing v{version} automatically...",
        "notif_update_available": "Update Available",
        "notif_update_available_msg": "Version {version} is available. Open the app to update.",
        "notif_update_failed": "Update Failed",
        "notif_auto_update_failed": "Auto-update download failed: {error}",
        "notif_updater_failed": "Could not launch updater: {error}",

        # === Settings Window ===
        "settings_title": "Settings",
        "tab_general": "General",
        "tab_player": "Player",
        "tab_advanced": "Advanced",

        # General tab
        "chk_keep_old_videos": "Keep old videos",
        "lbl_video_folder": "Video folder:",
        "btn_browse": "Browse",
        "lbl_default_quality": "Default quality:",
        "chk_auto_download": "Enable Automatic Downloads",
        "chk_notifications": "Enable Notifications",
        "chk_start_with_system": "Start with System (minimized to tray)",
        "chk_check_updates": "Check for updates on startup",
        "chk_auto_install": "Auto-install updates on startup",
        "chk_telemetry": "Send anonymous usage data",
        "lbl_telemetry_desc": "Helps improve the app. No personal data is collected.",

        # Player tab
        "chk_use_mpv": "Use MPV Player",
        "lbl_mpv_path": "MPV Path:",
        "chk_mpv_fullscreen": "MPV Fullscreen",
        "lbl_volume": "Volume (0-130):",
        "lbl_monitor": "Monitor:",
        "lbl_monitor_default": "Default",
        "lbl_custom_args": "Custom Arguments:",

        # Advanced tab
        "lbl_ffmpeg_path": "FFmpeg Path:",
        "lbl_ffmpeg_warning": "Warning: Only change FFmpeg path if you know what you're doing.",
        "btn_rollback": "Rollback to Previous Version",

        # Bottom buttons
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        "btn_reset": "Reset to Defaults",

        # Rollback dialog
        "dlg_rollback_title": "Rollback to Previous Version",
        "lbl_current_version": "Current version: v{version}",
        "lbl_loading_versions": "Loading available versions...",
        "lbl_no_versions": "No other versions available",
        "dlg_no_selection": "No Selection",
        "dlg_select_version": "Please select a version to rollback to.",
        "dlg_confirm_rollback": "Confirm Rollback",
        "dlg_rollback_msg": "Are you sure you want to rollback to v{version}?\n\nYour settings and downloaded videos will be preserved.\nThe app will close and restart on the selected version.",
        "dlg_rollback_failed": "Rollback Failed",
        "dlg_rollback_no_download": "No download available for this version on your platform.",

        # Reset dialog
        "dlg_confirm_reset": "Confirm Reset",
        "dlg_reset_msg": "Are you sure you want to reset all settings to their default values? This cannot be undone.",

        # Help
        "help_settings_title": "Settings Guide",
        "help_user_title": "User Guide",

        # Language
        "lbl_language": "Language:",

        # === Feedback Window ===
        "fb_title": "Feedback",
        "fb_new": "+ New",
        "fb_back": "← Back",
        "fb_loading": "Loading feedback...",
        "fb_empty": "No feedback yet. Click '+ New' to send feedback.",
        "fb_new_reply": "● New Reply",
        "fb_dev_prefix": "Dev: ",
        "fb_you_prefix": "You: ",
        "fb_your_message": "Your message:",
        "fb_replies": "REPLIES",
        "fb_developer": "Developer",
        "fb_you": "You",
        "fb_reply_section": "REPLY",
        "fb_send_reply": "Send Reply",
        "fb_sending": "Sending...",
        "fb_reply_sent": "Reply sent!",
        "fb_failed": "Failed: {error}",
        "fb_category": "Category",
        "fb_message": "Message",
        "fb_screenshots": "Screenshots",
        "fb_drop_hint": "Click to add or drag & drop images here",
        "fb_images_attached": "{count} image(s) attached — click to add more",
        "fb_send_feedback": "Send Feedback",
        "fb_sending_feedback": "Sending feedback...",
        "fb_feedback_sent": "Feedback sent!",
        "fb_missing_message": "Missing Message",
        "fb_enter_message": "Please enter a message.",
        "fb_send_failed": "Send Failed",
        "fb_select_screenshots": "Select Screenshots",
        "fb_thread_count": "{count} feedback thread(s)",

        # Categories
        "cat_bug_report": "Bug Report",
        "cat_feature_request": "Feature Request",
        "cat_positive_feedback": "Positive Feedback",
        "cat_negative_feedback": "Negative Feedback",
        "cat_other": "Other",

        # === File Viewer ===
        "fv_title": "Files for {name}",
        "fv_file_name": "File Name",
        "fv_play_selected": "Play Selected",
        "fv_delete_selected": "Delete Selected",
        "fv_delete_all": "Delete All",
        "fv_no_selection": "No Selection",
        "fv_select_video": "Please select a video to play.",
        "fv_select_file": "Please select a file to delete.",
        "fv_confirm_delete": "Confirm Delete",
        "fv_confirm_delete_msg": "Are you sure you want to permanently delete {filename}?",
        "fv_delete_error": "Failed to delete file: {error}",
        "fv_empty": "Empty",
        "fv_already_empty": "The folder is already empty.",
        "fv_confirm_delete_all": "Confirm Delete All",
        "fv_confirm_delete_all_msg": "Are you sure you want to permanently delete ALL files in the {name} folder? This cannot be undone.",
        "fv_delete_all_error": "Failed to delete files: {error}",

        # === Help Window ===
        "help_title": "Help - {title}",
        "help_close": "Close",
        "help_not_found": "Help file not found.\n\nSearched paths:\n",
        "help_load_error": "Error loading help content:\n\n{error}",

        # === Auto Downloader ===
        "auto_started": "Auto Download Started",
        "auto_starting_msg": "Starting automatic download for: {channels}",
        "auto_downloading": "Auto downloading {name}...",
        "auto_complete_status": "Auto downloads complete.",
        "auto_already_downloaded": "Auto Download",
        "auto_already_downloaded_msg": "All videos were already downloaded.",
        "auto_complete": "Auto Download Complete",
        "auto_complete_msg": "All videos downloaded successfully.",
        "auto_partial": "Auto Download Partially Complete",
        "auto_failed": "Auto Download Failed",
    },
    "ro": {
        # === Main Window ===
        "app_title": "YoutubeWeekly",
        "status_ready": "Pregătit pentru descărcarea videoclipurilor săptămânale sau personalizate. Selectează calitatea și data, apoi apasă Descarcă.",
        "status_update_complete": "Actualizare completă! Acum rulezi v{version}.",
        "btn_download": "Descarcă",
        "btn_download_channel": "Descarcă {name}",
        "btn_quit": "Ieșire",
        "placeholder_paste_link": "Lipește link YouTube...",

        # Tray
        "tray_show": "Afișează",
        "tray_quit": "Ieșire",

        # Status messages
        "status_download_in_progress": "O descărcare pentru {name} este deja în desfășurare.",
        "status_others_in_progress": "O descărcare pentru 'altele' este deja în desfășurare.",
        "status_enter_link": "Te rugăm să introduci un link YouTube.",
        "status_starting_download": "Se începe descărcarea...",
        "status_error_starting": "Eroare la pornirea descărcării: {error}",
        "status_download_complete": "Descărcare completă.",
        "status_error_downloading": "Eroare la descărcare: {error}",
        "status_error_downloading_name": "Eroare la descărcarea {name}: {error}",
        "status_finding_video": "Se caută videoclipul pentru {name}...",
        "status_date_parse_error": "Eroare la parsarea datei: {error}",
        "status_no_video_found": "Nu s-a găsit videoclip pentru {name} pe {date}.",
        "status_download_cancelled": "Descărcare anulată pentru {name}.",
        "status_already_exists": "Videoclipul pentru {name} există deja: {titles}",
        "status_downloading": "Se descarcă de la {name} ({quality})...",
        "status_downloading_percent": "Se descarcă... {percent}%",
        "status_searching_latest": "Se caută ultimul videoclip în {name}...",
        "status_no_videos_yet": "Nu s-au descărcat videoclipuri pentru {name} încă.",
        "status_no_videos_found": "Nu s-au găsit videoclipuri pentru {name}.",
        "status_playing": "Se redă {filename}...",
        "status_play_error": "Eroare la redare: {error}",
        "status_launched_player": "Player-ul video a fost lansat pentru {name}.",
        "status_checking_updates": "Se verifică actualizările...",
        "status_latest_version": "Rulezi cea mai recentă versiune.",
        "status_downloading_update": "Se descarcă actualizarea v{version}...",
        "status_downloading_update_percent": "Se descarcă actualizarea... {percent}%",
        "status_installing_update": "Se instalează actualizarea...",
        "status_update_download_failed": "Descărcarea actualizării a eșuat: {error}",
        "status_updater_launch_failed": "Nu s-a putut lansa actualizatorul: {error}",

        # Dialogs
        "dlg_config_warnings": "Avertismente de configurare",
        "dlg_possible_match": "Potrivire posibilă găsită",
        "dlg_possible_match_msg": "Nu s-a găsit potrivire exactă pentru {name} pe {date}.\n\nS-a găsit un videoclip similar:\n\"{title}\"\n\nMotiv: {reason}\n\nDorești să descarci acest videoclip?",
        "dlg_download_error": "Eroare de descărcare",
        "dlg_download_failed": "Descărcarea videoclipului a eșuat:\n{error}",
        "dlg_download_failed_name": "Descărcarea {name} a eșuat:\n{error}",
        "dlg_playback_error": "Eroare de redare",
        "dlg_playback_failed": "Nu s-a putut reda videoclipul:\n{error}",
        "dlg_error": "Eroare",
        "dlg_folder_error": "Nu s-a putut deschide folderul: {error}",
        "dlg_update_available": "Actualizare disponibilă",
        "dlg_version_available": "Versiunea {version} este disponibilă!",
        "dlg_update_question": "Dorești să actualizezi acum?",
        "dlg_update_now": "Actualizează",
        "dlg_later": "Mai târziu",
        "dlg_manual_update": "Actualizare manuală necesară",
        "dlg_manual_update_msg": "Aceasta este o actualizare manuală unică la v{version}.\n\nDescarcă și extrage ZIP-ul pentru a înlocui instalarea curentă.\nActualizările viitoare vor fi automate.",
        "dlg_update_failed": "Actualizare eșuată",
        "dlg_update_no_write": "Nu se poate scrie în directorul de instalare:\n{path}\n\nÎncearcă să rulezi aplicația ca administrator sau mut-o într-o locație accesibilă.",
        "dlg_manual_download": "Descărcare manuală necesară",
        "dlg_manual_download_msg": "Nu s-a găsit o descărcare potrivită pentru platforma ta.\nSe deschide pagina de lansare în browser.",
        "dlg_update_download_failed": "Descărcarea a eșuat:\n{error}",
        "dlg_updater_failed": "Nu s-a putut lansa actualizatorul:\n{error}",
        "dlg_whats_new": "Ce este nou în v{version}",
        "dlg_updated_fallback": "Actualizat la cea mai recentă versiune.",
        "btn_got_it": "Am înțeles!",
        "dlg_instance_error": "Nu s-a putut conecta la instanța care rulează.",

        # Notifications
        "notif_video_not_found": "Videoclip negăsit",
        "notif_download_error": "Eroare de descărcare",
        "notif_download_complete": "Descărcare completă",
        "notif_finished_downloading": "S-a terminat descărcarea videoclipului pentru {name}.",
        "notif_finished_link": "S-a terminat descărcarea videoclipului de la: {link}",
        "notif_failed_link": "Descărcarea videoclipului de la {link} a eșuat:\n{error}",
        "notif_failed_name": "Descărcarea videoclipului pentru {name} a eșuat: {error}",
        "notif_update_detected": "Actualizare detectată",
        "notif_installing_auto": "Se instalează v{version} automat...",
        "notif_update_available": "Actualizare disponibilă",
        "notif_update_available_msg": "Versiunea {version} este disponibilă. Deschide aplicația pentru a actualiza.",
        "notif_update_failed": "Actualizare eșuată",
        "notif_auto_update_failed": "Descărcarea automată a actualizării a eșuat: {error}",
        "notif_updater_failed": "Nu s-a putut lansa actualizatorul: {error}",

        # === Settings Window ===
        "settings_title": "Setări",
        "tab_general": "General",
        "tab_player": "Player",
        "tab_advanced": "Avansat",

        # General tab
        "chk_keep_old_videos": "Păstrează videoclipurile vechi",
        "lbl_video_folder": "Folder videoclipuri:",
        "btn_browse": "Răsfoiește",
        "lbl_default_quality": "Calitate implicită:",
        "chk_auto_download": "Activează descărcarea automată",
        "chk_notifications": "Activează notificările",
        "chk_start_with_system": "Pornește cu sistemul (minimizat în tray)",
        "chk_check_updates": "Verifică actualizările la pornire",
        "chk_auto_install": "Instalează automat actualizările la pornire",
        "chk_telemetry": "Trimite date anonime de utilizare",
        "lbl_telemetry_desc": "Ajută la îmbunătățirea aplicației. Nu se colectează date personale.",

        # Player tab
        "chk_use_mpv": "Folosește MPV Player",
        "lbl_mpv_path": "Cale MPV:",
        "chk_mpv_fullscreen": "MPV Ecran complet",
        "lbl_volume": "Volum (0-130):",
        "lbl_monitor": "Monitor:",
        "lbl_monitor_default": "Implicit",
        "lbl_custom_args": "Argumente personalizate:",

        # Advanced tab
        "lbl_ffmpeg_path": "Cale FFmpeg:",
        "lbl_ffmpeg_warning": "Atenție: Modifică calea FFmpeg doar dacă știi ce faci.",
        "btn_rollback": "Revenire la versiunea anterioară",

        # Bottom buttons
        "btn_save": "Salvează",
        "btn_cancel": "Anulează",
        "btn_reset": "Resetează la valorile implicite",

        # Rollback dialog
        "dlg_rollback_title": "Revenire la versiunea anterioară",
        "lbl_current_version": "Versiunea curentă: v{version}",
        "lbl_loading_versions": "Se încarcă versiunile disponibile...",
        "lbl_no_versions": "Nu sunt alte versiuni disponibile",
        "dlg_no_selection": "Nicio selecție",
        "dlg_select_version": "Te rugăm să selectezi o versiune.",
        "dlg_confirm_rollback": "Confirmă revenirea",
        "dlg_rollback_msg": "Ești sigur că vrei să revii la v{version}?\n\nSetările și videoclipurile descărcate vor fi păstrate.\nAplicația se va închide și va reporni pe versiunea selectată.",
        "dlg_rollback_failed": "Revenire eșuată",
        "dlg_rollback_no_download": "Nu este disponibilă descărcarea pentru această versiune pe platforma ta.",

        # Reset dialog
        "dlg_confirm_reset": "Confirmă resetarea",
        "dlg_reset_msg": "Ești sigur că vrei să resetezi toate setările la valorile implicite? Această acțiune nu poate fi anulată.",

        # Help
        "help_settings_title": "Ghid setări",
        "help_user_title": "Ghid utilizator",

        # Language
        "lbl_language": "Limbă:",

        # === Feedback Window ===
        "fb_title": "Feedback",
        "fb_new": "+ Nou",
        "fb_back": "← Înapoi",
        "fb_loading": "Se încarcă feedback-ul...",
        "fb_empty": "Nu există feedback încă. Apasă '+ Nou' pentru a trimite.",
        "fb_new_reply": "● Răspuns nou",
        "fb_dev_prefix": "Dev: ",
        "fb_you_prefix": "Tu: ",
        "fb_your_message": "Mesajul tău:",
        "fb_replies": "RĂSPUNSURI",
        "fb_developer": "Dezvoltator",
        "fb_you": "Tu",
        "fb_reply_section": "RĂSPUNDE",
        "fb_send_reply": "Trimite răspuns",
        "fb_sending": "Se trimite...",
        "fb_reply_sent": "Răspuns trimis!",
        "fb_failed": "Eșuat: {error}",
        "fb_category": "Categorie",
        "fb_message": "Mesaj",
        "fb_screenshots": "Capturi de ecran",
        "fb_drop_hint": "Apasă pentru a adăuga sau trage imaginile aici",
        "fb_images_attached": "{count} imagine(i) atașată(e) — apasă pentru a adăuga mai multe",
        "fb_send_feedback": "Trimite feedback",
        "fb_sending_feedback": "Se trimite feedback-ul...",
        "fb_feedback_sent": "Feedback trimis!",
        "fb_missing_message": "Mesaj lipsă",
        "fb_enter_message": "Te rugăm să introduci un mesaj.",
        "fb_send_failed": "Trimitere eșuată",
        "fb_select_screenshots": "Selectează capturi de ecran",
        "fb_thread_count": "{count} conversație(i) de feedback",

        # Categories
        "cat_bug_report": "Raport de eroare",
        "cat_feature_request": "Cerere de funcționalitate",
        "cat_positive_feedback": "Feedback pozitiv",
        "cat_negative_feedback": "Feedback negativ",
        "cat_other": "Altele",

        # === File Viewer ===
        "fv_title": "Fișiere pentru {name}",
        "fv_file_name": "Numele fișierului",
        "fv_play_selected": "Redă selecția",
        "fv_delete_selected": "Șterge selecția",
        "fv_delete_all": "Șterge tot",
        "fv_no_selection": "Nicio selecție",
        "fv_select_video": "Te rugăm să selectezi un videoclip pentru redare.",
        "fv_select_file": "Te rugăm să selectezi un fișier pentru ștergere.",
        "fv_confirm_delete": "Confirmă ștergerea",
        "fv_confirm_delete_msg": "Ești sigur că vrei să ștergi permanent {filename}?",
        "fv_delete_error": "Ștergerea fișierului a eșuat: {error}",
        "fv_empty": "Gol",
        "fv_already_empty": "Folderul este deja gol.",
        "fv_confirm_delete_all": "Confirmă ștergerea totală",
        "fv_confirm_delete_all_msg": "Ești sigur că vrei să ștergi permanent TOATE fișierele din folderul {name}? Această acțiune nu poate fi anulată.",
        "fv_delete_all_error": "Ștergerea fișierelor a eșuat: {error}",

        # === Help Window ===
        "help_title": "Ajutor - {title}",
        "help_close": "Închide",
        "help_not_found": "Fișierul de ajutor nu a fost găsit.\n\nCăi căutate:\n",
        "help_load_error": "Eroare la încărcarea conținutului:\n\n{error}",

        # === Auto Downloader ===
        "auto_started": "Descărcare automată pornită",
        "auto_starting_msg": "Se începe descărcarea automată pentru: {channels}",
        "auto_downloading": "Se descarcă automat {name}...",
        "auto_complete_status": "Descărcări automate complete.",
        "auto_already_downloaded": "Descărcare automată",
        "auto_already_downloaded_msg": "Toate videoclipurile au fost deja descărcate.",
        "auto_complete": "Descărcare automată completă",
        "auto_complete_msg": "Toate videoclipurile au fost descărcate cu succes.",
        "auto_partial": "Descărcare automată parțial completă",
        "auto_failed": "Descărcare automată eșuată",
    },
}


def set_language(lang):
    """Set the active language."""
    global _current_lang
    if lang in TRANSLATIONS:
        _current_lang = lang


def get_language():
    """Get the current language code."""
    return _current_lang


def t(key, **kwargs):
    """Translate a key, with optional format arguments."""
    text = TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"]).get(
        key, TRANSLATIONS["en"].get(key, key)
    )
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
