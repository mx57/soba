import time
from pynput import mouse, keyboard
from PySide6.QtCore import QObject, Signal, QThread, QTimer
from src.utils.bonding_utils import get_level

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
    def __init__(self, pet_window, data_store=None):
        super().__init__()
        self.window = pet_window
        self.db = data_store
        self.monitor = InputMonitor()

        self.last_key_time = 0
        self.typing_count = 0
        self.typing_speed_threshold = 5 # Нажатий в секунду для перехода в режим kneading/working
        self.overheat_threshold = 12 # KPS для режима перегрева

        self.last_mouse_time = 0
        self.last_mouse_pos = (0, 0)
        self.last_input_time = time.time()

        self.monitor.key_pressed.connect(self.handle_key)
        self.monitor.mouse_moved.connect(self.handle_mouse)

        # Watchdog для сброса состояний при отсутствии активности и начисления очков
        self.watchdog = QTimer(self)
        self.watchdog.timeout.connect(self.periodic_check)

        self.last_affection_points = 0
        self.pending_points = 0
        if self.db:
            self.last_affection_points = self.db.get_affection_points()

    def start(self):
        self.monitor.start()
        self.watchdog.start(500) # Проверка каждые 0.5 сек

    def periodic_check(self):
        now = time.time()

        # 1. Проверка бездействия
        # Если нет ввода более 2 секунд - сброс в idle
        if now - self.last_input_time > 2.0:
            if self.window.animation_manager.current_state in ["working", "overheat", "hunting", "playing"]:
                self.window.animation_manager.play_state("idle")
            self.typing_count = 0

        # 2. Начисление очков привязанности за взаимодействие (буферизация)
        if self.db and self.window.animation_manager.current_state in ["working", "overheat", "playing"]:
            self.add_points(1)

    def add_points(self, points):
        """Добавляет очки и проверяет повышение уровня."""
        if not self.db:
            return

        old_level = get_level(self.last_affection_points)
        self.pending_points += points

        # Сохраняем в БД только когда накопилось 10 очков (примерно каждые 10 сек активной работы)
        if self.pending_points >= 10:
            self.flush_points()

        # Проверка достижений (визуально можно чаще, используя буферизованные очки)
        virtual_total = self.last_affection_points + self.pending_points
        new_level = get_level(virtual_total)

        if new_level > old_level:
            self.flush_points() # Обязательно сбрасываем перед уведомлением
            self.window.show_message(f"Уровень дружбы повышен: {new_level} ❤️")
            self.window.sound_manager.play_sound("happy")

    def flush_points(self):
        """Записывает накопленные очки в базу данных."""
        if self.db and self.pending_points > 0:
            self.db.add_affection_points(self.pending_points)
            self.last_affection_points = self.db.get_affection_points()
            self.pending_points = 0

    def handle_key(self):
        now = time.time()
        self.last_input_time = now

        dt = now - self.last_key_time
        if dt > 1.0:
            self.typing_count = 1
        else:
            self.typing_count += 1

        self.last_key_time = now

        if self.typing_count > self.overheat_threshold:
            if self.window.animation_manager.current_state != "overheat":
                self.window.animation_manager.play_state("overheat")
        elif self.typing_count > self.typing_speed_threshold:
            if self.window.animation_manager.current_state != "working":
                self.window.animation_manager.play_state("working")

    def handle_mouse(self, x, y):
        now = time.time()
        self.last_input_time = now

        # Передаем позицию мыши в AnimationManager для оптимизации слежения глазами
        self.window.animation_manager.set_mouse_pos(x, y)

        # Вычисляем скорость мыши
        dt = now - self.last_mouse_time
        if dt > 0:
            dx = x - self.last_mouse_pos[0]
            dy = y - self.last_mouse_pos[1]
            # Оптимизация: используем квадрат расстояния для избежания math.sqrt
            dist_sq = dx*dx + dy*dy

            # Если мышь движется быстро, активируем охоту
            limit_hunt = 1500 * dt
            limit_stop = 100 * dt
            if dist_sq > limit_hunt * limit_hunt: # px/sec
                if self.window.animation_manager.current_state != "hunting":
                    self.window.animation_manager.play_state("hunting")
                    self.window.start_hunting(x, y)
            elif dist_sq < limit_stop * limit_stop:
                # Если мышь замерла, выходим из охоты через пару секунд
                if self.window.animation_manager.current_state == "hunting" and (now - self.last_mouse_time) > 2:
                    self.window.animation_manager.play_state("idle")

        self.last_mouse_pos = (x, y)
        self.last_mouse_time = now

        # Проверка "поглаживания" (оптимизировано через сравнение квадратов расстояний)
        pet_pos = self.window.pos()
        dx_pet = x - (pet_pos.x() + 50)
        dy_pet = y - (pet_pos.y() + 50)
        dist_sq_pet = dx_pet*dx_pet + dy_pet*dy_pet

        if dist_sq_pet < 3600: # 60**2
            if self.window.animation_manager.current_state not in ["playing", "hunting", "shaking"]:
                 self.window.animation_manager.play_state("playing")
                 self.window.sound_manager.play_sound("purr")
