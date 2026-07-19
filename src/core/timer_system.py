from PySide6.QtCore import QObject, QTimer, Signal

class TimerSystem(QObject):
    stretch_reminder = Signal()
    pomodoro_finished = Signal(str)  # 'work' or 'break'
    pomodoro_tick = Signal(str, int)  # state, remaining_seconds

    def __init__(self, config):
        super().__init__()
        self.config = config

        # Таймер для напоминания о растяжке
        self.stretch_timer = QTimer(self)
        self.stretch_timer.timeout.connect(self.on_stretch_timeout)

        # Таймер Pomodoro
        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.timeout.connect(self.on_pomodoro_timeout)
        self.pomodoro_state = "idle"  # 'work', 'break', 'idle'
        self.pomodoro_duration = 0
        self.pomodoro_remaining = 0

    def start_stretch_timer(self):
        interval = self.config.get("stretch_interval") * 60 * 1000  # в мс
        self.stretch_timer.start(interval)

    def restart_stretch_timer(self):
        self.stretch_timer.stop()
        self.start_stretch_timer()

    def on_stretch_timeout(self):
        self.stretch_reminder.emit()

    def start_pomodoro(self, mode="work"):
        self.pomodoro_state = mode
        minutes = self.config.get(f"pomodoro_{mode}")
        self.pomodoro_duration = minutes * 60
        self.pomodoro_remaining = self.pomodoro_duration
        self.pomodoro_timer.start(1000)  # Срабатывает каждую секунду
        self.pomodoro_tick.emit(self.pomodoro_state, self.pomodoro_remaining)

    def stop_pomodoro(self):
        self.pomodoro_timer.stop()
        self.pomodoro_state = "idle"
        self.pomodoro_duration = 0
        self.pomodoro_remaining = 0
        self.pomodoro_tick.emit("idle", 0)

    def on_pomodoro_timeout(self):
        if self.pomodoro_remaining > 1:
            self.pomodoro_remaining -= 1
            self.pomodoro_tick.emit(self.pomodoro_state, self.pomodoro_remaining)
        else:
            last_state = self.pomodoro_state
            self.stop_pomodoro()
            self.pomodoro_finished.emit(last_state)
