import unittest
from src.utils.bonding_utils import check_achievements, ACHIEVEMENTS

class TestAchievements(unittest.TestCase):
    def test_check_achievements_logic(self):
        # 1. Пустая статика
        stats = {}
        unlocked = []
        new = check_achievements(stats, unlocked)
        self.assertEqual(len(new), 0)

        # 2. Достижение по кликам
        stats = {"total_clicks": 1000}
        new = check_achievements(stats, unlocked)
        self.assertIn("clicker", new)

        # 3. Несколько достижений
        stats = {
            "total_clicks": 1000,
            "shakes_count": 10,
            "bonding_points": 100 # Level 1
        }
        new = check_achievements(stats, unlocked)
        self.assertIn("clicker", new)
        self.assertIn("shake_it", new)
        self.assertIn("first_friend", new)

        # 4. Уже разблокированные
        unlocked = ["clicker"]
        new = check_achievements(stats, unlocked)
        self.assertNotIn("clicker", new)
        self.assertIn("shake_it", new)

    def test_marathoner_achievement(self):
        stats = {"work_seconds": 3600}
        new = check_achievements(stats, [])
        self.assertIn("marathoner", new)
        self.assertIn("worker", new) # 600 seconds goal

if __name__ == "__main__":
    unittest.main()
