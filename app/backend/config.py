import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(__file__), '../../config')
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')
CHANNELS_FILE = os.path.join(CONFIG_DIR, 'channels.json')


def load_settings():
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_channels():
    with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
