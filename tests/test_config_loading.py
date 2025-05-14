from app.backend.config import load_settings, load_channels

def test_load_settings():
    settings = load_settings()
    assert "keep_old_videos" in settings, "Missing 'keep_old_videos' in settings"
    assert isinstance(settings["keep_old_videos"], bool), "'keep_old_videos' is not a boolean"

def test_load_channels():
    channels = load_channels()
    assert "channel_1" in channels, "Missing 'channel_1' in channels"
    assert "url" in channels["channel_1"], "Channel URL is missing"
