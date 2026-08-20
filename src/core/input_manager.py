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
        self.last_emit_time = 0
        self.throttle_interval = 1.0 / 60.0 # 60Hz

    def run(self):
        # Используем слушатели
        self.mouse_listener = mouse.Listener(on_move=self.on_move)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)

        self.mouse_listener.start()
        self.keyboard_listener.start()

        # Вместо цикла while с sleep используем join(), что эффективнее
        self.mouse_listener.join()
        self.keyboard_listener.join()

    def on_move(self, x, y):
        if self.running:
            now = time.time()
            if now - self.last_emit_time >= self.throttle_interval:
                self.mouse_moved.emit(x, y)
                self.last_emit_time = now

    def on_press(self, key):
        if self.running:
            self.key_pressed.emit()

    def stop(self):
        self.running = False
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()

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
        cursor_pos = self.window.cursor().pos() if self.window else None
        self.last_mouse_pos = (cursor_pos.x(), cursor_pos.y()) if cursor_pos else (0, 0)
        self.last_input_time = time.time()
        self.last_purr_time = 0
        self.laser_mode = False

        # Поглаживание: предотвращение пассивного фарма очков
        self.last_pet_time = 0
        self.last_pet_mouse_pos = (0, 0)

        # Форсированные состояния
        self.forced_state_name = None
        self.forced_state_expires = 0.0

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
        self.stats_cache = {}

        self.last_periodic_check_time = time.time()
        self.points_time_accumulator = 0.0
        self.work_time_accumulator = 0.0

        if self.db:
            self.last_affection_points = self.db.get_affection_points()
            self.unlocked_achievements = self.db.get_unlocked_achievements()
            self.stats_cache = self.db.get_all_stats()
            self.max_kps = self.stats_cache.get("max_kps", 0)
            self.total_clicks_cache = self.stats_cache.get("total_clicks", 0)

    def force_state(self, state, duration=3.0):
        """Форсирует состояние котика и откладывает автоматический сброс в idle."""
        self.forced_state_name = state
        self.forced_state_expires = time.time() + duration
        self.window.animation_manager.play_state(state)
        # Также сдвигаем last_input_time вперед, чтобы в течение duration секунд idle_time оставался <= 2.0
        self.last_input_time = time.time() + duration - 2.0

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
        dt = now - self.last_periodic_check_time
        self.last_periodic_check_time = now

        idle_time = now - self.last_input_time
        current_state = self.window.animation_manager.current_state

        # 0. Обновление скользящего окна KPS
        self._update_kps()

        # Проверяем, действует ли еще форсированное состояние
        is_forced_active = False
        if self.forced_state_name is not None:
            if now < self.forced_state_expires:
                is_forced_active = True
                # Если текущее состояние в менеджере анимаций почему-то сбилось, но должно быть форсированным
                if current_state != self.forced_state_name:
                    self.window.animation_manager.play_state(self.forced_state_name)
                    current_state = self.forced_state_name
            else:
                # Время форсированного состояния истекло, сбрасываем его
                self.forced_state_name = None
                self.forced_state_expires = 0.0

        # 1. Проверка бездействия и переходы состояний
        if is_forced_active:
            # Если активно форсированное состояние, игнорируем обычный сброс и автоматические переходы
            pass
        elif idle_time > 2.0:
            # Если нет ввода более 2 секунд - сброс активных состояний в idle
            if current_state in ["working", "overheat", "hunting", "playing", "eating"]:
                self.window.animation_manager.play_state("idle")
                current_state = "idle"

            # Авто-сон после 120 секунд бездействия
            if idle_time > 120.0:
                if current_state != "sleeping":
                    self.window.animation_manager.play_state("sleeping")
            # Переход в 'thinking' после 15 секунд бездействия (если был в idle)
            elif idle_time > 15.0:
                if current_state == "idle":
                    self.window.animation_manager.play_state("thinking")
        else:
            # Динамическая смена состояний на основе KPS (при активном вводе)
            if self.typing_count > self.overheat_threshold:
                if current_state != "overheat":
                    self.window.animation_manager.play_state("overheat")
            elif self.typing_count > self.typing_speed_threshold:
                if current_state not in ["working", "overheat"]:
                    self.window.animation_manager.play_state("working")
            elif self.typing_count <= self.typing_speed_threshold:
                if current_state in ["working", "overheat"]:
                    self.window.animation_manager.play_state("idle")

        # 2. Начисление очков привязанности за взаимодействие (буферизация) и статистика
        # Используем точные аккумуляторы времени вместо нестабильного деления по времени
        if self.db:
            state = self.window.animation_manager.current_state

            # Начисление очков привязанности каждые 2 секунды активного взаимодействия
            if state in ["working", "overheat", "playing", "hunting"]:
                self.points_time_accumulator += dt
                if self.points_time_accumulator >= 2.0:
                    points_to_add = int(self.points_time_accumulator // 2.0)
                    self.add_points(points_to_add)
                    self.points_time_accumulator %= 2.0
            else:
                self.points_time_accumulator = 0.0

            # Начисление рабочего времени каждые 2 секунды работы
            if state in ["working", "overheat"]:
                self.work_time_accumulator += dt
                if self.work_time_accumulator >= 2.0:
                    seconds_to_add = int(self.work_time_accumulator // 2.0) * 2
                    self.pending_stats["work_seconds"] += seconds_to_add
                    self.work_time_accumulator %= 2.0
                    self.check_for_achievements()
            else:
                self.work_time_accumulator = 0.0

        # 3. Поддержка непрерывной охоты
        if self.window.animation_manager.current_state == "hunting" or self.laser_mode:
            if self.laser_mode and self.window.animation_manager.current_state not in ["hunting", "happy"]:
                self.window.animation_manager.play_state("hunting")
            self.window.start_hunting(self.last_mouse_pos[0], self.last_mouse_pos[1])

        # 4. Обновление интерактивного тултипа
        self.window.update_tooltip()

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
            self.db.log_event("level_up", f"Уровень повышен до {new_level}")
            self.check_for_achievements()

    def flush_points(self):
        """Устарело: используйте flush_all"""
        self.flush_all()

    def flush_all(self):
        """Записывает все накопленные данные (очки и статистику) в базу данных."""
        if not self.db:
            return

        if self.pending_points == 0 and all(v == 0 for v in self.pending_stats.values()) and self.max_kps == self.stats_cache.get("max_kps", 0):
            return

        # Используем пакетное обновление для оптимизации I/O
        self.db.update_stats_batch(
            points=self.pending_points,
            stats_dict=self.pending_stats,
            max_kps=self.max_kps
        )

        # Обновляем локальный кэш
        if self.pending_points > 0:
            self.last_affection_points += self.pending_points
            self.stats_cache["bonding_points"] = self.last_affection_points
            self.pending_points = 0

        for key, value in self.pending_stats.items():
            if value > 0:
                if key == "total_clicks":
                    self.total_clicks_cache += value
                self.stats_cache[key] = self.stats_cache.get(key, 0) + value
                self.pending_stats[key] = 0

        self.stats_cache["max_kps"] = self.max_kps

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

        # Используем кэш вместо частого обращения к БД
        current_stats = self.stats_cache.copy()

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
                    self.db.log_event("achievement", f"Разблокировано: {ach['title']}")

    def _reset_idle_state(self):
        """Возвращает котика в idle, если он спал или думал."""
        # Если активно форсированное состояние, не перебиваем его обычным вводом
        if self.forced_state_name is not None and time.time() < self.forced_state_expires:
            return
        if self.window.animation_manager.current_state in ["sleeping", "thinking"]:
            self.window.animation_manager.play_state("idle")

    def handle_key(self):
        now = time.time()
        self.last_input_time = now
        self._reset_idle_state()

        # Если активно форсированное состояние, не прерываем его обычными клавишами
        if self.forced_state_name is not None and now < self.forced_state_expires:
            # Но учитываем в кликах
            if self.db:
                self.pending_stats["total_clicks"] += 1
                total_virtual_clicks = self.total_clicks_cache + self.pending_stats["total_clicks"]
                if total_virtual_clicks % 100 == 0:
                    self.check_for_achievements()
            # Обновление скользящего окна KPS
            self.key_timestamps.append(now)
            self._update_kps()
            self.last_key_time = now
            if self.typing_count > self.max_kps:
                self.max_kps = self.typing_count
                self.check_for_achievements()
            return

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

            # Если мышь движется быстро и форсированное состояние не активно, активируем охоту
            if self.forced_state_name is None or now >= self.forced_state_expires:
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
        center_x = pet_pos.x() + self.window.width() // 2
        center_y = pet_pos.y() + self.window.height() // 2
        dx_pet = x - center_x
        dy_pet = y - center_y
        dist_sq_pet = dx_pet * dx_pet + dy_pet * dy_pet

        # Динамический радиус поглаживания в зависимости от размера окна питомца
        pet_radius = max(30, int(self.window.width() * 0.6))
        if dist_sq_pet < pet_radius * pet_radius:
            # Исключаем пассивный фарм (требуем активное поглаживание: активное движение мыши и кулдаун)
            if self.last_pet_time == 0:
                self.last_pet_mouse_pos = (x, y)
                self.last_pet_time = now

            dx_stroke = x - self.last_pet_mouse_pos[0]
            dy_stroke = y - self.last_pet_mouse_pos[1]
            stroke_dist_sq = dx_stroke * dx_stroke + dy_stroke * dy_stroke

            # Кулдаун 500мс и требование к длине мазка движения (30px -> 900)
            if now - self.last_pet_time >= 0.5 and stroke_dist_sq >= 900:
                # Если активно другое форсированное состояние (например, eating), не сбиваем его
                is_another_forced_active = self.forced_state_name is not None and self.forced_state_name != "playing" and now < self.forced_state_expires
                if not is_another_forced_active:
                    if self.window.animation_manager.current_state not in ["playing", "hunting", "shaking"]:
                        self.force_state("playing", duration=3.0)
                        self.pending_stats["petting_count"] += 1
                        if self.pending_stats["petting_count"] % 5 == 0:
                            self.check_for_achievements()
                        if now - self.last_purr_time > 2.0:
                            self.window.sound_manager.play_sound("purr")
                            self.last_purr_time = now
                self.last_pet_time = now
                self.last_pet_mouse_pos = (x, y)
        else:
            # Сброс начальной точки поглаживания при выходе за пределы питомца
            self.last_pet_time = 0

    def toggle_laser_mode(self):
        self.laser_mode = not self.laser_mode
        if self.laser_mode:
            self.window.animation_manager.play_state("hunting")
            # Создаем красивый светящийся красный лазерный курсор
            from PySide6.QtGui import QCursor, QPixmap, QPainter, QColor, QRadialGradient

            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)

            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)

            # Радиальный градиент для эффекта свечения
            gradient = QRadialGradient(8, 8, 8)
            gradient.setColorAt(0.0, QColor(255, 0, 0, 255))     # Интенсивный красный центр
            gradient.setColorAt(0.3, QColor(255, 0, 0, 220))
            gradient.setColorAt(0.8, QColor(255, 50, 50, 100))   # Мягкое красное свечение
            gradient.setColorAt(1.0, QColor(255, 100, 100, 0))   # Прозрачный край

            painter.setBrush(gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(0, 0, 16, 16)
            painter.end()

            laser_cursor = QCursor(pixmap, 8, 8)
            self.window.setCursor(laser_cursor)
        else:
            self.window.setCursor(Qt.ArrowCursor)
            self.window.animation_manager.play_state("idle")
        return self.laser_mode

    def reset_all_data(self):
        """Очищает базу данных и безопасно сбрасывает все внутриигровые показатели, кэши и аккумуляторы в памяти."""
        if not self.db:
            return

        # 1. Сбрасываем базу данных
        self.db.reset_all_data()

        # 2. Сбрасываем все показатели в памяти
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
        self.stats_cache = {
            "bonding_points": 0,
            "total_clicks": 0,
            "total_feedings": 0,
            "work_seconds": 0,
            "max_kps": 0,
            "pomodoros_completed": 0,
            "petting_count": 0,
            "shakes_count": 0
        }
        self.points_time_accumulator = 0.0
        self.work_time_accumulator = 0.0
