import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt, QPoint, QSize, Signal, QPropertyAnimation, QEasingCurve, QTimer
from src.core.animation_manager import AnimationManager
from src.utils.sound_manager import SoundManager

class PetWindow(QMainWindow):
    closed = Signal()

    def __init__(self, config_manager=None):
        super().__init__()
        self.config = config_manager

        # Настройка прозрачного и безрамочного окна
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

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

        self.last_state_before_drag = "idle"

        self.drag_position = QPoint()
        self.last_drag_global_pos = QPoint()
        self.is_dragging = False
        self.shake_count = 0
        self.original_size = QSize(100, 100)

        # Начальный размер
        self.resize(self.original_size)

        self.sound_manager = SoundManager(self.config)

        # Анимация для перемещения окна (охота)
        self.pos_animation = QPropertyAnimation(self, b"pos")
        self.pos_animation.setEasingCurve(QEasingCurve.OutQuad)

        self.is_hidden = False
        self.original_pos = self.pos()
        self.timer_system = None

    def set_timer_system(self, timer_system):
        self.timer_system = timer_system

    def toggle_peek_mode(self):
        """Уход котика за край экрана и возвращение"""
        screen = self.screen().geometry()
        self.pos_animation.stop()
        self.pos_animation.setDuration(1000)

        if not self.is_hidden:
            self.original_pos = self.pos()
            # Прячемся за правый край
            dest = QPoint(screen.width() - 20, self.y())
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

        self.pos_animation.stop()
        self.pos_animation.setDuration(500)
        self.pos_animation.setEndValue(QPoint(dest_x, dest_y))
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
        self.sound_manager.play_sound("meow")
        QTimer.singleShot(duration, self.message_label.hide)


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

            # Детекция встряхивания (shaking)
            if not self.last_drag_global_pos.isNull():
                drag_delta = curr_global_pos - self.last_drag_global_pos
                if drag_delta.manhattanLength() > 50: # Резкое движение
                    self.shake_count += 1
                    if self.shake_count > 5:
                        self.animation_manager.play_state("shaking")

            self.last_drag_global_pos = curr_global_pos

            # Эффект Mochi Drag (растягивание при движении)
            diff = curr_global_pos - (self.pos() + self.drag_position)

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
