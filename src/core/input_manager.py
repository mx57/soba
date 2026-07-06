import time
from pynput import mouse, keyboard
from PySide6.QtCore import QObject, Signal, QThread, QTimer, Qt
from src.utils.bonding_utils import get_level, check_achievements, ACHIEVEMENTS

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
        self.key_timestamps = []
        self.typing_speed_threshold = 5 # Нажатий в секунду для перехода в режим kneading/working
        self.overheat_threshold = 12 # KPS для режима перегрева

        self.last_mouse_time = 0
        self.last_mouse_pos = (0, 0)
        self.last_input_time = time.time()
        self.last_purr_time = 0
        self.laser_mode = False

        self.monitor.key_pressed.connect(self.handle_key)
        self.monitor.mouse_moved.connect(self.handle_mouse)

        # Watchdog для сброса состояний при отсутствии активности и начисления очков
        self.watchdog = QTimer(self)
        self.watchdog.timeout.connect(self.periodic_check)

        self.last_affection_points = 0
        self.pending_points = 0
        self.pending_stats = {
            "total_clicks": 0,
            "work_seconds": 0,
            "cursor_catches": 0,
            "total_feedings": 0,
            "pomodoros_completed": 0,
            "petting_count": 0,
            "shakes_count": 0
        }
        self.max_kps = 0
        self.total_clicks_cache = 0
        self.unlocked_achievements = []
        if self.db:
            self.last_affection_points = self.db.get_affection_points()
            self.unlocked_achievements = self.db.get_unlocked_achievements()
            self.max_kps = self.db.get_stat("max_kps")
            self.total_clicks_cache = self.db.get_stat("total_clicks")

    def start(self):
        self.monitor.start()
        self.watchdog.start(500) # Проверка каждые 0.5 сек

    def _update_kps(self):
        """Обновляет скользящее окно KPS и текущий счетчик нажатий."""
        now = time.time()
        self.key_timestamps = [t for t in self.key_timestamps if now - t <= 1.0]
        self.typing_count = len(self.key_timestamps)

    def periodic_check(self):
        now = time.time()
        idle_time = now - self.last_input_time

        # 0. Обновление скользящего окна KPS
        self._update_kps()

        # 1. Проверка бездействия
        if idle_time > 2.0:
            # Если нет ввода более 2 секунд - сброс в idle
            if self.window.animation_manager.current_state in ["working", "overheat", "hunting", "playing", "eating"]:
                self.window.animation_manager.play_state("idle")

            # Если бездействие более 15 секунд и котик уже в idle - переходим в thinking
            if idle_time > 15.0 and self.window.animation_manager.current_state == "idle":
                self.window.animation_manager.play_state("thinking")
        else:
            # Динамическая смена состояний на основе KPS (даже если прямо сейчас нет нажатий)
            if self.typing_count > self.overheat_threshold:
                if self.window.animation_manager.current_state != "overheat":
                    self.window.animation_manager.play_state("overheat")
            elif self.typing_count > self.typing_speed_threshold:
                if self.window.animation_manager.current_state not in ["working", "overheat"]:
                    self.window.animation_manager.play_state("working")
            elif self.typing_count <= self.typing_speed_threshold:
                if self.window.animation_manager.current_state in ["working", "overheat"]:
                    self.window.animation_manager.play_state("idle")

        # Если нет ввода более 15 секунд и котик в idle - переходим в thinking
        if now - self.last_input_time > 15.0:
            if self.window.animation_manager.current_state == "idle":
                self.window.animation_manager.play_state("thinking")

        # 2. Начисление очков привязанности за взаимодействие (буферизация) и статистика
        # Начисляем очки раз в 2 секунды (каждый 4-й тик таймера 0.5с) для баланса
        if int(now * 2) % 4 == 0:
            state = self.window.animation_manager.current_state
            if self.db and state in ["working", "overheat", "playing", "hunting"]:
                self.add_points(1)

            # Статистика рабочего времени (буферизация)
            if self.db and state in ["working", "overheat"]:
                self.pending_stats["work_seconds"] += 2
                self.check_for_achievements()

        # 3. Поддержка непрерывной охоты
        if self.window.animation_manager.current_state == "hunting" or self.laser_mode:
            if self.laser_mode and self.window.animation_manager.current_state not in ["hunting", "happy"]:
                self.window.animation_manager.play_state("hunting")
            self.window.start_hunting(self.last_mouse_pos[0], self.last_mouse_pos[1])

    def add_points(self, points):
        """Добавляет очки и проверяет повышение уровня."""
        if not self.db:
            return

        old_level = get_level(self.last_affection_points)
        self.pending_points += points

        # Сохраняем в БД только когда накопилось 10 очков (примерно каждые 10 сек активной работы)
        if self.pending_points >= 10:
            self.flush_points()

        # Проверка уровня (визуально можно чаще, используя буферизованные очки)
        virtual_total = self.last_affection_points + self.pending_points
        new_level = get_level(virtual_total)

        if new_level > old_level:
            self.flush_points() # Обязательно сбрасываем перед уведомлением
            self.window.show_message(f"Уровень дружбы повышен: {new_level} ❤️")
            self.window.sound_manager.play_sound("happy")
            self.check_for_achievements()

    def flush_points(self):
        """Устарело: используйте flush_all"""
        self.flush_all()

    def flush_all(self):
        """Записывает все накопленные данные (очки и статистику) в базу данных."""
        if not self.db:
            return

        if self.pending_points > 0:
            self.db.add_affection_points(self.pending_points)
            self.last_affection_points += self.pending_points
            self.pending_points = 0

        for key, value in self.pending_stats.items():
            if value > 0:
                self.db.increment_stat(key, value)
                if key == "total_clicks":
                    self.total_clicks_cache += value
                self.pending_stats[key] = 0

        if hasattr(self.db, 'set_stat'):
            self.db.set_stat("max_kps", self.max_kps)

    def add_shake(self):
        """Регистрирует встряхивание котика."""
        self.pending_stats["shakes_count"] += 1
        self.check_for_achievements()

    def on_pomodoro_finished(self, mode):
        """Слот для завершения сессии Pomodoro."""
        if mode == "work":
            self.pending_stats["pomodoros_completed"] += 1
            self.check_for_achievements()

    def check_for_achievements(self):
        if not self.db:
            return

        # Получаем все данные из БД одним запросом
        current_stats = self.db.get_all_stats()

        # Обновляем значения на основе буферов в памяти
        current_stats["bonding_points"] = self.last_affection_points + self.pending_points
        current_stats["total_clicks"] = self.total_clicks_cache + self.pending_stats.get("total_clicks", 0)
        current_stats["max_kps"] = self.max_kps

        for key, value in self.pending_stats.items():
            if key not in ["total_clicks"]: # Эти мы уже обработали или они не нужны
                current_stats[key] = current_stats.get(key, 0) + value

        # Проверка достижений на основе актуальных данных в памяти
        new_ids = check_achievements(current_stats, self.unlocked_achievements)

        if new_ids:
            # Сбрасываем данные в БД только если открыто новое достижение
            self.flush_all()
            for ach_id in new_ids:
                # check_achievements уже фильтрует открытые, но на всякий случай
                if ach_id not in self.unlocked_achievements:
                    self.unlocked_achievements.append(ach_id)
                    self.db.add_achievement(ach_id)
                    ach = ACHIEVEMENTS[ach_id]
                    self.window.show_message(f"Достижение: {ach['icon']} {ach['title']}", duration=5000)
                    self.window.sound_manager.play_sound("happy")

    def _reset_idle_state(self):
        """Возвращает котика в idle, если он спал или думал."""
        if self.window.animation_manager.current_state in ["sleeping", "thinking"]:
            self.window.animation_manager.play_state("idle")

    def handle_key(self):
        now = time.time()
        self._reset_idle_state()
        self.last_input_time = now
        self._reset_idle_state()

        if self.db:
            self.pending_stats["total_clicks"] += 1
            # Проверяем достижения каждые 100 кликов (виртуальных)
            total_virtual_clicks = self.total_clicks_cache + self.pending_stats["total_clicks"]
            if total_virtual_clicks % 100 == 0:
                self.check_for_achievements()

        # Обновление скользящего окна KPS
        self.key_timestamps.append(now)
        self._update_kps()

        self.last_key_time = now

        # Обновление макс. KPS
        if self.typing_count > self.max_kps:
            self.max_kps = self.typing_count
            self.check_for_achievements()

        if self.typing_count > self.overheat_threshold:
            if self.window.animation_manager.current_state != "overheat":
                self.window.animation_manager.play_state("overheat")
        elif self.typing_count > self.typing_speed_threshold:
            if self.window.animation_manager.current_state != "working":
                self.window.animation_manager.play_state("working")

    def handle_mouse(self, x, y):
        now = time.time()
        self._reset_idle_state()
        self.last_input_time = now
        self._reset_idle_state()

        # Передаем позицию мыши в AnimationManager для оптимизации слежения глазами
        self.window.animation_manager.set_mouse_pos(x, y)

        # Вычисляем скорость мыши
        dt = now - self.last_mouse_time
        if dt > 0:
            dx = x - self.last_mouse_pos[0]
            dy = y - self.last_mouse_pos[1]
            # Оптимизация: используем квадрат расстояния для сравнения скоростей,
            # чтобы избежать дорогостоящего вычисления корня (sqrt/**0.5) и возведения в степень (**2)
            dist_sq = dx * dx + dy * dy

            # Если мышь движется быстро, активируем охоту (1500 px/sec)
            # speed > 1500  =>  sqrt(dist_sq)/dt > 1500  =>  dist_sq > (1500 * dt)**2
            threshold_fast = 1500 * dt
            if dist_sq > threshold_fast * threshold_fast:
                if self.window.animation_manager.current_state != "hunting":
                    self.window.animation_manager.play_state("hunting")
                    self.window.start_hunting(x, y)
            elif dist_sq < (100 * dt) * (100 * dt):
                # Если мышь замерла (speed < 100 px/sec), выходим из охоты через пару секунд
                if self.window.animation_manager.current_state == "hunting" and (now - self.last_mouse_time) > 2:
                    self.window.animation_manager.play_state("idle")

        self.last_mouse_pos = (x, y)
        self.last_mouse_time = now

        # Проверка "поглаживания"
        pet_pos = self.window.get_cached_pos()
        dx_pet = x - (pet_pos.x() + 50)
        dy_pet = y - (pet_pos.y() + 50)
        dist_sq_pet = dx_pet * dx_pet + dy_pet * dy_pet

        # Оптимизация: сравнение квадрата расстояния (порог 60px -> 3600)
        if dist_sq_pet < 3600:
            if self.window.animation_manager.current_state not in ["playing", "hunting", "shaking"]:
                 self.window.animation_manager.play_state("playing")
                 self.pending_stats["petting_count"] += 1
                 if self.pending_stats["petting_count"] % 5 == 0:
                     self.check_for_achievements()
                 if now - self.last_purr_time > 2.0:
                     self.window.sound_manager.play_sound("purr")
                     self.last_purr_time = now

    def toggle_laser_mode(self):
        self.laser_mode = not self.laser_mode
        if self.laser_mode:
            self.window.animation_manager.play_state("hunting")
            self.window.setCursor(Qt.CrossCursor)
        else:
            self.window.setCursor(Qt.ArrowCursor)
            self.window.animation_manager.play_state("idle")
        return self.laser_mode
