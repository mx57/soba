import os
import random
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QMovie, QPixmap
from src.utils.paths import ANIMATIONS_DIR, get_animation_path

class AnimationManager:
    def __init__(self, label: QLabel, config=None):
        self.label = label
        self.config = config
        self.movie = None
        self.current_state = "idle"
        self.pet_type = "cat"
        self.skin = config.get("skin") if config else "default"

    def set_animation(self, path):
        if self.movie:
            self.movie.stop()
            self.movie = None

        if path.endswith(".gif"):
            self.movie = QMovie(path)
            if not self.movie.isValid():
                print(f"Error: Invalid GIF at {path}")
                return
            self.movie.setScaledSize(self.label.size())
            self.label.setMovie(self.movie)
            self.movie.start()
        else:
            # Статическая картинка (скин)
            pixmap = QPixmap(path)
            scaled_pixmap = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(scaled_pixmap)

    def play_state(self, state):
        self.current_state = state

        # Если это скин и состояние idle, пробуем загрузить скин
        if self.skin != "default" and state == "idle":
            skin_path = os.path.join(ANIMATIONS_DIR, "skins", f"cat_{self.skin}.png")
            if os.path.exists(skin_path):
                self.set_animation(skin_path)
                return

        # Поиск анимации
        possible_files = [
            get_animation_path(self.pet_type, state)
        ]

        # Добавляем поддержку нескольких файлов для одного состояния
        for i in range(1, 5):
            possible_files.append(get_animation_path(self.pet_type, state, i))

        valid_files = [f for f in possible_files if os.path.exists(f)]

        if valid_files:
            path = random.choice(valid_files)
            self.set_animation(path)
        else:
            # Fallback на idle если анимация состояния не найдена
            if state != "idle":
                self.play_state("idle")

    def update_size(self, size: QSize):
        if self.movie:
            self.movie.setScaledSize(size)
        elif self.current_state == "idle" and self.skin != "default":
            self.play_state("idle") # Рефреш пиксмапа

    def set_skin(self, skin_name):
        self.skin = skin_name
        if self.config:
            self.config.set("skin", skin_name)
        self.play_state(self.current_state)
