from PySide6.QtCore import QObject, QTimer, Signal

class TimerSystem(QObject):
    stretch_reminder = Signal()
    pomodoro_finished = Signal(str) # 'work' or 'break'

    def __init__(self, config):
        super().__init__()
        self.config = config

        # Таймер для напоминания о растяжке
        self.stretch_timer = QTimer(self)
        self.stretch_timer.timeout.connect(self.on_stretch_timeout)

        # Таймер Pomodoro
        self.pomodoro_timer = QTimer(self)
        self.pomodoro_timer.timeout.connect(self.on_pomodoro_timeout)
        self.pomodoro_state = "idle" # 'work', 'break', 'idle'

    def start_stretch_timer(self):
        interval = self.config.get("stretch_interval") * 60 * 1000 # в мс
        self.stretch_timer.start(interval)

    def on_stretch_timeout(self):
        self.stretch_reminder.emit()

    def start_pomodoro(self, mode="work"):
        self.pomodoro_state = mode
        minutes = self.config.get(f"pomodoro_{mode}")
        self.pomodoro_timer.start(minutes * 60 * 1000)

    def on_pomodoro_timeout(self):
        last_state = self.pomodoro_state
        self.pomodoro_timer.stop()
        self.pomodoro_state = "idle"
        self.pomodoro_finished.emit(last_state)
