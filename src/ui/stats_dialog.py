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

        # Переменные для отслеживания состояния вкладок и истории
        self.last_max_activity_id = 0
        self.ach_widgets_cache = {}

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

        # Таймер real-time обновлений (каждые 500мс)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_realtime_data)
        self.update_timer.start(500)

    def setup_progress_tab(self, widget):
        layout = QVBoxLayout(widget)

        points = self.db.get_affection_points()
        if self.parent() and hasattr(self.parent(), 'input_manager') and self.parent().input_manager:
            im = self.parent().input_manager
            points = im.last_affection_points + im.pending_points
            max_kps = im.max_kps
        else:
            max_kps = self.db.get_stat("max_kps")

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

        self.kps_label = QLabel(f"Рекорд: {max_kps} кл/сек ⚡")
        self.kps_label.setStyleSheet("color: #555; font-size: 11px;")

        stats_row.addWidget(self.points_label)
        stats_row.addStretch()
        stats_row.addWidget(self.kps_label)
        layout.addLayout(stats_row)

        # Прогресс бар
        self.next_level_desc_label = QLabel()
        layout.addWidget(self.next_level_desc_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%v / %m")
        layout.addWidget(self.progress_bar)

        # Обновляем прогресс-бар в первый раз
        self._update_progress_bar_widget(points_in_level, points_for_next_level)

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
            goal = ach_info.get('goal', 0)
            if 'stat' in ach_info:
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

                if goal > 0:
                    progress_text = f" <span style='color: #888;'>({current_val}/{goal})</span>"

            info_label = QLabel(f"<b>{ach_info['title']}</b>{progress_text}<br/><small>{ach_info['desc']}</small>")
            if not is_unlocked:
                info_label.setStyleSheet("color: #888;")

            # Добавляем прогресс-бар для закрытых достижений
            ach_text_layout = QVBoxLayout()
            ach_text_layout.addWidget(info_label)

            prog_bar = None
            if not is_unlocked and goal > 0:
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

            # Сохраняем ссылки в кэш для real-time обновлений
            self.ach_widgets_cache[ach_id] = {
                "icon_label": item_label,
                "info_label": info_label,
                "progress_bar": prog_bar,
                "is_unlocked": is_unlocked
            }

        scroll.setWidget(scroll_content)
        scroll.setFixedHeight(200)
        layout.addWidget(scroll)

    def _update_progress_bar_widget(self, points_in_level, points_for_next_level):
        if points_for_next_level > 0:
            self.next_level_desc_label.setText(f"До следующего уровня: {points_for_next_level - points_in_level}")
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(points_for_next_level)
            self.progress_bar.setValue(points_in_level)
        else:
            self.next_level_desc_label.setText("Максимальный уровень достигнут! 🎉")
            self.progress_bar.setVisible(False)

    def setup_history_tab(self, widget):
        layout = QVBoxLayout(widget)

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_scroll_content = QWidget()
        self.history_scroll_layout = QVBoxLayout(self.history_scroll_content)
        self.history_scroll_layout.setAlignment(Qt.AlignTop)

        self.history_scroll.setWidget(self.history_scroll_content)
        layout.addWidget(self.history_scroll)

        # Выполняем первоначальное наполнение истории
        self.rebuild_history_list()

    def rebuild_history_list(self):
        # Очищаем старый layout истории
        while self.history_scroll_layout.count() > 0:
            item = self.history_scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        events = self.db.get_recent_activity(30)

        # Сохраняем максимальный ID для последующей проверки обновлений
        if events:
            self.last_max_activity_id = max(ev[0] for ev in events)
        else:
            self.last_max_activity_id = 0

        type_icons = {
            "app_start": "🚀",
            "level_up": "🆙",
            "achievement": "🏆",
            "pomodoro_start": "⏱️",
            "feeding": "🐟"
        }

        if not events:
            no_events_lbl = QLabel("История событий пуста...")
            self.history_scroll_layout.addWidget(no_events_lbl)
            return

        for ev in events:
            # ev format: (id, timestamp, event_type, description)
            ts_str = ev[1]
            try:
                dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
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

            self.history_scroll_layout.addWidget(item)

            # Разделитель
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #eee;")
            self.history_scroll_layout.addWidget(line)

    def update_realtime_data(self):
        """Регулярное real-time обновление данных статистики с минимизацией CPU нагрузки."""
        im = None
        if self.parent() and hasattr(self.parent(), 'input_manager') and self.parent().input_manager:
            im = self.parent().input_manager

        # 1. Получаем актуальные данные (учитывая буферы в памяти)
        if im:
            points = im.last_affection_points + im.pending_points
            max_kps = im.max_kps
        else:
            points = self.db.get_affection_points()
            max_kps = self.db.get_stat("max_kps")

        level, title, points_in_level, points_for_next_level = get_level_info(points)

        # 2. Быстрое обновление первой вкладки (Прогресс)
        self.title_label.setText(f"Уровень {level}: {title}")
        self.points_label.setText(f"Всего: {points} ❤️")
        self.kps_label.setText(f"Рекорд: {max_kps} кл/сек ⚡")
        self._update_progress_bar_widget(points_in_level, points_for_next_level)

        # 3. Обновление достижений
        unlocked = self.db.get_unlocked_achievements()

        for ach_id, ach_info in ACHIEVEMENTS.items():
            cache = self.ach_widgets_cache.get(ach_id)
            if not cache:
                continue

            # Определяем текущее значение статистики для достижения
            current_val = 0
            if 'stat' in ach_info:
                if im:
                    if ach_info['stat'] == 'bonding_points':
                        current_val = points
                    elif ach_info['stat'] == 'total_clicks':
                        current_val = im.total_clicks_cache + im.pending_stats.get('total_clicks', 0)
                    elif ach_info['stat'] == 'max_kps':
                        current_val = max_kps
                    else:
                        current_val = self.db.get_stat(ach_info['stat']) + im.pending_stats.get(ach_info['stat'], 0)
                else:
                    current_val = self.db.get_stat(ach_info['stat'])

                if ach_info['stat'] == 'level':
                    current_val = level

            goal = ach_info.get('goal', 0)
            is_unlocked = ach_id in unlocked

            # Если состояние достижения поменялось на разблокированное
            if is_unlocked and not cache["is_unlocked"]:
                cache["is_unlocked"] = True
                cache["icon_label"].setText(f"<span style='font-size: 20px;'>{ach_info['icon']}</span>")
                cache["info_label"].setText(f"<b>{ach_info['title']}</b><br/><small>{ach_info['desc']}</small>")
                cache["info_label"].setStyleSheet("")
                if cache["progress_bar"]:
                    cache["progress_bar"].deleteLater()
                    cache["progress_bar"] = None

            # Если достижение закрыто, обновляем прогресс
            elif not is_unlocked:
                progress_text = ""
                if goal > 0:
                    progress_text = f" <span style='color: #888;'>({current_val}/{goal})</span>"
                cache["info_label"].setText(f"<b>{ach_info['title']}</b>{progress_text}<br/><small>{ach_info['desc']}</small>")
                if cache["progress_bar"]:
                    cache["progress_bar"].setValue(min(current_val, goal))

        # 4. Сверхбыстрое O(1) обновление вкладки Истории при её активности
        if self.tabs.currentIndex() == 1: # Вкладка "История" активна
            # Проверяем, появились ли новые события в БД по MAX(id)
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT MAX(id) FROM activity_log")
            max_id_row = cursor.fetchone()
            current_max_id = max_id_row[0] if max_id_row and max_id_row[0] else 0

            if current_max_id > self.last_max_activity_id:
                # Найдено новое событие, пересобираем вкладку истории
                self.rebuild_history_list()
