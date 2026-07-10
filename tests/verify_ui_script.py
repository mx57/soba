import sys
import os

# Add src to path
sys.path.append(os.getcwd())

from PySide6.QtWidgets import QApplication
from src.ui.stats_dialog import StatsDialog
from src.utils.data_store import DataStore
from src.utils.config_manager import ConfigManager

def verify_ui():
    # Use offscreen platform for headless environments
    os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication(sys.argv)

    # Setup temporary DB
    db_path = "test_verify.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = DataStore(db_path)

    # Populate with some data
    db.add_affection_points(150) # Level 1
    db.set_stat("max_kps", 10)
    db.set_stat("total_clicks", 500)
    db.set_stat("work_seconds", 300)
    db.add_achievement("first_friend")

    # Log some events
    db.log_event("app_start", "Приложение замурчало")
    db.log_event("feeding", "Покормили рыбкой")
    db.log_event("level_up", "Уровень повышен до 1")
    db.log_event("achievement", "Разблокировано: Первый друг")
    db.log_event("pomodoro_start", "Начата сессия работы")

    # Mock window parent for StatsDialog if needed, but it should work with None
    dialog = StatsDialog(db)
    dialog.show()

    # Ensure UI is processed
    app.processEvents()

    # Take screenshots of both tabs
    os.makedirs("verification/screenshots", exist_ok=True)

    # Progress tab (default)
    dialog.tabs.setCurrentIndex(0)
    app.processEvents()
    dialog.grab().save("verification/screenshots/stats_progress.png")

    # History tab
    dialog.tabs.setCurrentIndex(1)
    app.processEvents()
    dialog.grab().save("verification/screenshots/stats_history.png")

    print("Screenshots saved to verification/screenshots/")

    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    verify_ui()
