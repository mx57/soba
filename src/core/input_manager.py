import time
from pynput import mouse, keyboard
from PySide6.QtCore import QObject, Signal, QThread

class InputMonitor(QThread):
    key_pressed = Signal()
    mouse_moved = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        # Используем слушатели
        self.mouse_listener = mouse.Listener(on_move=self.on_move)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)

        self.mouse_listener.start()
        self.keyboard_listener.start()

        while self.running:
            time.sleep(0.1)

        self.mouse_listener.stop()
        self.keyboard_listener.stop()

    def on_move(self, x, y):
        self.mouse_moved.emit(x, y)

    def on_press(self, key):
        self.key_pressed.emit()

    def stop(self):
        self.running = False

class InputManager(QObject):
    def __init__(self, pet_window):
        super().__init__()
        self.window = pet_window
        self.monitor = InputMonitor()

        self.last_key_time = 0
        self.typing_count = 0
        self.typing_speed_threshold = 5 # Нажатий в секунду для перехода в режим kneading/working

        self.monitor.key_pressed.connect(self.handle_key)
        self.monitor.mouse_moved.connect(self.handle_mouse)

    def start(self):
        self.monitor.start()

    def handle_key(self):
        now = time.time()
        self.typing_count += 1

        if now - self.last_key_time > 2:
            self.typing_count = 1

        self.last_key_time = now

        if self.window.animation_manager.current_state != "working":
             self.window.animation_manager.play_state("working")

    def handle_mouse(self, x, y):
        # Здесь можно реализовать "охоту" или слежение глазами
        # Пока просто проверяем расстояние до окна для реакции (поглаживание)
        pet_pos = self.window.pos()
        dist = ((x - (pet_pos.x() + 50))**2 + (y - (pet_pos.y() + 50))**2)**0.5

        if dist < 60:
            if self.window.animation_manager.current_state not in ["playing", "hunting"]:
                 self.window.animation_manager.play_state("hunting")
