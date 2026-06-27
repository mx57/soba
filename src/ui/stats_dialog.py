from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from src.utils.bonding_utils import get_level_info

class StatsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Статистика привязанности")
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)

        points = self.db.get_affection_points()
        level, title, points_in_level, points_for_next_level = get_level_info(points)

        # Заголовок
        title_label = QLabel(f"Уровень {level}: {title}")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Общие очки
        points_label = QLabel(f"Всего очков: {points} ❤️")
        points_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(points_label)

        # Прогресс бар
        if points_for_next_level > 0:
            layout.addWidget(QLabel(f"До следующего уровня: {points_for_next_level - points_in_level}"))
            progress = QProgressBar()
            progress.setMaximum(points_for_next_level)
            progress.setValue(points_in_level)
            progress.setFormat("%v / %m")
            layout.addWidget(progress)
        else:
            layout.addWidget(QLabel("Максимальный уровень достигнут! 🎉"))

        layout.addSpacing(20)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
