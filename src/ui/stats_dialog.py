from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout, QTabWidget, QWidget, QScrollArea
from PySide6.QtCore import Qt
from src.utils.bonding_utils import get_level_info, get_achievements

class StatsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Прогресс и Достижения")
        self.resize(350, 450)

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self.setup_overview_tab()
        self.setup_achievements_tab()

        main_layout.addWidget(self.tabs)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)

    def setup_overview_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        points = self.db.get_affection_points()
        level, title, points_in_level, points_for_next_level = get_level_info(points)
        mice = self.db.get_stat("mice_caught")
        fed = self.db.get_stat("times_fed")
        work_sec = self.db.get_stat("total_work_seconds")

        # Форматирование времени
        h = int(work_sec // 3600)
        m = int((work_sec % 3600) // 60)
        s = int(work_sec % 60)
        work_time_str = f"{h:02d}:{m:02d}:{s:02d}"

        # Уровень
        level_label = QLabel(f"Уровень {level}: {title}")
        level_label.setAlignment(Qt.AlignCenter)
        level_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(level_label)

        # Прогресс бар
        if points_for_next_level > 0:
            layout.addWidget(QLabel(f"Прогресс уровня:"))
            progress = QProgressBar()
            progress.setMaximum(points_for_next_level)
            progress.setValue(points_in_level)
            progress.setFormat("%v / %m")
            layout.addWidget(progress)
        else:
            layout.addWidget(QLabel("Максимальный уровень достигнут! 🎉"))

        layout.addSpacing(20)

        # Доп. статистика
        stats_group = QWidget()
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.addWidget(QLabel(f"<b>Всего привязанности:</b> {points} ❤️"))
        stats_layout.addWidget(QLabel(f"<b>Поймано мышек:</b> {mice} 🐭"))
        stats_layout.addWidget(QLabel(f"<b>Покормлено раз:</b> {fed} 🍖"))
        stats_layout.addWidget(QLabel(f"<b>Время совместной работы:</b> {work_time_str} ⏱"))
        layout.addWidget(stats_group)

        layout.addStretch()
        self.tabs.addTab(tab, "Обзор")

    def setup_achievements_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)

        achievements = get_achievements(self.db)
        for title, desc, unlocked in achievements:
            item = QWidget()
            item_layout = QVBoxLayout(item)

            title_label = QLabel(f"{'✅' if unlocked else '🔒'} {title}")
            title_label.setStyleSheet(f"font-weight: bold; color: {'#27ae60' if unlocked else '#7f8c8d'};")
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("font-size: 11px; color: #34495e;")

            item_layout.addWidget(title_label)
            item_layout.addWidget(desc_label)
            item.setStyleSheet("border-bottom: 1px solid #ecf0f1; padding: 5px;")
            layout.addWidget(item)

        layout.addStretch()
        scroll.setWidget(content)
        self.tabs.addTab(scroll, "Награды")
