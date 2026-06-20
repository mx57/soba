import os
import random
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QSize
from src.utils.paths import ANIMATIONS_DIR, get_animation_path

class AnimationManager:
    def __init__(self, label: QLabel):
        self.label = label
        self.movie = None
        self.current_state = "idle"
        self.pet_type = "cat"

    def set_animation(self, gif_path):
        if self.movie:
            self.movie.stop()

        self.movie = QMovie(gif_path)
        if not self.movie.isValid():
            print(f"Error: Invalid GIF at {gif_path}")
            return

        # Масштабируем анимацию под размер лейбла
        self.movie.setScaledSize(self.label.size())
        self.label.setMovie(self.movie)
        self.movie.start()

    def play_state(self, state):
        self.current_state = state
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
