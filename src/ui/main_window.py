import sys
import time
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt, QPoint, QSize, Signal, QPropertyAnimation, QEasingCurve, QTimer
from src.core.animation_manager import AnimationManager
from src.utils.sound_manager import SoundManager
from src.utils.bonding_utils import get_level_info

class PetWindow(QMainWindow):
    closed = Signal()

    def __init__(self, config_manager=None):
        super().__init__()
        self.config = config_manager
        self.input_manager = None

        # Настройка прозрачного и безрамочного окна
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self.config is None or self.config.get("always_on_top"):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(self.config.get("opacity") / 100.0 if self.config else 1.0)

        # Основной виджет для отображения котика
        self.pet_label = QLabel(self)
        self.pet_label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self.pet_label)

        # Сообщения над котиком
        self.message_label = QLabel(self)
        self.message_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #555;
                border-radius: 10px;
                padding: 5px;
                font-weight: bold;
            }
        """)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.hide()

        self.animation_manager = AnimationManager(self.pet_label, self.config)
        self.animation_manager.play_state("idle")

        # Применяем прозрачность из конфига
        if self.config:
            self.set_opacity(self.config.get("opacity"))

        self.last_state_before_drag = "idle"

        self.drag_position = QPoint()
        self.last_drag_global_pos = QPoint()
        self.is_dragging = False
        self.shake_count = 0
        self.last_shake_time = 0
        pet_size = self.config.get("pet_size") if self.config else 100
        self.original_size = QSize(pet_size, pet_size)

        # Начальный размер
        self.resize(self.original_size)

        self.sound_manager = SoundManager(self.config)

        # Анимация для перемещения окна (охота)
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setEasingCurve(QEasingCurve.OutQuad)

        self.is_hidden = False
        self.original_pos = self.pos()
        self._cached_pos = self.pos()
        self.timer_system = None
        self.last_meow_time = 0

        # Таймер для скрытия сообщений
        self.message_hide_timer = QTimer(self)
        self.message_hide_timer.setSingleShot(True)
        self.message_hide_timer.timeout.connect(self.message_label.hide)

        # Настраиваем дефолтный пустой тултип для активации событий наведения мыши
        self.setToolTip("Загрузка...")

    def moveEvent(self, event):
        self._cached_pos = event.pos()
        super().moveEvent(event)

    def get_cached_pos(self):
        return self._cached_pos

    def set_opacity(self, value):
        """Устанавливает прозрачность окна (0-100)"""
        self.setWindowOpacity(value / 100.0)

    def set_pet_size(self, size):
        """Устанавливает базовый размер питомца и обновляет окно."""
        if self.config:
            self.config.set("pet_size", size)
        self.original_size = QSize(size, size)
        self.resize(self.original_size)
        self.animation_manager.update_size(self.size())

    def set_always_on_top(self, enabled):
        """Включает или выключает режим 'Поверх всех окон' динамически"""
        if self.config:
            self.config.set("always_on_top", enabled)

        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowStaysOnTopHint

        is_visible = self.isVisible()
        self.setWindowFlags(flags)
        if is_visible:
            self.show()

    def set_timer_system(self, timer_system):
        self.timer_system = timer_system

    def update_tooltip(self):
        """Интерактивное обновление тултипа."""
        if not self.input_manager:
            return

        username = self.config.get("username") if self.config else "Пользователь"

        # Виртуальные (актуальные в памяти) очки привязанности
        virtual_points = self.input_manager.last_affection_points + self.input_manager.pending_points
        level, title, _, _ = get_level_info(virtual_points)

        # Рекорд KPS
        max_kps = self.input_manager.max_kps

        # Pomodoro таймер
        pomodoro_text = "Таймер не запущен"
        if self.timer_system and self.timer_system.pomodoro_state != "idle":
            state = "Работа" if self.timer_system.pomodoro_state == "work" else "Отдых"
            remaining = self.timer_system.pomodoro_remaining
            mins, secs = divmod(remaining, 60)
            pomodoro_text = f"{state}: {mins:02d}:{secs:02d}"

        tooltip_text = (
            f"Хозяин: {username}\n"
            f"Уровень {level}: {title} ({virtual_points} ❤️)\n"
            f"Рекорд кликов: {max_kps} кл/сек ⚡\n"
            f"Pomodoro: {pomodoro_text}"
        )
        self.setToolTip(tooltip_text)

    def toggle_peek_mode(self):
        """Уход котика за край экрана и возвращение"""
        screen = self.screen().geometry()
        self.pos_animation.stop()
        self.pos_animation.setDuration(1000)

        if not self.is_hidden:
            self.original_pos = self._cached_pos
            # Прячемся за правый край
            dest = QPoint(screen.width() - 20, self._cached_pos.y())
            self.is_hidden = True
        else:
            dest = self.original_pos
            self.is_hidden = False

        self.pos_animation.setEndValue(dest)
        self.pos_animation.start()

    def start_hunting(self, target_x, target_y):
        """Плавное перемещение котика к курсору"""
        if self.is_dragging:
            return

        # Целевая позиция (центр котика на курсоре)
        dest_x = target_x - self.width() // 2
        dest_y = target_y - self.height() // 2
        dest_point = QPoint(dest_x, dest_y)

        # Если уже движемся к этой точке, не перезапускаем
        if self.pos_animation.state() == QPropertyAnimation.Running and self.pos_animation.endValue() == dest_point:
            return

        # Проверка "поимки" (порог масштабируется в зависимости от размера окна)
        curr_pos = self.get_cached_pos()
        dx = curr_pos.x() - dest_x
        dy = curr_pos.y() - dest_y
        dist_sq = dx * dx + dy * dy
        catch_threshold_sq = (self.width() * 0.1) ** 2
        if dist_sq < catch_threshold_sq:
            if self.animation_manager.current_state == "hunting":
                self.animation_manager.play_state("happy")
                self.show_message("Поймал! 🐾")
                if self.input_manager:
                    self.input_manager.add_points(2)
                    self.input_manager.pending_stats["cursor_catches"] += 1
                    self.input_manager.check_for_achievements()
            return
        else:
            # Если лазер/курсор ушел дальше, а котик все еще радовался — возвращаем режим охоты
            if self.animation_manager.current_state == "happy":
                self.animation_manager.play_state("hunting")

        self.pos_animation.stop()
        self.pos_animation.setDuration(500)
        self.pos_animation.setEndValue(dest_point)
        self.pos_animation.start()

    def show_message(self, text, duration=3000):
        """Отображение всплывающего сообщения над котиком"""
        self.message_label.setText(text)
        self.message_label.adjustSize()
        # Позиционируем над котиком
        self.message_label.move(
            (self.width() - self.message_label.width()) // 2,
            0
        )
        self.message_label.show()

        now = time.time()
        if now - self.last_meow_time > 2.0:
            self.sound_manager.play_sound("meow")
            self.last_meow_time = now

        self.message_hide_timer.stop()
        self.message_hide_timer.start(duration)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.is_dragging = True
            self.last_state_before_drag = self.animation_manager.current_state
            self.animation_manager.play_state("stretching")
            event.accept()

    def mouseMoveEvent(self, event):
        if event.button() == Qt.LeftButton or self.is_dragging:
            curr_global_pos = event.globalPosition().toPoint()
            current_time = time.time()

            # Детекция встряхивания (shaking) - оптимизированная
            if not self.last_drag_global_pos.isNull():
                drag_delta = curr_global_pos - self.last_drag_global_pos
                if drag_delta.manhattanLength() > 60: # Более резкое движение
                    # Если прошло больше 500мс с прошлого резкого движения, сбрасываем счетчик
                    if current_time - self.last_shake_time > 0.5:
                        self.shake_count = 0

                    self.shake_count += 1
                    self.last_shake_time = current_time

                    if self.shake_count > 4: # 5 резких движений подряд
                        if self.animation_manager.current_state != "shaking":
                            self.animation_manager.play_state("shaking")
                            self.show_message("Ой, голова кружится! 🌪️")
                            if self.input_manager:
                                self.input_manager.add_shake()

            self.last_drag_global_pos = curr_global_pos

            # Эффект Mochi Drag (растягивание при движении)
            diff = curr_global_pos - (self._cached_pos + self.drag_position)

            # Более органичное растягивание (ограниченное и плавное)
            stretch_x = min(2.0, 1.0 + abs(diff.x()) / 200)
            stretch_y = min(2.0, 1.0 + abs(diff.y()) / 200)

            new_width = int(self.original_size.width() * stretch_x)
            new_height = int(self.original_size.height() * (1 / stretch_y if stretch_y > 0 else 1))

            # Если тянем в основном по Y, то сужаем по X
            if abs(diff.y()) > abs(diff.x()):
                new_width = int(self.original_size.width() * (1 / stretch_y))
                new_height = int(self.original_size.height() * stretch_y)

            self.resize(new_width, max(40, new_height))
            self.animation_manager.update_size(self.size())
            self.move(curr_global_pos - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.shake_count = 0
        self.last_drag_global_pos = QPoint()
        self.resize(self.original_size) # Возвращаем размер
        self.animation_manager.update_size(self.size())
        self.animation_manager.play_state(self.last_state_before_drag)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PetWindow()
    window.show()
    sys.exit(app.exec())
