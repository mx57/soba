import time
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout, QScrollArea, QWidget, QTabWidget
from PySide6.QtCore import Qt
from src.utils.bonding_utils import get_level_info, ACHIEVEMENTS
from datetime import datetime, timezone

from PySide6.QtCore import QTimer

class StatsDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Статистика Котика")
        self.setFixedWidth(320)

        # Список для обновления шкал прогресса заблокированных достижений на лету
        self.locked_progress_bars = {}

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Вкладка 1: Прогресс
        self.progress_tab = QWidget()
        self.setup_progress_tab(self.progress_tab)
        self.tabs.addTab(self.progress_tab, "Прогресс")

        # Вкладка 2: История
        history_tab = QWidget()
        self.setup_history_tab(history_tab)
        self.tabs.addTab(history_tab, "История")

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)

        # Таймер обновления данных в реальном времени
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_stats_live)
        self.update_timer.start(500)

    def setup_progress_tab(self, widget):
        layout = QVBoxLayout(widget)

        points = self.db.get_affection_points()
        if self.parent() and hasattr(self.parent(), 'input_manager') and self.parent().input_manager:
            points += self.parent().input_manager.pending_points
        level, title, points_in_level, points_for_next_level = get_level_info(points)

        # Заголовок
        self.title_label = QLabel(f"Уровень {level}: {title}")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(self.title_label)

        # Общие очки и KPS в одной строке
        stats_row = QHBoxLayout()
        self.points_label = QLabel(f"Всего: {points} ❤️")
        self.points_label.setStyleSheet("font-weight: bold; font-size: 12px;")

        max_kps = self.db.get_stat("max_kps")
        if self.parent() and hasattr(self.parent(), 'input_manager') and self.parent().input_manager:
            max_kps = max(max_kps, self.parent().input_manager.max_kps)
        self.kps_label = QLabel(f"Рекорд: {max_kps} кл/сек ⚡")
        self.kps_label.setStyleSheet("color: #555; font-size: 11px;")

        stats_row.addWidget(self.points_label)
        stats_row.addStretch()
        stats_row.addWidget(self.kps_label)
        layout.addLayout(stats_row)

        # Прогресс бар
        self.next_level_desc_label = QLabel()
        layout.addWidget(self.next_level_desc_label)
        self.level_progress = QProgressBar()
        layout.addWidget(self.level_progress)

        self._update_level_progress_visuals(points, points_in_level, points_for_next_level)

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
            current_val = 0
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
                # Сохраняем ссылку для обновления в реальном времени
                self.locked_progress_bars[ach_id] = (prog_bar, info_label, ach_info)

            ach_item_layout.addLayout(ach_text_layout)
            ach_item_layout.addStretch()

            scroll_layout.addWidget(ach_widget)

        scroll.setWidget(scroll_content)
        scroll.setFixedHeight(200)
        layout.addWidget(scroll)

    def _update_level_progress_visuals(self, points, points_in_level, points_for_next_level):
        if points_for_next_level > 0:
            self.next_level_desc_label.setText(f"До следующего уровня: {points_for_next_level - points_in_level}")
            self.level_progress.setMaximum(points_for_next_level)
            self.level_progress.setValue(points_in_level)
            self.level_progress.setFormat("%v / %m")
            self.level_progress.show()
        else:
            self.next_level_desc_label.setText("Максимальный уровень достигнут! 🎉")
            self.level_progress.hide()

    def update_stats_live(self):
        """Регулярно опрашивает менеджер ввода и БД для обновления прогресса на лету."""
        points = self.db.get_affection_points()
        max_kps = self.db.get_stat("max_kps")

        if self.parent() and hasattr(self.parent(), 'input_manager') and self.parent().input_manager:
            im = self.parent().input_manager
            points += im.pending_points
            max_kps = max(max_kps, im.max_kps)

        level, title, points_in_level, points_for_next_level = get_level_info(points)

        # 1. Обновляем заголовок уровня и общие очки/KPS
        self.title_label.setText(f"Уровень {level}: {title}")
        self.points_label.setText(f"Всего: {points} ❤️")
        self.kps_label.setText(f"Рекорд: {max_kps} кл/сек ⚡")

        # 2. Обновляем уровень прогресса
        self._update_level_progress_visuals(points, points_in_level, points_for_next_level)

        # 3. Обновляем шкалы прогресса для закрытых достижений
        unlocked = self.db.get_unlocked_achievements()
        for ach_id, (prog_bar, label, ach_info) in list(self.locked_progress_bars.items()):
            if ach_id in unlocked:
                # Если достижение было разблокировано прямо сейчас, мы могли бы перерисовать,
                # но для простоты и безопасности просто убираем его из отслеживания обновления
                del self.locked_progress_bars[ach_id]
                continue

            current_val = 0
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
                current_val = level

            goal = ach_info['goal']
            prog_bar.setValue(min(current_val, goal))

            progress_text = ""
            if goal > 0:
                progress_text = f" <span style='color: #888;'>({current_val}/{goal})</span>"
            label.setText(f"<b>{ach_info['title']}</b>{progress_text}<br/><small>{ach_info['desc']}</small>")

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
                dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                # Конвертация UTC времени из базы в локальное время системы автоматически
                dt_local = dt_utc.astimezone(None)
                time_display = dt_local.strftime("%H:%M")
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
