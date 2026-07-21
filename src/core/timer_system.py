from PySide6.QtCore import QObject, QTimer, Signal

class TimerSystem(QObject):
    stretch_reminder = Signal()
    pomodoro_finished = Signal(str) # 'work' or 'break'
    pomodoro_tick = Signal(int)     # remaining seconds

    def __init__(self, config):
        super().__init__()
        self.config = config

        # Таймер для напоминания о растяжке
        self.stretch_timer = QTimer(self)
        self.stretch_timer.timeout.connect(self.on_stretch_timeout)

        # Таймер Pomodoro (работает с секундным интервалом)
        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.timeout.connect(self.on_pomodoro_tick)
        self.pomodoro_state = "idle" # 'work', 'break', 'idle'
        self.pomodoro_remaining = 0

    def start_stretch_timer(self):
        interval = self.config.get("stretch_interval") * 60 * 1000 # в мс
        self.stretch_timer.start(interval)

    def restart_stretch_timer(self):
        self.stretch_timer.stop()
        self.start_stretch_timer()

    def on_stretch_timeout(self):
        self.stretch_reminder.emit()

    def start_pomodoro(self, mode="work"):
        self.pomodoro_state = mode
        minutes = self.config.get(f"pomodoro_{mode}")
        self.pomodoro_remaining = minutes * 60
        self.pomodoro_timer.start(1000) # Секундный интервал
        self.pomodoro_tick.emit(self.pomodoro_remaining)

    def on_pomodoro_tick(self):
        if self.pomodoro_remaining > 0:
            self.pomodoro_remaining -= 1
            self.pomodoro_tick.emit(self.pomodoro_remaining)
            if self.pomodoro_remaining <= 0:
                self.on_pomodoro_timeout()

    def on_pomodoro_timeout(self):
        last_state = self.pomodoro_state
        self.pomodoro_timer.stop()
        self.pomodoro_state = "idle"
        self.pomodoro_remaining = 0
        self.pomodoro_finished.emit(last_state)

    def stop_pomodoro(self):
        if self.pomodoro_state != "idle":
            self.pomodoro_timer.stop()
            self.pomodoro_state = "idle"
            self.pomodoro_remaining = 0
            self.pomodoro_tick.emit(0)
