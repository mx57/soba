import time
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout, QScrollArea, QWidget, QTabWidget
from PySide6.QtCore import Qt, QTimer
from src.utils.bonding_utils import get_level_info, ACHIEVEMENTS
from datetime import datetime, timezone

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

        # Инициализируем значения
        self.update_progress_ui()
        self.update_history_ui()

        # Таймер для обновления UI в реальном времени
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(500) # Обновление каждые 500мс

        # Кнопки управления
        btn_layout = QHBoxLayout()

        self.reset_btn = QPushButton("Сбросить прогресс")
        self.reset_btn.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.reset_btn.clicked.connect(self.confirm_reset)
        btn_layout.addWidget(self.reset_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        main_layout.addLayout(btn_layout)

    def update_ui(self):
        self.update_progress_ui()
        if self.tabs.currentIndex() == 1:
            self.update_history_ui()

    def confirm_reset(self):
        from PySide6.QtWidgets import QMessageBox

        reply = QMessageBox.question(
            self,
            "Сбросить прогресс",
            "Вы уверены, что хотите полностью сбросить весь прогресс, достижения и историю активности? Это действие необратимо.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        # Находим и сбрасываем менеджер ввода, если он доступен
        im = None
        if self.parent() and hasattr(self.parent(), 'input_manager') and self.parent().input_manager:
            im = self.parent().input_manager

        if im:
            im.reset_all_data()
        else:
            self.db.reset_all_data()

        # Очищаем кэш истории
        self.last_events_cache = []

        # Мгновенно перерисовываем обе вкладки диалога
        self.update_progress_ui()
        self.update_history_ui()

        QMessageBox.information(
            self,
            "Сброс выполнен",
            "Весь игровой прогресс и статистика успешно сброшены.",
            QMessageBox.Ok
        )

    def setup_progress_tab(self, widget):
        layout = QVBoxLayout(widget)

        # Заголовок
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(self.title_label)

        # Общие очки и KPS в одной строке
        stats_row = QHBoxLayout()
        self.points_label = QLabel()
        self.points_label.setStyleSheet("font-weight: bold; font-size: 12px;")

        self.kps_label = QLabel()
        self.kps_label.setStyleSheet("color: #555; font-size: 11px;")

        stats_row.addWidget(self.points_label)
        stats_row.addStretch()
        stats_row.addWidget(self.kps_label)
        layout.addLayout(stats_row)

        # Прогресс бар
        self.next_level_label = QLabel()
        layout.addWidget(self.next_level_label)

        self.level_progress_bar = QProgressBar()
        self.level_progress_bar.setFormat("%v / %m")
        layout.addWidget(self.level_progress_bar)

        layout.addSpacing(10)
        layout.addWidget(QLabel("<b>Достижения:</b>"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(5, 5, 5, 5)

        self.achievement_widgets = {}

        for ach_id, ach_info in ACHIEVEMENTS.items():
            ach_widget = QWidget()
            ach_item_layout = QHBoxLayout(ach_widget)
            ach_item_layout.setContentsMargins(0, 0, 0, 0)

            icon_label = QLabel()
            ach_item_layout.addWidget(icon_label)

            ach_text_layout = QVBoxLayout()
            info_label = QLabel()
            ach_text_layout.addWidget(info_label)

            prog_bar = None
            if 'goal' in ach_info and ach_info['goal'] > 0:
                prog_bar = QProgressBar()
                prog_bar.setMaximum(ach_info['goal'])
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

            self.achievement_widgets[ach_id] = {
                'icon_label': icon_label,
                'info_label': info_label,
                'prog_bar': prog_bar,
                'widget': ach_widget
            }

        scroll.setWidget(scroll_content)
        scroll.setFixedHeight(200)
        layout.addWidget(scroll)

    def update_progress_ui(self):
        # Получаем данные о привязанности и KPS
        im = None
        if self.parent() and hasattr(self.parent(), 'input_manager') and self.parent().input_manager:
            im = self.parent().input_manager

        if im:
            points = im.last_affection_points + im.pending_points
            max_kps = im.max_kps
        else:
            points = self.db.get_affection_points()
            max_kps = self.db.get_stat("max_kps")

        level, title, points_in_level, points_for_next_level = get_level_info(points)

        # Обновляем основные метки
        self.title_label.setText(f"Уровень {level}: {title}")
        self.points_label.setText(f"Всего: {points} ❤️")
        self.kps_label.setText(f"Рекорд: {max_kps} кл/сек ⚡")

        # Обновляем прогресс-бар уровня
        if points_for_next_level > 0:
            self.next_level_label.setText(f"До следующего уровня: {points_for_next_level - points_in_level}")
            self.level_progress_bar.setVisible(True)
            self.level_progress_bar.setMaximum(points_for_next_level)
            self.level_progress_bar.setValue(points_in_level)
        else:
            self.next_level_label.setText("Максимальный уровень достигнут! 🎉")
            self.level_progress_bar.setVisible(False)

        # Получаем разблокированные достижения
        if im:
            unlocked = im.unlocked_achievements
        else:
            unlocked = self.db.get_unlocked_achievements()

        # Обновляем виджеты достижений
        for ach_id, ach_info in ACHIEVEMENTS.items():
            ref = self.achievement_widgets[ach_id]
            is_unlocked = ach_id in unlocked

            # Иконка
            icon = ach_info['icon'] if is_unlocked else "🔒"
            ref['icon_label'].setText(f"<span style='font-size: 20px;'>{icon}</span>")

            # Текущее значение прогресса
            current_val = 0
            if 'stat' in ach_info:
                stat_name = ach_info['stat']
                if stat_name == 'level':
                    current_val = level
                elif stat_name == 'bonding_points':
                    current_val = points
                elif stat_name == 'total_clicks':
                    current_val = im.total_clicks_cache + im.pending_stats.get('total_clicks', 0) if im else self.db.get_stat('total_clicks')
                elif stat_name == 'max_kps':
                    current_val = max_kps
                else:
                    current_val = self.db.get_stat(stat_name) + (im.pending_stats.get(stat_name, 0) if im else 0)

            # Текст с прогрессом
            progress_text = ""
            if not is_unlocked and 'goal' in ach_info and ach_info['goal'] > 0:
                progress_text = f" <span style='color: #888;'>({current_val}/{ach_info['goal']})</span>"

            info_text = f"<b>{ach_info['title']}</b>{progress_text}<br/><small>{ach_info['desc']}</small>"
            ref['info_label'].setText(info_text)

            if is_unlocked:
                ref['info_label'].setStyleSheet("")
                if ref['prog_bar']:
                    ref['prog_bar'].setVisible(False)
            else:
                ref['info_label'].setStyleSheet("color: #888;")
                if ref['prog_bar']:
                    ref['prog_bar'].setVisible(True)
                    ref['prog_bar'].setValue(min(current_val, ach_info['goal']))

    def setup_history_tab(self, widget):
        layout = QVBoxLayout(widget)

        self.history_scroll = QScrollArea()
        self.history_scroll.setWidgetResizable(True)
        self.history_content = QWidget()
        self.history_layout = QVBoxLayout(self.history_content)
        self.history_layout.setAlignment(Qt.AlignTop)

        self.history_scroll.setWidget(self.history_content)
        layout.addWidget(self.history_scroll)

        self.last_events_cache = []

    def update_history_ui(self):
        events = self.db.get_recent_activity(30)
        # Оптимизация: не перерисовываем историю, если события не изменились
        if events == self.last_events_cache:
            return
        self.last_events_cache = events

        # Очищаем старые элементы истории
        while self.history_layout.count() > 0:
            item = self.history_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        type_icons = {
            "app_start": "🚀",
            "level_up": "🆙",
            "achievement": "🏆",
            "pomodoro_start": "⏱️",
            "feeding": "🐟"
        }

        if not events:
            no_events_label = QLabel("История событий пуста...")
            self.history_layout.addWidget(no_events_label)
            return

        for ev in events:
            # ev format: (id, timestamp, event_type, description)
            ts_str = ev[1]
            try:
                # Попытка форматировать время для красоты (SQLite хранит в UTC обычно)
                dt_utc = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                # Конвертация UTC времени из базы в локальное время системы автоматически
                dt_local = dt_utc.astimezone(None)
                time_display = dt_local.strftime("%H:%M")
            except Exception:
                time_display = ts_str

            icon = type_icons.get(ev[2], "📝")

            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 5, 0, 5)

            label = QLabel(f"<span style='color: #888; font-size: 10px;'>{time_display}</span> {icon} {ev[3]}")
            label.setWordWrap(True)
            item_layout.addWidget(label)

            self.history_layout.addWidget(item)

            # Разделитель
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #eee;")
            self.history_layout.addWidget(line)
