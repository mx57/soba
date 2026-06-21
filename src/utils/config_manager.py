import os
import json

class ConfigManager:
    DEFAULT_CONFIG = {
        "pet_type": "cat",
        "username": "User",
        "always_on_top": True,
        "pomodoro_work": 25,
        "pomodoro_break": 5,
        "stretch_interval": 30,
        "volume": 70,
        "language": "ru",
        "skin": "default"
    }

    def __init__(self, config_path="settings.json"):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return {**self.DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get(self, key):
        return self.config.get(key, self.DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()
