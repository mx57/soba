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
        self.current_anim_path = None
        self.pet_type = "cat"
        self.skin = config.get("skin") if config else "default"
        cursor_pos = self.label.cursor().pos() if self.label else None
        self.last_mouse_pos = (cursor_pos.x(), cursor_pos.y()) if cursor_pos else (0, 0)
        self.cached_pixmap = None
        self.last_size = QSize(0, 0)
        self.main_window = self.label.window()
        self._current_fps = 12

        # Таймер для процедурной SVG анимации
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.update_frame)
        self.frame_counter = 0

    @property
    def current_fps(self):
        """Возвращает текущую заданную частоту кадров (FPS)."""
        return self._current_fps

    @current_fps.setter
    def current_fps(self, value):
        """Устанавливает текущую заданную частоту кадров (FPS)."""
        self._current_fps = value

    def set_animation(self, path):
        # Оптимизация: не перезагружаем ту же самую анимацию
        if self.current_anim_path == path:
            if path.endswith(".svg") and self.svg_renderer:
                # Обновляем интервал даже если путь тот же (для динамического FPS)
                interval = int(1000 / self.current_fps)
                self.anim_timer.start(interval)
            return

        if self.movie:
            self.movie.stop()
            self.movie = None

        self.svg_renderer = None
        self.anim_timer.stop()
        self.current_anim_path = path

        if path.endswith(".gif"):
            self.movie = QMovie(path)
            if not self.movie.isValid():
                print(f"Error: Invalid GIF at {path}")
                self.current_anim_path = None
                return
            self.movie.setScaledSize(self.label.size())
            self.label.setMovie(self.movie)
            self.movie.start()
        elif path.endswith(".svg"):
            self.svg_renderer = QSvgRenderer(path)
            # Динамический FPS в зависимости от состояния
            interval = int(1000 / self.current_fps)
            self.anim_timer.start(interval)
        else:
            # Статическая картинка (скин)
            pixmap = QPixmap(path)
            scaled_pixmap = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.label.setPixmap(scaled_pixmap)

    def update_frame(self):
        if not self.svg_renderer:
            return

        size = self.label.size()

        # Оптимизация: кэширование QPixmap для избежания повторных аллокаций
        if self.cached_pixmap is None or self.last_size != size:
            self.cached_pixmap = QPixmap(size)
            self.last_size = size

        self.cached_pixmap.fill(Qt.transparent)

        painter = QPainter(self.cached_pixmap)

        # Процедурные трансформации в зависимости от состояния
        self.frame_counter += 1

        painter.save()

        # Центрирование для вращений
        painter.translate(size.width() / 2, size.height() / 2)

        # Слежение глазами (смещение всего котика в сторону курсора)
        # Оптимизация: используем кешированную позицию мыши относительно окна
        # Рассчитываем смещение на основе глобальных координат, чтобы избежать mapFromGlobal в каждом кадре
        if not self.main_window:
            self.main_window = self.label.window()

        if self.main_window and hasattr(self.main_window, 'get_cached_pos'):
            pet_pos = self.main_window.get_cached_pos()
            local_mouse_x = self.last_mouse_pos[0] - pet_pos.x()
            local_mouse_y = self.last_mouse_pos[1] - pet_pos.y()
        else:
            # Fallback к стандартному методу, если окно не поддерживает кэширование
            local_mouse = self.label.mapFromGlobal(self.label.cursor().pos())
            local_mouse_x = local_mouse.x()
            local_mouse_y = local_mouse.y()

        look_x = (local_mouse_x - size.width()/2) / size.width() * 5
        look_y = (local_mouse_y - size.height()/2) / size.height() * 5
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
        elif self.current_state == "eating":
            # Наклоны головы вперед-назад при еде
            scale_y = 1.0 + 0.1 * abs(math.sin(self.frame_counter * 0.8))
            painter.translate(0, 10 * (scale_y - 1.0))
            painter.scale(1.0, scale_y)
        elif self.current_state == "thinking":
            # Наклон + покачивание
            painter.rotate(10 + 5 * math.sin(self.frame_counter * 0.2))
        elif self.current_state == "playing":
            # Покачивание и подпрыгивание
            angle = 8 * math.sin(self.frame_counter * 0.6)
            painter.rotate(angle)
            painter.translate(0, -abs(8 * math.sin(self.frame_counter * 0.6)))
        elif self.current_state == "shaking":
            # Сильное встряхивание с динамическим изменением масштаба
            scale = 1.0 + 0.1 * math.sin(self.frame_counter * 0.9)
            painter.scale(scale, scale)
            painter.translate(random.randint(-5, 5), random.randint(-5, 5))

        painter.translate(-size.width() / 2, -size.height() / 2)

        self.svg_renderer.render(painter)
        painter.restore()
        painter.end()

        self.label.setPixmap(self.cached_pixmap)

    def play_state(self, state, force=False):
        # Оптимизация: не перезапускаем то же самое состояние, если не требуется принудительно
        if not force and self.current_state == state and self.current_anim_path:
            return

        self.current_state = state

        # Установка FPS на основе состояния
        if state == "sleeping":
            self.current_fps = 4
        elif state in ["overheat", "shaking"]:
            self.current_fps = 20
        else:
            self.current_fps = 12

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
        if self.skin == skin_name:
            return

        self.skin = skin_name
        if self.config:
            self.config.set("skin", skin_name)

        # Сбрасываем путь текущей анимации, чтобы принудительно загрузить новый скин
        self.current_anim_path = None
        self.play_state(self.current_state, force=True)

    def set_mouse_pos(self, x, y):
        self.last_mouse_pos = (x, y)
        self.last_mouse_pos_qpoint = QPoint(x, y)
