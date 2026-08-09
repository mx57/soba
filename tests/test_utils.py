import sys
from unittest.mock import MagicMock

# Mock pynput because it requires an X server connection which fails in headless environments
mock_pynput = MagicMock()
sys.modules['pynput'] = mock_pynput
sys.modules['pynput.mouse'] = mock_pynput.mouse
sys.modules['pynput.keyboard'] = mock_pynput.keyboard

import unittest
import os
import json
import time
from PySide6.QtCore import Qt, QPoint
from src.ui.main_window import PetWindow
from src.utils.config_manager import ConfigManager
from src.utils.data_store import DataStore
from src.core.timer_system import TimerSystem
from src.core.input_manager import InputManager

class TestUtils(unittest.TestCase):
    def setUp(self):
        self.config_path = "test_settings.json"
        self.db_path = "test_activity.db"

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_always_on_top_logic(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])

        config = ConfigManager(self.config_path)

        # 1. Проверяем дефолтное значение и перезапись в ConfigManager
        self.assertTrue(config.get("always_on_top"))
        config.set("always_on_top", False)
        self.assertFalse(config.get("always_on_top"))

        # 2. Инициализация PetWindow со значением False
        window = PetWindow(config)
        flags = window.windowFlags()
        self.assertFalse(bool(flags & Qt.WindowStaysOnTopHint))

        # 3. Динамическое изменение через set_always_on_top(True)
        window.set_always_on_top(True)
        flags = window.windowFlags()
        self.assertTrue(bool(flags & Qt.WindowStaysOnTopHint))
        self.assertTrue(config.get("always_on_top"))

        # 4. Динамическое изменение через set_always_on_top(False)
        window.set_always_on_top(False)
        flags = window.windowFlags()
        self.assertFalse(bool(flags & Qt.WindowStaysOnTopHint))
        self.assertFalse(config.get("always_on_top"))

    def test_config_manager(self):
        config = ConfigManager(self.config_path)
        config.set("username", "TestUser")
        self.assertEqual(config.get("username"), "TestUser")

        with open(self.config_path, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["username"], "TestUser")

    def test_data_store(self):
        db = DataStore(self.db_path)
        db.log_event("test_event", "test_description")
        recent = db.get_recent_activity(1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0][2], "test_event")

        # Тест статистики
        db.increment_stat("test_stat", 5)
        self.assertEqual(db.get_stat("test_stat"), 5)
        db.increment_stat("test_stat", 2)
        self.assertEqual(db.get_stat("test_stat"), 7)

        # Тест достижений
        db.add_achievement("test_ach")
        unlocked = db.get_unlocked_achievements()
        self.assertIn("test_ach", unlocked)

        # Тест пакетного обновления
        db.update_stats_batch(points=10, stats_dict={"total_clicks": 100, "new_stat": 1}, max_kps=20)
        self.assertEqual(db.get_affection_points(), 10)
        self.assertEqual(db.get_stat("total_clicks"), 100)
        self.assertEqual(db.get_stat("new_stat"), 1)
        self.assertEqual(db.get_stat("max_kps"), 20)

        db.close()

    def test_timer_system_pomodoro(self):
        config = ConfigManager(self.config_path)
        # Устанавливаем короткие интервалы для теста
        config.set("pomodoro_work", 2)
        ts = TimerSystem(config)

        # 1. Проверяем инициализацию и старт
        self.assertEqual(ts.pomodoro_state, "idle")
        self.assertEqual(ts.pomodoro_remaining, 0)

        ts.start_pomodoro("work")
        self.assertEqual(ts.pomodoro_state, "work")
        self.assertEqual(ts.pomodoro_remaining, 120)

        # 2. Проверяем тик таймера
        ts.on_pomodoro_tick()
        self.assertEqual(ts.pomodoro_remaining, 119)

        # 3. Проверяем остановку
        ts.stop_pomodoro()
        self.assertEqual(ts.pomodoro_state, "idle")
        self.assertEqual(ts.pomodoro_remaining, 0)

    def test_input_manager_petting_logic(self):
        # Мокаем PetWindow, AnimationManager и SoundManager
        mock_window = MagicMock()
        mock_window.width.return_value = 100
        mock_window.height.return_value = 100

        # Настраиваем mock для get_cached_pos
        mock_pos = MagicMock()
        mock_pos.x.return_value = 100
        mock_pos.y.return_value = 100
        mock_window.get_cached_pos.return_value = mock_pos

        # Настраиваем mock для cursor().pos()
        mock_cursor = MagicMock()
        mock_cursor.pos.return_value = QPoint(100, 100)
        mock_window.cursor.return_value = mock_cursor

        mock_window.animation_manager.current_state = "idle"

        db = DataStore(self.db_path)
        im = InputManager(mock_window, db)

        # 1. Первая попытка: устанавливаем начальную точку
        im.handle_mouse(150, 150) # внутри котика (центр на 150, 150)
        self.assertEqual(im.pending_stats["petting_count"], 0)

        # 2. Маленькое движение (stroke_dist < 30px, dist_sq < 900)
        im.handle_mouse(155, 155) # движение на 7px
        self.assertEqual(im.pending_stats["petting_count"], 0)

        # 3. Быстрое движение без кулдауна (менее 500мс)
        im.handle_mouse(190, 190) # движение > 30px, но без кулдауна
        self.assertEqual(im.pending_stats["petting_count"], 0)

        # 4. Движение с симуляцией времени (кулдаун пройден и длина > 30px)
        im.last_pet_time -= 1.0 # Проматываем время назад
        im.handle_mouse(190, 190) # движение от (150,150) к (190,190) это ~56px
        self.assertEqual(im.pending_stats["petting_count"], 1)

        db.close()

    def test_periodic_check_time_accumulators(self):
        # Мокаем PetWindow и AnimationManager
        mock_window = MagicMock()
        mock_window.animation_manager.current_state = "working"

        # Настраиваем mock для cursor().pos()
        mock_cursor = MagicMock()
        mock_cursor.pos.return_value = QPoint(100, 100)
        mock_window.cursor.return_value = mock_cursor

        db = DataStore(self.db_path)
        im = InputManager(mock_window, db)

        # Сбрасываем время
        im.last_periodic_check_time = time.time() - 2.5
        im.points_time_accumulator = 0.0
        im.work_time_accumulator = 0.0

        # Вызываем первый periodic_check, симулирующий 2.5 секунды работы
        # Ожидаем, что добавится 1 поинт привязанности и 2 секунды рабочего времени
        im.periodic_check()

        self.assertEqual(im.pending_points, 1)
        self.assertEqual(im.pending_stats["work_seconds"], 2)
        # Остаток в аккумуляторах должен быть 0.5с
        self.assertAlmostEqual(im.points_time_accumulator, 0.5, places=1)
        self.assertAlmostEqual(im.work_time_accumulator, 0.5, places=1)

        db.close()

    def test_laser_mode_transitions(self):
        # Мокаем PetWindow и AnimationManager
        mock_window = MagicMock()
        mock_window.animation_manager.current_state = "idle"

        # Настраиваем mock для cursor().pos()
        mock_cursor = MagicMock()
        mock_cursor.pos.return_value = QPoint(100, 100)
        mock_window.cursor.return_value = mock_cursor

        db = DataStore(self.db_path)
        im = InputManager(mock_window, db)

        # Переключаем лазер в True
        im.toggle_laser_mode()
        self.assertTrue(im.laser_mode)
        mock_window.animation_manager.play_state.assert_called_with("hunting")
        mock_window.setCursor.assert_called()

        # Переключаем обратно в False
        im.toggle_laser_mode()
        self.assertFalse(im.laser_mode)
        mock_window.animation_manager.play_state.assert_called_with("idle")

        db.close()

    def test_force_state_delays_idle(self):
        mock_window = MagicMock()
        mock_window.animation_manager.current_state = "idle"
        mock_cursor = MagicMock()
        mock_cursor.pos.return_value = QPoint(100, 100)
        mock_window.cursor.return_value = mock_cursor

        db = DataStore(self.db_path)
        im = InputManager(mock_window, db)

        now = time.time()
        # Force "eating" state with a duration of 5 seconds
        im.force_state("eating", duration=5.0)

        # last_input_time should be shifted into the future (about now + 3 seconds)
        self.assertTrue(im.last_input_time > now + 2.5)
        self.assertEqual(im.forced_state_name, "eating")
        self.assertTrue(im.forced_state_expires > now + 4.5)

        db.close()

    def test_force_state_expiry_and_resets(self):
        mock_window = MagicMock()
        mock_window.animation_manager.current_state = "eating"
        mock_cursor = MagicMock()
        mock_cursor.pos.return_value = QPoint(100, 100)
        mock_window.cursor.return_value = mock_cursor

        db = DataStore(self.db_path)
        im = InputManager(mock_window, db)

        # Инициализируем форсированное состояние
        im.force_state("eating", duration=0.1)
        self.assertEqual(im.forced_state_name, "eating")

        # Симулируем прохождение времени (истечение срока действия)
        im.forced_state_expires = time.time() - 1.0

        # periodic_check должен сбросить форсированное состояние и сбросить котика в idle, так как ввод не активен
        im.last_periodic_check_time = time.time() - 1.0
        im.last_input_time = time.time() - 5.0  # симулируем простой более 2 секунд
        im.periodic_check()

        self.assertIsNone(im.forced_state_name)
        mock_window.animation_manager.play_state.assert_any_call("idle")

        db.close()

    def test_sound_manager_with_none_config(self):
        from src.utils.sound_manager import SoundManager
        sm = SoundManager(None)
        # Test that play_sound on a non-existent sound returns gracefully and doesn't crash on None config
        sm.play_sound("non_existent_sound_123")

    def test_custom_skins_integration(self):
        # 1. Запись тестового SVG-файла
        from src.utils.bonding_utils import CAT_SKINS
        from src.core.animation_manager import AnimationManager
        from src.utils.paths import ANIMATIONS_DIR
        import shutil

        test_svg_dir = os.path.join(ANIMATIONS_DIR, "svg_skins")
        os.makedirs(test_svg_dir, exist_ok=True)
        test_svg_path = os.path.join(test_svg_dir, "cat_custom_test_skin.svg")

        with open(test_svg_path, "w", encoding="utf-8") as f:
            f.write("<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'><circle cx='50' cy='50' r='40'/></svg>")

        # 2. Инициализация ConfigManager с фейковым путем
        config = ConfigManager(self.config_path)
        custom_skins = {"custom_test_skin": "Тестовый Окрас"}
        config.set("custom_skins", custom_skins)

        # Симулируем регистрацию скинов при старте
        for skin_id, name in custom_skins.items():
            CAT_SKINS[skin_id] = name

        self.assertIn("custom_test_skin", CAT_SKINS)
        self.assertEqual(CAT_SKINS["custom_test_skin"], "Тестовый Окрас")

        # 3. Проверка того, что AnimationManager распознает этот скин
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication, QLabel
        app = QApplication.instance() or QApplication([])

        label = QLabel()
        anim_mgr = AnimationManager(label, config)
        anim_mgr.set_skin("custom_test_skin")

        self.assertEqual(anim_mgr.skin, "custom_test_skin")
        self.assertTrue(anim_mgr.current_anim_path.endswith("cat_custom_test_skin.svg"))

        # Очистка
        if os.path.exists(test_svg_path):
            os.remove(test_svg_path)
        if "custom_test_skin" in CAT_SKINS:
            del CAT_SKINS["custom_test_skin"]

    def test_delete_custom_skin(self):
        # 1. Подготовка тестового окружения
        from src.utils.bonding_utils import CAT_SKINS
        from src.utils.paths import ANIMATIONS_DIR
        from src.ui.settings_dialog import SettingsDialog
        from PySide6.QtWidgets import QMessageBox

        config = ConfigManager(self.config_path)
        config.set("skin", "custom_todel_skin")
        config.set("custom_skins", {"custom_todel_skin": "Удаляемый Скин"})
        CAT_SKINS["custom_todel_skin"] = "Удаляемый Скин"

        test_svg_dir = os.path.join(ANIMATIONS_DIR, "svg_skins")
        os.makedirs(test_svg_dir, exist_ok=True)
        test_svg_path = os.path.join(test_svg_dir, "cat_custom_todel_skin.svg")
        with open(test_svg_path, "w", encoding="utf-8") as f:
            f.write("<svg></svg>")

        self.assertTrue(os.path.exists(test_svg_path))

        # 2. Мокаем QMessageBox.question и QMessageBox.information с try...finally для безопасности
        original_question = QMessageBox.question
        original_information = QMessageBox.information
        QMessageBox.question = MagicMock(return_value=QMessageBox.Yes)
        QMessageBox.information = MagicMock()

        try:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication([])

            # 3. Создаем диалог и проверяем, что кнопка удаления активна для этого скина
            dialog = SettingsDialog(config)
            self.assertEqual(dialog.skin_combo.currentData(), "custom_todel_skin")
            self.assertTrue(dialog.delete_btn.isEnabled())

            # 4. Вызываем удаление скина
            dialog.delete_custom_skin()

            # 5. Проверяем результаты
            self.assertFalse(os.path.exists(test_svg_path))
            self.assertNotIn("custom_todel_skin", CAT_SKINS)
            self.assertEqual(config.get("skin"), "default")
            self.assertNotIn("custom_todel_skin", config.get("custom_skins") or {})
        finally:
            # Восстанавливаем моки гарантированно
            QMessageBox.question = original_question
            QMessageBox.information = original_information

    def test_datastore_reset(self):
        db = DataStore(self.db_path)
        # Наполняем тестовыми данными
        db.log_event("test_event", "test_description")
        db.increment_stat("test_stat", 10)
        db.add_achievement("test_ach")

        # Проверяем, что данные записались
        self.assertEqual(len(db.get_recent_activity(5)), 1)
        self.assertEqual(db.get_stat("test_stat"), 10)
        self.assertIn("test_ach", db.get_unlocked_achievements())

        # Выполняем сброс
        db.reset_all_data()

        # Проверяем чистоту
        self.assertEqual(len(db.get_recent_activity(5)), 0)
        self.assertEqual(db.get_stat("test_stat"), 0)
        self.assertEqual(len(db.get_unlocked_achievements()), 0)
        db.close()

    def test_input_manager_reset(self):
        mock_window = MagicMock()
        mock_window.animation_manager.current_state = "eating"
        mock_cursor = MagicMock()
        mock_cursor.pos.return_value = QPoint(100, 100)
        mock_window.cursor.return_value = mock_cursor

        db = DataStore(self.db_path)
        im = InputManager(mock_window, db)

        # Симулируем активность
        im.last_affection_points = 50
        im.pending_points = 5
        im.max_kps = 10
        im.total_clicks_cache = 100
        im.pending_stats["total_clicks"] = 20
        im.unlocked_achievements = ["first_friend"]
        im.forced_state_name = "eating"
        im.forced_state_expires = time.time() + 10

        # Сбрасываем все данные
        im.reset_all_data()

        # Проверяем, что в памяти всё обнулилось
        self.assertEqual(im.last_affection_points, 0)
        self.assertEqual(im.pending_points, 0)
        self.assertEqual(im.max_kps, 0)
        self.assertEqual(im.total_clicks_cache, 0)
        self.assertEqual(im.pending_stats["total_clicks"], 0)
        self.assertEqual(len(im.unlocked_achievements), 0)
        self.assertIsNone(im.forced_state_name)
        mock_window.animation_manager.play_state.assert_called_with("idle", force=True)

        db.close()

    def test_stats_dialog_reset_with_mock_msgbox(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
        from src.ui.stats_dialog import StatsDialog
        app = QApplication.instance() or QApplication([])

        # Создаем реальный QWidget в качестве родителя, чтобы избежать ошибки типов в PySide
        parent_widget = QWidget()
        parent_widget.animation_manager = MagicMock()
        parent_widget.animation_manager.current_state = "idle"

        db = DataStore(self.db_path)
        im = InputManager(parent_widget, db)
        parent_widget.input_manager = im

        # Симулируем данные
        im.last_affection_points = 100
        im.pending_points = 50
        im.unlocked_achievements = ["first_friend"]

        dialog = StatsDialog(db, parent=parent_widget)

        # Мокаем QMessageBox для симуляции согласия пользователя на сброс
        original_question = QMessageBox.question
        original_information = QMessageBox.information
        QMessageBox.question = MagicMock(return_value=QMessageBox.Yes)
        QMessageBox.information = MagicMock()

        try:
            # Вызываем сброс через диалог
            dialog.confirm_and_reset()

            # Проверяем, что вызвался сброс у InputManager и обновился диалог
            self.assertEqual(im.last_affection_points, 0)
            self.assertEqual(im.pending_points, 0)
            self.assertEqual(dialog.points_label.text(), "Всего: 0 ❤️")
        finally:
            QMessageBox.question = original_question
            QMessageBox.information = original_information

        db.close()

    def test_sound_manager_volume_override(self):
        from src.utils.sound_manager import SoundManager
        from PySide6.QtMultimedia import QSoundEffect

        config = ConfigManager(self.config_path)
        config.set("volume", 50)
        sm = SoundManager(config)

        # Создаем фиктивный QSoundEffect
        mock_effect = MagicMock(spec=QSoundEffect)
        sm.sounds["test_meow"] = mock_effect

        # Проверка воспроизведения со стандартной громкостью
        sm.play_sound("test_meow")
        mock_effect.setVolume.assert_called_with(0.5)
        mock_effect.play.assert_called()

        # Проверка воспроизведения с переопределенной громкостью
        sm.play_sound("test_meow", volume=80)
        mock_effect.setVolume.assert_called_with(0.8)

    def test_animation_manager_current_fps(self):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PySide6.QtWidgets import QApplication, QLabel
        from src.core.animation_manager import AnimationManager

        app = QApplication.instance() or QApplication([])
        label = QLabel()
        config = ConfigManager(self.config_path)
        am = AnimationManager(label, config)

        # Проверка дефолтного значения
        self.assertEqual(am.current_fps, 12)

        # Смена состояния
        am.play_state("sleeping")
        self.assertEqual(am.current_fps, 4)

        am.play_state("overheat")
        self.assertEqual(am.current_fps, 20)

        am.play_state("shaking")
        self.assertEqual(am.current_fps, 20)

        am.play_state("idle")
        self.assertEqual(am.current_fps, 12)

        # Тест кастомного FPS
        am.current_fps = 15
        self.assertEqual(am.current_fps, 15)

    def test_sound_manager_fallback(self):
        from src.utils.sound_manager import SoundManager
        from PySide6.QtMultimedia import QSoundEffect

        config = ConfigManager(self.config_path)
        sm = SoundManager(config)

        # Создаем фиктивный QSoundEffect для meow
        mock_effect = MagicMock(spec=QSoundEffect)
        sm.sounds["meow"] = mock_effect

        # Проигрываем несуществующий "happy"
        # Ожидаем, что сработает резервный meow
        sm.play_sound("happy")
        mock_effect.play.assert_called()

    def test_data_store_reset_logic(self):
        db = DataStore(self.db_path)
        db.log_event("test_event", "test_description")
        db.add_achievement("test_ach")
        db.increment_stat("total_clicks", 100)

        # Сбрасываем все данные
        db.reset_all_data()

        # Проверяем, что логи и ачивки удалены, а статы сброшены в 0
        self.assertEqual(db.get_stat("total_clicks"), 0)
        self.assertEqual(len(db.get_unlocked_achievements()), 0)

        # Должен остаться только один лог события сброса
        recent = db.get_recent_activity()
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0][2], "stats_reset")

        db.close()

    def test_input_manager_reset_logic(self):
        mock_window = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.pos.return_value = QPoint(100, 100)
        mock_window.cursor.return_value = mock_cursor

        db = DataStore(self.db_path)
        im = InputManager(mock_window, db)

        # Накапливаем данные в памяти
        im.last_affection_points = 50
        im.pending_points = 10
        im.pending_stats["total_clicks"] = 5
        im.unlocked_achievements = ["first_friend"]
        im.points_time_accumulator = 1.5
        im.work_time_accumulator = 1.0

        # Сбрасываем через менеджер
        im.reset_all_data()

        # Проверяем сброс в памяти
        self.assertEqual(im.last_affection_points, 0)
        self.assertEqual(im.pending_points, 0)
        self.assertEqual(im.pending_stats["total_clicks"], 0)
        self.assertEqual(len(im.unlocked_achievements), 0)
        self.assertEqual(im.points_time_accumulator, 0.0)
        self.assertEqual(im.work_time_accumulator, 0.0)

        # Проверяем сброс в БД
        self.assertEqual(db.get_affection_points(), 0)

        db.close()

    def test_stats_dialog_reset_ui_flow(self):
        from src.ui.stats_dialog import StatsDialog
        from PySide6.QtWidgets import QMessageBox, QApplication

        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication.instance() or QApplication([])

        # Подготовка данных
        db = DataStore(self.db_path)
        db.log_event("test_event", "test")
        db.add_affection_points(150)

        dialog = StatsDialog(db)

        # Мокаем QMessageBox.question и QMessageBox.information
        original_question = QMessageBox.question
        original_information = QMessageBox.information
        QMessageBox.question = MagicMock(return_value=QMessageBox.No)
        QMessageBox.information = MagicMock()

        try:
            # 1. Сценарий отказа (No)
            dialog.confirm_reset()
            self.assertEqual(db.get_affection_points(), 150)

            # 2. Сценарий подтверждения (Yes)
            QMessageBox.question = MagicMock(return_value=QMessageBox.Yes)
            dialog.confirm_reset()
            self.assertEqual(db.get_affection_points(), 0)
            QMessageBox.information.assert_called_once()
        finally:
            QMessageBox.question = original_question
            QMessageBox.information = original_information
            db.close()

if __name__ == '__main__':
    unittest.main()
