from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl
import os

class SoundManager:
    def __init__(self, config):
        self.config = config
        self.sounds = {}

    def play_sound(self, sound_name):
        if sound_name not in self.sounds:
            path = f"assets/sounds/{sound_name}.wav"
            if not os.path.exists(path):
                return

            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            self.sounds[sound_name] = effect

        effect = self.sounds[sound_name]
        volume = self.config.get("volume") if self.config else 70
        effect.setVolume(volume / 100.0)
        effect.play()
