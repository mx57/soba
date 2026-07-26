import sys
from unittest.mock import MagicMock

# Mock pynput because it requires an X server connection which fails in headless environments
mock_pynput = MagicMock()
sys.modules['pynput'] = mock_pynput
sys.modules['pynput.mouse'] = mock_pynput.mouse
sys.modules['pynput.keyboard'] = mock_pynput.keyboard

import unittest
import os
import json
import time
from src.utils.config_manager import ConfigManager
from src.utils.data_store import DataStore
from src.core.timer_system import TimerSystem
from src.core.input_manager import InputManager

class TestUtils(unittest.TestCase):
    def setUp(self):
        self.config_path = "test_settings.json"
        self.db_path = "test_activity.db"

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_config_manager(self):
        config = ConfigManager(self.config_path)
        config.set("username", "TestUser")
        self.assertEqual(config.get("username"), "TestUser")

        with open(self.config_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["username"], "TestUser")

    def test_data_store(self):
        db = DataStore(self.db_path)
        db.log_event("test_event", "test_description")
        recent = db.get_recent_activity(1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0][2], "test_event")

        # Тест статистики
        db.increment_stat("test_stat", 5)
        self.assertEqual(db.get_stat("test_stat"), 5)
        db.increment_stat("test_stat", 2)
        self.assertEqual(db.get_stat("test_stat"), 7)

        # Тест достижений
        db.add_achievement("test_ach")
        unlocked = db.get_unlocked_achievements()
        self.assertIn("test_ach", unlocked)

        # Тест пакетного обновления
        db.update_stats_batch(points=10, stats_dict={"total_clicks": 100, "new_stat": 1}, max_kps=20)
        self.assertEqual(db.get_affection_points(), 10)
        self.assertEqual(db.get_stat("total_clicks"), 100)
        self.assertEqual(db.get_stat("new_stat"), 1)
        self.assertEqual(db.get_stat("max_kps"), 20)

        db.close()

    def test_timer_system_pomodoro(self):
        config = ConfigManager(self.config_path)
        # Устанавливаем короткие интервалы для теста
        config.set("pomodoro_work", 2)
        ts = TimerSystem(config)

        # 1. Проверяем инициализацию и старт
        self.assertEqual(ts.pomodoro_state, "idle")
        self.assertEqual(ts.pomodoro_remaining, 0)

        ts.start_pomodoro("work")
        self.assertEqual(ts.pomodoro_state, "work")
        self.assertEqual(ts.pomodoro_remaining, 120)

        # 2. Проверяем тик таймера
        ts.on_pomodoro_tick()
        self.assertEqual(ts.pomodoro_remaining, 119)

        # 3. Проверяем остановку
        ts.stop_pomodoro()
        self.assertEqual(ts.pomodoro_state, "idle")
        self.assertEqual(ts.pomodoro_remaining, 0)

    def test_input_manager_petting_logic(self):
        # Мокаем PetWindow, AnimationManager и SoundManager
        mock_window = MagicMock()
        mock_window.width.return_value = 100
        mock_window.height.return_value = 100

        # Настраиваем mock для get_cached_pos
        mock_pos = MagicMock()
        mock_pos.x.return_value = 100
        mock_pos.y.return_value = 100
        mock_window.get_cached_pos.return_value = mock_pos

        mock_window.animation_manager.current_state = "idle"

        db = DataStore(self.db_path)
        im = InputManager(mock_window, db)

        # 1. Первая попытка: устанавливаем начальную точку
        im.handle_mouse(150, 150) # внутри котика (центр на 150, 150)
        self.assertEqual(im.pending_stats["petting_count"], 0)

        # 2. Маленькое движение (stroke_dist < 30px, dist_sq < 900)
        im.handle_mouse(155, 155) # движение на 7px
        self.assertEqual(im.pending_stats["petting_count"], 0)

        # 3. Быстрое движение без кулдауна (менее 500мс)
        im.handle_mouse(190, 190) # движение > 30px, но без кулдауна
        self.assertEqual(im.pending_stats["petting_count"], 0)

        # 4. Движение с симуляцией времени (кулдаун пройден и длина > 30px)
        im.last_pet_time -= 1.0 # Проматываем время назад
        im.handle_mouse(190, 190) # движение от (150,150) к (190,190) это ~56px
        self.assertEqual(im.pending_stats["petting_count"], 1)

        db.close()

    def test_always_on_top_logic(self):
        config = ConfigManager(self.config_path)
        config.set("always_on_top", True)

        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt

        app = QApplication.instance() or QApplication([])

        from src.ui.main_window import PetWindow
        window = PetWindow(config)

        # Проверяем начальные флаги
        self.assertTrue(bool(window.windowFlags() & Qt.WindowStaysOnTopHint))

        # Выключаем поверх всех окон
        window.set_always_on_top(False)
        self.assertFalse(bool(window.windowFlags() & Qt.WindowStaysOnTopHint))
        self.assertFalse(config.get("always_on_top"))

        # Включаем обратно
        window.set_always_on_top(True)
        self.assertTrue(bool(window.windowFlags() & Qt.WindowStaysOnTopHint))
        self.assertTrue(config.get("always_on_top"))

        window.close()

if __name__ == '__main__':
    unittest.main()
