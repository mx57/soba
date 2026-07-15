from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout, QScrollArea, QWidget, QTabWidget
from PySide6.QtCore import Qt
from src.utils.bonding_utils import get_level_info, ACHIEVEMENTS
from datetime import datetime

class StatsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Статистика Котика")
        self.setFixedWidth(320)

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладка 1: Прогресс
        progress_tab = QWidget()
        self.setup_progress_tab(progress_tab)
        self.tabs.addTab(progress_tab, "Прогресс")

        # Вкладка 2: История
        history_tab = QWidget()
        self.setup_history_tab(history_tab)
        self.tabs.addTab(history_tab, "История")

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)

    def setup_progress_tab(self, widget):
        layout = QVBoxLayout(widget)

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

            # Добавляем прогресс-бар для закрытых достижений
            ach_text_layout = QVBoxLayout()
            ach_text_layout.addWidget(info_label)

            if not is_unlocked and 'goal' in ach_info and goal > 0:
                prog_bar = QProgressBar()
                prog_bar.setMaximum(goal)
                prog_bar.setValue(min(current_val, goal))
                prog_bar.setFixedHeight(10)
                prog_bar.setTextVisible(False)
                prog_bar.setStyleSheet("""
                    QProgressBar {
                        background-color: #eee;
                        border: none;
                        border-radius: 5px;
                    }
                    QProgressBar::chunk {
                        background-color: #4CAF50;
                        border-radius: 5px;
                    }
                """)
                ach_text_layout.addWidget(prog_bar)

            ach_item_layout.addLayout(ach_text_layout)
            ach_item_layout.addStretch()

            scroll_layout.addWidget(ach_widget)

        scroll.setWidget(scroll_content)
        scroll.setFixedHeight(200)
        layout.addWidget(scroll)

    def setup_history_tab(self, widget):
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignTop)

        events = self.db.get_recent_activity(30)

        type_icons = {
            "app_start": "🚀",
            "level_up": "🆙",
            "achievement": "🏆",
            "pomodoro_start": "⏱️",
            "feeding": "🐟"
        }

        if not events:
            scroll_layout.addWidget(QLabel("История событий пуста..."))

        for ev in events:
            # ev format: (id, timestamp, event_type, description)
            ts_str = ev[1]
            try:
                # Попытка форматировать время для красоты (SQLite хранит в UTC обычно)
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                time_display = dt.strftime("%H:%M")
            except:
                time_display = ts_str

            icon = type_icons.get(ev[2], "📝")

            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 5, 0, 5)

            label = QLabel(f"<span style='color: #888; font-size: 10px;'>{time_display}</span> {icon} {ev[3]}")
            label.setWordWrap(True)
            item_layout.addWidget(label)

            scroll_layout.addWidget(item)

            # Разделитель
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #eee;")
            scroll_layout.addWidget(line)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
