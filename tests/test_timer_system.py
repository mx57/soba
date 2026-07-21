import sys
import unittest
from PySide6.QtWidgets import QApplication
from src.core.timer_system import TimerSystem
from src.utils.config_manager import ConfigManager

# Ensure QApplication instance is created for QTimer
app = QApplication.instance() or QApplication(sys.argv)

class TestTimerSystem(unittest.TestCase):
    def setUp(self):
        # Create a mock config or ConfigManager
        self.config = ConfigManager("test_timer_settings.json")
        # Ensure our test settings are set
        self.config.set("pomodoro_work", 25)
        self.config.set("pomodoro_break", 5)
        self.timer_system = TimerSystem(self.config)

    def tearDown(self):
        # Stop any active timers
        self.timer_system.stretch_timer.stop()
        self.timer_system.pomodoro_timer.stop()
        import os
        if os.path.exists("test_timer_settings.json"):
            os.remove("test_timer_settings.json")

    def test_initial_state(self):
        self.assertEqual(self.timer_system.pomodoro_state, "idle")
        self.assertEqual(self.timer_system.pomodoro_remaining, 0)

    def test_start_pomodoro_work(self):
        self.timer_system.start_pomodoro("work")
        self.assertEqual(self.timer_system.pomodoro_state, "work")
        self.assertEqual(self.timer_system.pomodoro_remaining, 25 * 60)
        self.assertTrue(self.timer_system.pomodoro_timer.isActive())

    def test_start_pomodoro_break(self):
        self.timer_system.start_pomodoro("break")
        self.assertEqual(self.timer_system.pomodoro_state, "break")
        self.assertEqual(self.timer_system.pomodoro_remaining, 5 * 60)
        self.assertTrue(self.timer_system.pomodoro_timer.isActive())

    def test_stop_pomodoro(self):
        self.timer_system.start_pomodoro("work")
        self.timer_system.stop_pomodoro()
        self.assertEqual(self.timer_system.pomodoro_state, "idle")
        self.assertEqual(self.timer_system.pomodoro_remaining, 0)
        self.assertFalse(self.timer_system.pomodoro_timer.isActive())

    def test_pomodoro_tick(self):
        ticks = []
        self.timer_system.pomodoro_tick.connect(lambda val: ticks.append(val))

        self.timer_system.start_pomodoro("work")
        # Remaining starts at 25 * 60
        self.assertEqual(self.timer_system.pomodoro_remaining, 1500)
        self.assertEqual(len(ticks), 1)
        self.assertEqual(ticks[0], 1500)

        # Simulate a tick
        self.timer_system.on_pomodoro_tick()
        self.assertEqual(self.timer_system.pomodoro_remaining, 1499)
        self.assertEqual(len(ticks), 2)
        self.assertEqual(ticks[1], 1499)

    def test_pomodoro_finish(self):
        finished_modes = []
        self.timer_system.pomodoro_finished.connect(lambda mode: finished_modes.append(mode))

        self.timer_system.start_pomodoro("break")
        self.timer_system.pomodoro_remaining = 1 # Set remaining to 1 second

        # Simulate final tick to 0
        self.timer_system.on_pomodoro_tick()
        self.assertEqual(self.timer_system.pomodoro_remaining, 0)
        self.assertEqual(self.timer_system.pomodoro_state, "idle")
        self.assertEqual(len(finished_modes), 1)
        self.assertEqual(finished_modes[0], "break")
        self.assertFalse(self.timer_system.pomodoro_timer.isActive())

if __name__ == "__main__":
    unittest.main()
