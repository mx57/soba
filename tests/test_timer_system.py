import unittest
from PySide6.QtWidgets import QApplication
from src.core.timer_system import TimerSystem
from src.utils.config_manager import ConfigManager

# Ensure there's a QApplication instance for QTimer / QObject creation
app = QApplication.instance() or QApplication([])

class TestTimerSystem(unittest.TestCase):
    def setUp(self):
        self.config = ConfigManager("test_settings.json")
        self.config.set("pomodoro_work", 25)
        self.config.set("pomodoro_break", 5)
        self.timer_system = TimerSystem(self.config)

    def test_initial_state(self):
        self.assertEqual(self.timer_system.pomodoro_state, "idle")
        self.assertEqual(self.timer_system.pomodoro_duration, 0)
        self.assertEqual(self.timer_system.pomodoro_remaining, 0)

    def test_start_pomodoro(self):
        tick_emitted = []
        def on_tick(state, remaining):
            tick_emitted.append((state, remaining))

        self.timer_system.pomodoro_tick.connect(on_tick)
        self.timer_system.start_pomodoro("work")

        self.assertEqual(self.timer_system.pomodoro_state, "work")
        self.assertEqual(self.timer_system.pomodoro_duration, 25 * 60)
        self.assertEqual(self.timer_system.pomodoro_remaining, 25 * 60)
        self.assertTrue(self.timer_system.pomodoro_timer.isActive())

        # Verify initial tick was emitted immediately
        self.assertEqual(len(tick_emitted), 1)
        self.assertEqual(tick_emitted[0], ("work", 25 * 60))

    def test_pomodoro_countdown_ticks(self):
        tick_emitted = []
        def on_tick(state, remaining):
            tick_emitted.append((state, remaining))

        self.timer_system.pomodoro_tick.connect(on_tick)
        self.timer_system.start_pomodoro("work")

        # Simulate a countdown tick
        self.timer_system.on_pomodoro_timeout()
        self.assertEqual(self.timer_system.pomodoro_remaining, 25 * 60 - 1)
        self.assertEqual(len(tick_emitted), 2)
        self.assertEqual(tick_emitted[1], ("work", 25 * 60 - 1))

    def test_stop_pomodoro(self):
        tick_emitted = []
        def on_tick(state, remaining):
            tick_emitted.append((state, remaining))

        self.timer_system.pomodoro_tick.connect(on_tick)
        self.timer_system.start_pomodoro("work")
        self.timer_system.stop_pomodoro()

        self.assertEqual(self.timer_system.pomodoro_state, "idle")
        self.assertEqual(self.timer_system.pomodoro_duration, 0)
        self.assertEqual(self.timer_system.pomodoro_remaining, 0)
        self.assertFalse(self.timer_system.pomodoro_timer.isActive())

        # Two ticks should have been emitted: start and stop
        self.assertEqual(len(tick_emitted), 2)
        self.assertEqual(tick_emitted[-1], ("idle", 0))

    def test_pomodoro_finished(self):
        finished_emitted = []
        def on_finished(mode):
            finished_emitted.append(mode)

        self.timer_system.pomodoro_finished.connect(on_finished)
        self.timer_system.start_pomodoro("break")

        # Set remaining to 1 second so next timeout triggers finished
        self.timer_system.pomodoro_remaining = 1
        self.timer_system.on_pomodoro_timeout()

        self.assertEqual(self.timer_system.pomodoro_state, "idle")
        self.assertEqual(len(finished_emitted), 1)
        self.assertEqual(finished_emitted[0], "break")
        self.assertFalse(self.timer_system.pomodoro_timer.isActive())

    def tearDown(self):
        import os
        if os.path.exists("test_settings.json"):
            os.remove("test_settings.json")

if __name__ == "__main__":
    unittest.main()
