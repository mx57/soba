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
    db = DataStore()
    db.log_event("app_start", "Приложение запущено")

    window = PetWindow(config)
    tray = TrayMenu(window)

    sound_manager = SoundManager(config)

    timer_system = TimerSystem(config)
    timer_system.stretch_reminder.connect(lambda: tray.show_message("Пора размяться!", "Котик напоминает: сделай перерыв и потянись!"))
    timer_system.pomodoro_finished.connect(lambda mode: tray.show_message("Pomodoro", f"Время {('работы' if mode=='work' else 'отдыха')} окончено!"))
    timer_system.start_stretch_timer()

    input_manager = InputManager(window)
    input_manager.start()

    # Cleanup on close
    window.closed.connect(lambda: input_manager.monitor.stop())
    window.closed.connect(lambda: input_manager.monitor.wait())

    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
