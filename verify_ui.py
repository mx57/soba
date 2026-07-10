
import sys
import os

# Set offscreen platform for headless environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from src.ui.stats_dialog import StatsDialog
from unittest.mock import MagicMock

def verify():
    app = QApplication(sys.argv)

    # Mock DataStore
    db = MagicMock()
    db.get_affection_points.return_value = 150
    db.get_stat.return_value = 25
    db.get_unlocked_achievements.return_value = ["first_friend"]
    db.get_recent_activity.return_value = [
        (1, "2023-10-27 10:00:00", "app_start", "Приложение запущено"),
        (2, "2023-10-27 10:05:00", "feed", "Котик покормлен"),
        (3, "2023-10-27 10:10:00", "achievement", "Открыто достижение: Первый друг")
    ]

    dialog = StatsDialog(db)
    dialog.show()

    # Process events to ensure layout is done
    app.processEvents()

    # Take screenshot of the first tab
    pixmap = dialog.grab()
    os.makedirs("verification/screenshots", exist_ok=True)
    pixmap.save("verification/screenshots/stats_dialog_progress.png")
    print("Screenshot saved to verification/screenshots/stats_dialog_progress.png")

    # Switch to the second tab (History)
    dialog.tabs.setCurrentIndex(1)
    app.processEvents()

    # Take screenshot of the second tab
    pixmap = dialog.grab()
    pixmap.save("verification/screenshots/stats_dialog_history.png")
    print("Screenshot saved to verification/screenshots/stats_dialog_history.png")

if __name__ == "__main__":
    verify()
