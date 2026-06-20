import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtCore import Qt, QPoint, QSize, Signal
from src.core.animation_manager import AnimationManager

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

        self.animation_manager = AnimationManager(self.pet_label)
        self.animation_manager.play_state("idle")

        self.last_state_before_drag = "idle"

        self.drag_position = QPoint()
        self.is_dragging = False
        self.original_size = QSize(100, 100)

        # Начальный размер
        self.resize(self.original_size)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.is_dragging = True
            self.last_state_before_drag = self.animation_manager.current_state
            self.animation_manager.play_state("stretching")
            event.accept()

    def mouseMoveEvent(self, event):
        if event.button() == Qt.LeftButton or self.is_dragging:
            # Эффект Mochi Drag (растягивание при движении)
            curr_pos = event.globalPosition().toPoint()
            diff = curr_pos - (self.pos() + self.drag_position)

            # Программное растягивание окна
            stretch_factor = 1 + (abs(diff.x()) + abs(diff.y())) / 500
            new_width = int(self.original_size.width() * stretch_factor)
            new_height = int(self.original_size.height() * (1 / stretch_factor if stretch_factor > 0 else 1))

            self.resize(new_width, max(50, new_height))
            self.animation_manager.update_size(self.size())
            self.move(curr_pos - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
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
