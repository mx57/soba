import os
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject
from src.utils.paths import TRAY_ICON_PATH, get_animation_path
from src.ui.settings_dialog import SettingsDialog
from src.ui.stats_dialog import StatsDialog

class TrayMenu(QObject):
    def __init__(self, pet_window):
        super().__init__()
        self.window = pet_window

        self.tray_icon = QSystemTrayIcon(self.window)
        # Используем статичную PNG иконку для трея
        if os.path.exists(TRAY_ICON_PATH):
            self.tray_icon.setIcon(QIcon(TRAY_ICON_PATH))
        else:
            self.tray_icon.setIcon(QIcon(get_animation_path("cat", "idle")))

        self.menu = QMenu()
        self.setup_menu()

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

    def setup_menu(self):
        # Действия с питомцем
        feed_action = QAction("Покормить", self)
        feed_action.triggered.connect(self.feed_pet)
        self.menu.addAction(feed_action)

        play_action = QAction("Поиграть", self)
        play_action.triggered.connect(lambda checked: self.window.animation_manager.play_state("playing"))
        self.menu.addAction(play_action)

        sleep_action = QAction("Уложить спать", self)
        sleep_action.triggered.connect(lambda checked: self.window.animation_manager.play_state("sleeping"))
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
        skins = {
            "Стандартный": "default",
            "Рыжий": "orange",
            "Сиамский": "siamese",
            "Бежевый": "ginger",
            "Розовый": "pink",
            "Белый": "white",
            "Серый": "gray",
            "Трехцветный": "calico",
            "Черный": "black"
        }
        for name, skin_id in skins.items():
            action = QAction(name, self)
            action.triggered.connect(lambda checked, sid=skin_id: self.window.animation_manager.set_skin(sid))
            skin_menu.addAction(action)
        self.menu.addMenu(skin_menu)

        self.menu.addSeparator()

        # Pomodoro
        pomodoro_menu = QMenu("Таймер Pomodoro", self.menu)
        start_work = QAction("Начать работу (25 мин)", self)
        start_work.triggered.connect(self.start_work_timer)
        pomodoro_menu.addAction(start_work)

        start_break = QAction("Перерыв (5 мин)", self)
        start_break.triggered.connect(self.start_break_timer)
        pomodoro_menu.addAction(start_break)

        self.menu.addMenu(pomodoro_menu)

        self.menu.addSeparator()

        # Peek Mode (Прятки)
        peek_action = QAction("Спрятать котика", self)
        peek_action.triggered.connect(self.window.toggle_peek_mode)
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

    def show_message(self, title, message):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)

    def quit_app(self, checked=False):
        QApplication.instance().quit()

    def start_work_timer(self, checked=False):
        if self.window.timer_system:
            self.window.timer_system.start_pomodoro("work")
            self.window.show_message("Пора работать! 🛠")

    def start_break_timer(self, checked=False):
        if self.window.timer_system:
            self.window.timer_system.start_pomodoro("break")
            self.window.show_message("Отдыхаем! ☕")

    def show_settings(self, checked=False):
        dialog = SettingsDialog(self.window.config, self.window)
        if dialog.exec():
            # Обновляем настройки в реальном времени
            self.window.update_from_config()
            self.window.show_message("Настройки сохранены! 💾")

    def show_stats(self, checked=False):
        if self.window.input_manager and self.window.input_manager.db:
            # Сбрасываем очки перед показом
            self.window.input_manager.flush_points()
            dialog = StatsDialog(self.window.input_manager.db, self.window)
            dialog.exec()

    def feed_pet(self, checked=False):
        self.window.animation_manager.play_state("eating")
        if self.window.input_manager:
            self.window.input_manager.add_points(5)
            if self.window.input_manager.db:
                self.window.input_manager.db.increment_stat("times_fed")
            self.window.show_message("Мням! +5 ❤️")

    def toggle_laser(self, checked):
        if self.window.input_manager:
            self.window.input_manager.set_laser_mode(checked)
            if checked:
                self.window.show_message("Лазерная указка активирована! 🔴")
            else:
                self.window.show_message("Лазерная указка выключена.")
