import unittest
import os
import json
from src.utils.config_manager import ConfigManager
from src.utils.data_store import DataStore

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

        db.close()

if __name__ == '__main__':
    unittest.main()
