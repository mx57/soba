from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QProgressBar,
                             QPushButton, QHBoxLayout, QScrollArea, QWidget,
                             QTabWidget, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt
from src.utils.bonding_utils import get_level_info, ACHIEVEMENTS

class StatsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Статистика Котика")
        self.setFixedWidth(350)
        self.setFixedHeight(500)

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладка Прогресса
        self.progress_tab = QWidget()
        self.setup_progress_tab()
        self.tabs.addTab(self.progress_tab, "Прогресс")

        # Вкладка Истории
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.history_tab, "История")

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)

    def setup_progress_tab(self):
        layout = QVBoxLayout(self.progress_tab)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладка 1: Прогресс и Достижения
        self.progress_tab = QWidget()
        self.setup_progress_tab()
        self.tabs.addTab(self.progress_tab, "🎯 Прогресс")

        # Вкладка 2: История активности
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tabs.addTab(self.history_tab, "📜 История")

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def setup_progress_tab(self):
        layout = QVBoxLayout(self.progress_tab)

        points = self.db.get_affection_points()
        level, title, points_in_level, points_for_next_level = get_level_info(points)

        # Заголовок
        title_label = QLabel(f"Уровень {level}: {title}")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(title_label)

        # Общие очки и KPS в одной строке
        stats_row = QHBoxLayout()
        points_label = QLabel(f"Всего: {points} ❤️")

        max_kps = self.db.get_stat("max_kps")
        kps_label = QLabel(f"Рекорд скорости: {max_kps} кл/сек ⚡")
        kps_label.setAlignment(Qt.AlignCenter)
        kps_label.setStyleSheet("color: #555; font-size: 11px; margin-bottom: 5px;")
        layout.addWidget(kps_label)

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

        layout.addSpacing(10)
        layout.addWidget(QLabel("<b>Достижения:</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(5, 5, 5, 5)

        unlocked = self.db.get_unlocked_achievements()

        for ach_id, ach_info in ACHIEVEMENTS.items():
            ach_widget = QWidget()
            ach_item_layout = QHBoxLayout(ach_widget)
            ach_item_layout.setContentsMargins(0, 0, 0, 0)

            is_unlocked = ach_id in unlocked
            icon = ach_info['icon'] if is_unlocked else "🔒"

            label_text = f"<span style='font-size: 20px;'>{icon}</span>"
            item_label = QLabel(label_text)
            ach_item_layout.addWidget(item_label)

            # Расчет прогресса
            progress_text = ""
            if not is_unlocked and 'goal' in ach_info and 'stat' in ach_info:
                if self.parent() and hasattr(self.parent(), 'input_manager') and self.parent().input_manager:
                    im = self.parent().input_manager
                    if ach_info['stat'] == 'bonding_points':
                        current_val = im.last_affection_points + im.pending_points
                    elif ach_info['stat'] == 'total_clicks':
                        current_val = im.total_clicks_cache + im.pending_stats.get('total_clicks', 0)
                    elif ach_info['stat'] == 'max_kps':
                        current_val = im.max_kps
                    else:
                        current_val = self.db.get_stat(ach_info['stat']) + im.pending_stats.get(ach_info['stat'], 0)
                else:
                    current_val = self.db.get_stat(ach_info['stat'])

                if ach_info['stat'] == 'level':
                    current_val, _, _, _ = get_level_info(points)

                goal = ach_info['goal']
                if goal > 0:
                    progress_text = f" <span style='color: #888;'>({current_val}/{goal})</span>"

            info_label = QLabel(f"<b>{ach_info['title']}</b>{progress_text}<br/><small>{ach_info['desc']}</small>")
            if not is_unlocked:
                info_label.setStyleSheet("color: #888;")
            ach_item_layout.addWidget(info_label)
            ach_item_layout.addStretch()

            scroll_layout.addWidget(ach_widget)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def setup_history_tab(self):
        layout = QVBoxLayout(self.history_tab)

        layout.addWidget(QLabel("<b>Последние события:</b>"))

        self.history_list = QListWidget()

        events = self.db.get_recent_activity(30)
        for event in events:
            # event = (id, timestamp, event_type, description)
            _, timestamp, event_type, desc = event

            # Красивое форматирование времени (убираем секунды)
            time_str = timestamp.split(' ')[1][:5] if ' ' in timestamp else timestamp

            icon = "ℹ️"
            if event_type == "level_up": icon = "🆙"
            elif event_type == "achievement": icon = "🏆"
            elif event_type == "feeding": icon = "🐟"
            elif event_type == "pomodoro_start": icon = "⏱"
            elif event_type == "app_start": icon = "🚀"

            item_text = f"[{time_str}] {icon} {desc if desc else event_type}"
            item = QListWidgetItem(item_text)
            self.history_list.addItem(item)

        layout.addWidget(self.history_list)

        if not events:
            layout.addWidget(QLabel("История пока пуста..."))
