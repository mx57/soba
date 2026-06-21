import os
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject
from src.utils.paths import TRAY_ICON_PATH, get_animation_path

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
        feed_action.triggered.connect(lambda: self.window.animation_manager.play_state("eating"))
        self.menu.addAction(feed_action)

        play_action = QAction("Поиграть", self)
        play_action.triggered.connect(lambda: self.window.animation_manager.play_state("playing"))
        self.menu.addAction(play_action)

        sleep_action = QAction("Уложить спать", self)
        sleep_action.triggered.connect(lambda: self.window.animation_manager.play_state("sleeping"))
        self.menu.addAction(sleep_action)

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
            action.triggered.connect(lambda checked=False, sid=skin_id: self.window.animation_manager.set_skin(sid))
            skin_menu.addAction(action)
        self.menu.addMenu(skin_menu)

        # Настройки
        settings_action = QAction("Настройки", self)
        # settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(settings_action)

        self.menu.addSeparator()

        # Выход
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.window.close)
        self.menu.addAction(quit_action)

    def show_message(self, title, message):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 5000)
