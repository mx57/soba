import os
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject
from src.utils.paths import TRAY_ICON_PATH, get_animation_path
from src.ui.settings_dialog import SettingsDialog
from src.ui.stats_dialog import StatsDialog
from src.utils.bonding_utils import CAT_SKINS

class TrayMenu(QObject):
    def __init__(self, pet_window):
        super().__init__()
        self.window = pet_window

        self.tray_icon = QSystemTrayIcon(self.window)
        self.tray_icon.setToolTip("Котик-помощник 🐾")

        # Используем статичную PNG иконку для трея
        if os.path.exists(TRAY_ICON_PATH):
            self.tray_icon.setIcon(QIcon(TRAY_ICON_PATH))
        else:
            self.tray_icon.setIcon(QIcon(get_animation_path("cat", "idle")))

        self.menu = QMenu()
        self.setup_menu()

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

        if self.window.timer_system:
            self.window.timer_system.pomodoro_tick.connect(self.on_pomodoro_tick)
            self.window.timer_system.pomodoro_finished.connect(self.on_pomodoro_finished)

    def setup_menu(self):
        # Действия с питомцем
        feed_action = QAction("Покормить", self)
        feed_action.triggered.connect(self.feed_pet)
        self.menu.addAction(feed_action)

        play_action = QAction("Поиграть", self)
        play_action.triggered.connect(lambda checked=False: self.window.animation_manager.play_state("playing"))
        self.menu.addAction(play_action)

        sleep_action = QAction("Уложить спать", self)
        sleep_action.triggered.connect(lambda checked=False: self.window.animation_manager.play_state("sleeping"))
        self.menu.addAction(sleep_action)

        self.menu.addSeparator()

        # Лазерная указка
        laser_action = QAction("Лазерная указка 🔴", self)
        laser_action.setCheckable(True)
        laser_action.triggered.connect(self.toggle_laser)
        self.menu.addAction(laser_action)

        self.menu.addSeparator()

        # Выбор скина
        skin_menu = QMenu("Выбрать окрас", self.menu)
        for skin_id, name in CAT_SKINS.items():
            action = QAction(name, self)
            action.triggered.connect(lambda checked=False, sid=skin_id: self.window.animation_manager.set_skin(sid))
            skin_menu.addAction(action)
        self.menu.addMenu(skin_menu)

        self.menu.addSeparator()

        # Pomodoro
        self.pomodoro_menu = QMenu("Таймер Pomodoro", self.menu)

        self.pomodoro_status_action = QAction("Активного таймера нет", self)
        self.pomodoro_status_action.setEnabled(False)
        self.pomodoro_menu.addAction(self.pomodoro_status_action)

        self.pomodoro_menu.addSeparator()

        self.start_work_action = QAction("Начать работу", self)
        self.start_work_action.triggered.connect(self.start_work_timer)
        self.pomodoro_menu.addAction(self.start_work_action)

        self.start_break_action = QAction("Перерыв", self)
        self.start_break_action.triggered.connect(self.start_break_timer)
        self.pomodoro_menu.addAction(self.start_break_action)

        self.stop_pomodoro_action = QAction("Остановить таймер", self)
        self.stop_pomodoro_action.triggered.connect(self.stop_pomodoro_timer)
        self.stop_pomodoro_action.setVisible(False)
        self.pomodoro_menu.addAction(self.stop_pomodoro_action)

        self.menu.addMenu(self.pomodoro_menu)

        # Обновляем тексты в меню на основе конфигурации
        self.update_pomodoro_menu_texts()

        self.menu.addSeparator()

        # Peek Mode (Прятки)
        peek_action = QAction("Спрятать котика", self)
        peek_action.triggered.connect(lambda checked=False: self.window.toggle_peek_mode())
        self.menu.addAction(peek_action)

        self.menu.addSeparator()

        # Статистика
        stats_action = QAction("Статистика", self)
        stats_action.triggered.connect(self.show_stats)
        self.menu.addAction(stats_action)

        # Настройки
        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(settings_action)

        self.menu.addSeparator()

        # Выход
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.quit_app)
        self.menu.addAction(quit_action)

    def update_pomodoro_menu_texts(self):
        work_mins = self.window.config.get("pomodoro_work")
        break_mins = self.window.config.get("pomodoro_break")
        self.start_work_action.setText(f"Начать работу ({work_mins} мин)")
        self.start_break_action.setText(f"Перерыв ({break_mins} мин)")

    def quit_app(self, checked=False):
        self.window.close()
        QApplication.instance().quit()

    def show_message(self, title, message):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)

    def start_work_timer(self, checked=False):
        if self.window.timer_system:
            self.window.timer_system.start_pomodoro("work")
            self.window.show_message("Пора работать! 🛠")
            if self.window.input_manager and self.window.input_manager.db:
                self.window.input_manager.db.log_event("pomodoro_start", "Начата сессия работы")

    def start_break_timer(self, checked=False):
        if self.window.timer_system:
            self.window.timer_system.start_pomodoro("break")
            self.window.show_message("Отдыхаем! ☕")
            if self.window.input_manager and self.window.input_manager.db:
                self.window.input_manager.db.log_event("pomodoro_start", "Начата сессия отдыха")

    def stop_pomodoro_timer(self, checked=False):
        if self.window.timer_system:
            self.window.timer_system.stop_pomodoro()
            self.window.show_message("Таймер остановлен ⏹️")
            if self.window.input_manager and self.window.input_manager.db:
                self.window.input_manager.db.log_event("pomodoro_stop", "Таймер Pomodoro остановлен пользователем")

    def on_pomodoro_tick(self, mode, remaining_seconds):
        if mode == "idle" or remaining_seconds <= 0:
            self.pomodoro_status_action.setText("Активного таймера нет")
            self.start_work_action.setVisible(True)
            self.start_break_action.setVisible(True)
            self.stop_pomodoro_action.setVisible(False)
            self.tray_icon.setToolTip("Котик-помощник 🐾")
        else:
            mins = remaining_seconds // 60
            secs = remaining_seconds % 60
            time_str = f"{mins:02d}:{secs:02d}"

            mode_name = "Работа" if mode == "work" else "Отдых"
            mode_icon = "🛠" if mode == "work" else "☕"

            self.pomodoro_status_action.setText(f"Идет сессия: {mode_name} ({time_str})")
            self.start_work_action.setVisible(False)
            self.start_break_action.setVisible(False)
            self.stop_pomodoro_action.setVisible(True)

            self.tray_icon.setToolTip(f"Котик работает {mode_icon} (Осталось: {time_str})" if mode == "work" else f"Котик отдыхает {mode_icon} (Осталось: {time_str})")

        # Обновляем тултип главного окна, если применимо
        if hasattr(self.window, 'update_tooltip'):
            self.window.update_tooltip()

    def on_pomodoro_finished(self, mode):
        self.on_pomodoro_tick("idle", 0)

    def show_settings(self, checked=False):
        dialog = SettingsDialog(self.window.config, self.window)
        if dialog.exec():
            # Обновляем скин и прозрачность в реальном времени
            self.window.animation_manager.set_skin(self.window.config.get("skin"))
            self.window.set_opacity(self.window.config.get("opacity"))
            # Обновляем тексты меню Pomodoro
            self.update_pomodoro_menu_texts()
            # Перезапускаем таймер растяжки с новым интервалом
            if self.window.timer_system:
                self.window.timer_system.restart_stretch_timer()
            self.window.show_message("Настройки сохранены! 💾")

    def show_stats(self, checked=False):
        if self.window.input_manager and self.window.input_manager.db:
            # Сбрасываем все накопленные данные перед показом
            self.window.input_manager.flush_all()
            dialog = StatsDialog(self.window.input_manager.db, self.window)
            dialog.exec()

    def feed_pet(self, checked=False):
        self.window.animation_manager.play_state("eating")
        if self.window.input_manager:
            self.window.input_manager.add_points(5)
            self.window.show_message("Мням! +5 ❤️")
            self.window.input_manager.pending_stats["total_feedings"] += 1
            if self.window.input_manager.db:
                self.window.input_manager.db.log_event("feeding", "Котик покормлен")
            self.window.input_manager.check_for_achievements()

    def toggle_laser(self, checked):
        if self.window.input_manager:
            is_active = self.window.input_manager.toggle_laser_mode()
            if is_active:
                self.show_message("Мини-игра", "Лазерная указка активирована! 🔴")
            else:
                self.show_message("Мини-игра", "Лазерная указка выключена.")
