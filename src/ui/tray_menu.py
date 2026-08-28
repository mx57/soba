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
        # Используем статичную PNG иконку для трея
        if os.path.exists(TRAY_ICON_PATH):
            self.tray_icon.setIcon(QIcon(TRAY_ICON_PATH))
        else:
            self.tray_icon.setIcon(QIcon(get_animation_path("cat", "idle")))

        self.menu = QMenu()
        self.setup_menu()

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.show()

        # Подписка на сигналы таймера для обновления статуса
        if self.window.timer_system:
            self.window.timer_system.pomodoro_tick.connect(self.update_pomodoro_status)
            self.window.timer_system.pomodoro_finished.connect(self.on_pomodoro_finished)

    def setup_menu(self):
        # 1. Секция статуса Pomodoro
        self.status_action = QAction("Таймер не запущен", self)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.stop_pomodoro_action = QAction("Остановить таймер", self)
        self.stop_pomodoro_action.setVisible(False)
        self.stop_pomodoro_action.triggered.connect(self.stop_pomodoro)
        self.menu.addAction(self.stop_pomodoro_action)

        self.menu.addSeparator()

        # Действия с питомцем
        feed_action = QAction("Покормить", self)
        feed_action.triggered.connect(self.feed_pet)
        self.menu.addAction(feed_action)

        play_action = QAction("Поиграть", self)
        play_action.triggered.connect(self.play_with_pet)
        self.menu.addAction(play_action)

        sleep_action = QAction("Уложить спать", self)
        sleep_action.triggered.connect(lambda checked=False: self.window.animation_manager.play_state("sleeping"))
        self.menu.addAction(sleep_action)

        self.menu.addSeparator()

        # Лазерная указка
        self.laser_action = QAction("Лазерная указка 🔴", self)
        self.laser_action.setCheckable(True)
        self.laser_action.triggered.connect(self.toggle_laser)
        self.menu.addAction(self.laser_action)

        # Подключаем синхронизацию сигнала лазерной указки от InputManager
        if hasattr(self.window, "input_manager") and self.window.input_manager:
            self.window.input_manager.laser_mode_changed.connect(self.laser_action.setChecked)

        self.menu.addSeparator()

        # Выбор скина
        self.skin_menu = QMenu("Выбрать окрас", self.menu)
        self.update_skin_menu()
        self.menu.addMenu(self.skin_menu)

        self.menu.addSeparator()

        # Pomodoro
        self.pomodoro_menu = QMenu("Таймер Pomodoro", self.menu)
        self.update_pomodoro_menu_texts()
        self.menu.addMenu(self.pomodoro_menu)

        self.menu.addSeparator()

        # Peek Mode (Прятки)
        peek_action = QAction("Спрятать котика", self)
        peek_action.triggered.connect(lambda checked=False: self.window.toggle_peek_mode())
        self.menu.addAction(peek_action)

        self.menu.addSeparator()

        # Опция "Поверх всех окон"
        self.always_on_top_action = QAction("Поверх всех окон", self)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.setChecked(self.window.config.get("always_on_top"))
        self.always_on_top_action.triggered.connect(self.toggle_always_on_top)
        self.menu.addAction(self.always_on_top_action)

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
        """Динамически обновляет или создает пункты меню Pomodoro на основе конфига."""
        self.pomodoro_menu.clear()

        work_min = self.window.config.get("pomodoro_work")
        break_min = self.window.config.get("pomodoro_break")

        start_work = QAction(f"Начать работу ({work_min} мин)", self)
        start_work.triggered.connect(self.start_work_timer)
        self.pomodoro_menu.addAction(start_work)

        start_break = QAction(f"Перерыв ({break_min} мин)", self)
        start_break.triggered.connect(self.start_break_timer)
        self.pomodoro_menu.addAction(start_break)

    def update_pomodoro_status(self, remaining_seconds):
        if not self.window.timer_system:
            return

        state = self.window.timer_system.pomodoro_state
        if state == "idle" or remaining_seconds <= 0:
            self.status_action.setText("Таймер не запущен")
            self.stop_pomodoro_action.setVisible(False)
            self.tray_icon.setToolTip("Десктопный Котик 🐾")
        else:
            mins, secs = divmod(remaining_seconds, 60)
            time_str = f"{mins:02d}:{secs:02d}"
            state_text = "Работа" if state == "work" else "Отдых"

            self.status_action.setText(f"Осталось ({state_text}): {time_str}")
            self.stop_pomodoro_action.setVisible(True)
            self.tray_icon.setToolTip(f"Котик [{state_text}]: {time_str}")

    def on_pomodoro_finished(self, mode):
        self.status_action.setText("Таймер не запущен")
        self.stop_pomodoro_action.setVisible(False)
        self.tray_icon.setToolTip("Десктопный Котик 🐾")

    def stop_pomodoro(self, checked=False):
        if self.window.timer_system:
            self.window.timer_system.stop_pomodoro()
            self.window.show_message("Таймер остановлен ⏹️")

    def toggle_always_on_top(self, checked):
        self.window.set_always_on_top(checked)

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

    def show_settings(self, checked=False):
        dialog = SettingsDialog(self.window.config, self.window)
        if dialog.exec():
            # Обновляем скин и прозрачность в реальном времени
            self.window.animation_manager.set_skin(self.window.config.get("skin"))
            self.window.set_opacity(self.window.config.get("opacity"))
            # Обновляем меню скинов
            self.update_skin_menu()
            # Обновляем режим "Поверх всех окон" в реальном времени
            self.window.set_always_on_top(self.window.config.get("always_on_top"))
            self.always_on_top_action.setChecked(self.window.config.get("always_on_top"))
            # Обновляем тексты в меню Pomodoro
            self.update_pomodoro_menu_texts()
            # Перезапускаем таймер растяжки с новым интервалом
            if self.window.timer_system:
                self.window.timer_system.restart_stretch_timer()
            self.window.show_message("Настройки сохранены! 💾")
        else:
            # Даже если диалог был отклонен, скин мог быть импортирован или удален мгновенно.
            # Поэтому мы в любом случае синхронизируем меню выбора окрасов в трее.
            self.update_skin_menu()
            # Также обновляем отображаемый скин (если удалили текущий активный, он мог сброситься на default)
            self.window.animation_manager.set_skin(self.window.config.get("skin"))

    def show_stats(self, checked=False):
        if self.window.input_manager and self.window.input_manager.db:
            # Сбрасываем все накопленные данные перед показом
            self.window.input_manager.flush_all()
            dialog = StatsDialog(self.window.input_manager.db, self.window)
            dialog.exec()

    def play_with_pet(self, checked=False):
        if self.window.input_manager:
            self.window.input_manager.force_state("playing")
        else:
            self.window.animation_manager.play_state("playing")

    def feed_pet(self, checked=False):
        if self.window.input_manager:
            self.window.input_manager.force_state("eating")
            self.window.input_manager.add_points(5)
            self.window.show_message("Мням! +5 ❤️")
            self.window.input_manager.pending_stats["total_feedings"] += 1
            if self.window.input_manager.db:
                self.window.input_manager.db.log_event("feeding", "Котик покормлен")
            self.window.input_manager.check_for_achievements()
        else:
            self.window.animation_manager.play_state("eating")
            self.window.show_message("Мням! +5 ❤️")

    def toggle_laser(self, checked):
        if self.window.input_manager:
            is_active = self.window.input_manager.toggle_laser_mode()
            if is_active:
                self.show_message("Мини-игра", "Лазерная указка активирована! 🔴")
            else:
                self.show_message("Мини-игра", "Лазерная указка выключена.")

    def update_skin_menu(self):
        self.skin_menu.clear()
        for skin_id, name in CAT_SKINS.items():
            action = QAction(name, self)
            action.triggered.connect(lambda checked=False, sid=skin_id: self.window.animation_manager.set_skin(sid))
            self.skin_menu.addAction(action)
