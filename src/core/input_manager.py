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
        self.overheat_threshold = 12 # KPS для режима перегрева

        self.last_mouse_time = 0
        self.last_mouse_pos = (0, 0)

        self.monitor.key_pressed.connect(self.handle_key)
        self.monitor.mouse_moved.connect(self.handle_mouse)

    def start(self):
        self.monitor.start()

    def handle_key(self):
        now = time.time()
        dt = now - self.last_key_time

        if dt > 1.0:
            kps = self.typing_count / dt if dt > 0 else 0
            self.typing_count = 1

            if kps > self.overheat_threshold:
                if self.window.animation_manager.current_state != "overheat":
                    self.window.animation_manager.play_state("overheat")
            elif kps > self.typing_speed_threshold:
                if self.window.animation_manager.current_state != "working":
                    self.window.animation_manager.play_state("working")
            else:
                # Если скорость упала ниже порога, возвращаемся в idle
                if self.window.animation_manager.current_state in ["working", "overheat"]:
                    self.window.animation_manager.play_state("idle")
        else:
            self.typing_count += 1

        self.last_key_time = now

    def handle_mouse(self, x, y):
        now = time.time()
        # Вычисляем скорость мыши
        dt = now - self.last_mouse_time
        if dt > 0:
            dx = x - self.last_mouse_pos[0]
            dy = y - self.last_mouse_pos[1]
            speed = (dx**2 + dy**2)**0.5 / dt

            # Если мышь движется быстро, активируем охоту
            if speed > 1500: # px/sec
                if self.window.animation_manager.current_state != "hunting":
                    self.window.animation_manager.play_state("hunting")
                    self.window.start_hunting(x, y)
            elif speed < 100:
                # Если мышь замерла, выходим из охоты через пару секунд
                if self.window.animation_manager.current_state == "hunting" and (now - self.last_mouse_time) > 2:
                    self.window.animation_manager.play_state("idle")

        self.last_mouse_pos = (x, y)
        self.last_mouse_time = now

        # Проверка "поглаживания"
        pet_pos = self.window.pos()
        dist = ((x - (pet_pos.x() + 50))**2 + (y - (pet_pos.y() + 50))**2)**0.5

        if dist < 60:
            if self.window.animation_manager.current_state not in ["playing", "hunting", "shaking"]:
                 self.window.animation_manager.play_state("playing")
                 self.window.sound_manager.play_sound("purr")
