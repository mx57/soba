import sys
from PySide6.QtWidgets import QApplication
from src.ui.main_window import PetWindow
from src.ui.tray_menu import TrayMenu
from src.core.input_manager import InputManager
from src.core.timer_system import TimerSystem
from src.utils.config_manager import ConfigManager
from src.utils.sound_manager import SoundManager
from src.utils.data_store import DataStore

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config = ConfigManager()

    # Регистрация пользовательских скинов из конфига
    from src.utils.bonding_utils import CAT_SKINS
    custom_skins = config.get("custom_skins") or {}
    for skin_id, name in custom_skins.items():
        CAT_SKINS[skin_id] = name

    db = DataStore()
    db.log_event("app_start", "Приложение запущено")

    window = PetWindow(config)

    sound_manager = SoundManager(config)

    timer_system = TimerSystem(config)
    window.set_timer_system(timer_system)

    timer_system.stretch_reminder.connect(lambda: window.show_notification("Время размяться", "Пора немного пошевелиться! 🐾"))
    timer_system.pomodoro_finished.connect(lambda mode: window.show_notification("Таймер Pomodoro", f"Пора для {('отдыха' if mode=='work' else 'работы')}! 🍎"))
    timer_system.start_stretch_timer()

    input_manager = InputManager(window, db)
    window.input_manager = input_manager
    input_manager.start()

    timer_system.pomodoro_finished.connect(input_manager.on_pomodoro_finished)

    tray = TrayMenu(window)

    # Cleanup on close
    window.closed.connect(input_manager.flush_all)
    window.closed.connect(lambda: input_manager.monitor.stop())
    window.closed.connect(lambda: input_manager.monitor.wait())
    window.closed.connect(db.close)

    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
