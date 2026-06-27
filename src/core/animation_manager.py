import os
import random
import math
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QMovie, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QTimer, QPoint
from src.utils.paths import ANIMATIONS_DIR, get_animation_path

class AnimationManager:
    def __init__(self, label: QLabel, config=None):
        self.label = label
        self.config = config
        self.movie = None
        self.svg_renderer = None
        self.current_state = "idle"
        self.pet_type = "cat"
        self.skin = config.get("skin") if config else "default"
        self.last_mouse_pos = (0, 0)

        # Таймер для процедурной SVG анимации
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.update_frame)
        self.frame_counter = 0

    def set_animation(self, path):
        if self.movie:
            self.movie.stop()
            self.movie = None

        self.svg_renderer = None
        self.anim_timer.stop()

        if path.endswith(".gif"):
            self.movie = QMovie(path)
            if not self.movie.isValid():
                print(f"Error: Invalid GIF at {path}")
                return
            self.movie.setScaledSize(self.label.size())
            self.label.setMovie(self.movie)
            self.movie.start()
        elif path.endswith(".svg"):
            self.svg_renderer = QSvgRenderer(path)
            self.anim_timer.start(1000 // 12) # 12 FPS
        else:
            # Статическая картинка (скин)
            pixmap = QPixmap(path)
            scaled_pixmap = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(scaled_pixmap)

    def update_frame(self):
        if not self.svg_renderer:
            return

        size = self.label.size()
        pixmap = QPixmap(size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)

        # Процедурные трансформации в зависимости от состояния
        self.frame_counter += 1

        painter.save()

        # Центрирование для вращений
        painter.translate(size.width() / 2, size.height() / 2)

        # Слежение глазами (смещение всего котика в сторону курсора)
        # Оптимизация: используем кешированную позицию мыши
        local_mouse = self.label.mapFromGlobal(self.label.cursor().pos() if not hasattr(self, 'last_mouse_pos_qpoint') else self.last_mouse_pos_qpoint)
        look_x = (local_mouse.x() - size.width()/2) / size.width() * 5
        look_y = (local_mouse.y() - size.height()/2) / size.height() * 5
        painter.translate(look_x, look_y)

        # Базовые трансформации
        if self.current_state == "idle":
            # Дыхание
            scale = 1.0 + 0.02 * math.sin(self.frame_counter * 0.3)
            painter.scale(1.0, scale)
        elif self.current_state == "working":
            # Работа лапками (наклоны влево-вправо)
            angle = 5 * math.sin(self.frame_counter * 0.8)
            painter.rotate(angle)
        elif self.current_state == "happy":
            # Прыжки
            painter.translate(0, -abs(15 * math.sin(self.frame_counter * 0.5)))
        elif self.current_state == "sleeping":
            # Глубокое медленное дыхание + наклон
            scale = 1.0 + 0.05 * math.sin(self.frame_counter * 0.1)
            painter.scale(scale, scale)
            painter.rotate(5)
        elif self.current_state == "hunting":
            # Приседание перед прыжком + тряска
            painter.scale(1.1, 0.9)
            painter.translate(random.randint(-2, 2), 0)
        elif self.current_state == "overheat":
            # Бешеная тряска + увеличение
            painter.scale(1.2, 1.2)
            painter.translate(random.randint(-4, 4), random.randint(-4, 4))
        elif self.current_state == "stretching":
            # Растягивание
            painter.scale(0.8, 1.4)

        painter.translate(-size.width() / 2, -size.height() / 2)

        self.svg_renderer.render(painter)
        painter.restore()
        painter.end()

        self.label.setPixmap(pixmap)

    def play_state(self, state):
        self.current_state = state

        # Если выбран скин, пробуем загрузить его SVG версию
        if self.skin != "default":
            svg_path = os.path.join(ANIMATIONS_DIR, "svg_skins", f"cat_{self.skin}.svg")
            if os.path.exists(svg_path):
                self.set_animation(svg_path)
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

    def set_mouse_pos(self, x, y):
        self.last_mouse_pos = (x, y)
        self.last_mouse_pos_qpoint = QPoint(x, y)
