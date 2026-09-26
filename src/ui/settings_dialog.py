from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSlider, QComboBox, QPushButton, QSpinBox, QCheckBox
from PySide6.QtCore import Qt
from src.utils.bonding_utils import CAT_SKINS

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Настройки Котика")
        self.setFixedWidth(300)

        layout = QVBoxLayout(self)

        # Имя пользователя
        layout.addWidget(QLabel("Имя пользователя:"))
        self.name_edit = QLineEdit(self.config.get("username"))
        layout.addWidget(self.name_edit)

        # Поверх всех окон
        self.always_on_top_check = QCheckBox("Поверх всех окон")
        self.always_on_top_check.setChecked(self.config.get("always_on_top"))
        layout.addWidget(self.always_on_top_check)

        # Громкость
        volume_header_layout = QHBoxLayout()
        volume_header_layout.addWidget(QLabel("Громкость звука:"))
        self.volume_val_label = QLabel(f"{self.config.get('volume')}%")
        self.volume_val_label.setStyleSheet("font-weight: bold; color: #555;")
        volume_header_layout.addStretch()
        volume_header_layout.addWidget(self.volume_val_label)
        layout.addLayout(volume_header_layout)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.config.get("volume"))
        self.volume_slider.valueChanged.connect(lambda v: self.volume_val_label.setText(f"{v}%"))
        self.volume_slider.sliderReleased.connect(self.play_test_sound)
        layout.addWidget(self.volume_slider)

        # Прозрачность
        opacity_header_layout = QHBoxLayout()
        opacity_header_layout.addWidget(QLabel("Прозрачность окна:"))
        self.opacity_val_label = QLabel(f"{self.config.get('opacity')}%")
        self.opacity_val_label.setStyleSheet("font-weight: bold; color: #555;")
        opacity_header_layout.addStretch()
        opacity_header_layout.addWidget(self.opacity_val_label)
        layout.addLayout(opacity_header_layout)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(self.config.get("opacity"))
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_val_label.setText(f"{v}%"))
        layout.addWidget(self.opacity_slider)

        # Размер питомца
        size_header_layout = QHBoxLayout()
        size_header_layout.addWidget(QLabel("Размер питомца (px):"))
        pet_size_val = self.config.get("pet_size") or 100
        self.size_val_label = QLabel(f"{pet_size_val}px")
        self.size_val_label.setStyleSheet("font-weight: bold; color: #555;")
        size_header_layout.addStretch()
        size_header_layout.addWidget(self.size_val_label)
        layout.addLayout(size_header_layout)

        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(50, 250)
        self.size_slider.setValue(pet_size_val)
        self.size_slider.valueChanged.connect(lambda v: self.size_val_label.setText(f"{v}px"))
        layout.addWidget(self.size_slider)

        # Интервал растяжки
        layout.addWidget(QLabel("Интервал растяжки (мин):"))
        self.stretch_spin = QSpinBox()
        self.stretch_spin.setRange(5, 120)
        self.stretch_spin.setValue(self.config.get("stretch_interval"))
        layout.addWidget(self.stretch_spin)

        # Интервалы Pomodoro
        layout.addWidget(QLabel("Pomodoro: работа (мин):"))
        self.pomodoro_work_spin = QSpinBox()
        self.pomodoro_work_spin.setRange(1, 60)
        self.pomodoro_work_spin.setValue(self.config.get("pomodoro_work"))
        layout.addWidget(self.pomodoro_work_spin)

        layout.addWidget(QLabel("Pomodoro: отдых (мин):"))
        self.pomodoro_break_spin = QSpinBox()
        self.pomodoro_break_spin.setRange(1, 30)
        self.pomodoro_break_spin.setValue(self.config.get("pomodoro_break"))
        layout.addWidget(self.pomodoro_break_spin)

        # Выбор скина
        layout.addWidget(QLabel("Окрас котика:"))
        skin_layout = QHBoxLayout()
        self.skin_combo = QComboBox()
        self.populate_skins()
        skin_layout.addWidget(self.skin_combo)

        import_btn = QPushButton("Импорт...")
        import_btn.clicked.connect(self.import_custom_skin)
        skin_layout.addWidget(import_btn)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.delete_custom_skin)
        skin_layout.addWidget(self.delete_btn)
        layout.addLayout(skin_layout)

        # Подключаем отслеживание смены скина для управления доступностью кнопки "Удалить"
        self.skin_combo.currentIndexChanged.connect(self.on_skin_changed)
        self.on_skin_changed()

        # Кнопки
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def play_test_sound(self):
        # Если есть родительское окно с менеджером звуков, проигрываем звук через него
        parent = self.parent()
        if parent and hasattr(parent, "sound_manager") and parent.sound_manager:
            parent.sound_manager.play_sound("meow", volume=self.volume_slider.value())

    def on_skin_changed(self, index=0):
        current_skin_id = self.skin_combo.currentData()
        is_custom = bool(current_skin_id and current_skin_id.startswith("custom_"))
        self.delete_btn.setEnabled(is_custom)

    def delete_custom_skin(self):
        from PySide6.QtWidgets import QMessageBox
        import os
        from src.utils.paths import ANIMATIONS_DIR
        from src.utils.bonding_utils import CAT_SKINS

        skin_id = self.skin_combo.currentData()
        if not skin_id or not skin_id.startswith("custom_"):
            return

        skin_name = self.skin_combo.currentText()
        reply = QMessageBox.question(
            self,
            "Удалить окрас",
            f"Вы уверены, что хотите удалить окрас '{skin_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        # 1. Сброс текущей конфигурации скина, если мы удаляем активный скин
        if self.config.get("skin") == skin_id:
            self.config.set("skin", "default")

        # 2. Удаление из настроек custom_skins
        custom_skins = self.config.get("custom_skins") or {}
        if skin_id in custom_skins:
            del custom_skins[skin_id]
            self.config.set("custom_skins", custom_skins)

        # 3. Удаление из глобального словаря CAT_SKINS
        if skin_id in CAT_SKINS:
            del CAT_SKINS[skin_id]

        # 4. Физическое удаление файла с диска
        svg_path = os.path.join(ANIMATIONS_DIR, "svg_skins", f"cat_{skin_id}.svg")
        if os.path.exists(svg_path):
            try:
                os.remove(svg_path)
            except Exception as e:
                print(f"Error deleting file {svg_path}: {e}")

        # 5. Обновление комбобокса в диалоге
        self.populate_skins()
        self.on_skin_changed()

        QMessageBox.information(self, "Успех", f"Окрас '{skin_name}' успешно удален.")

    def save_settings(self):
        self.config.set("username", self.name_edit.text())
        self.config.set("always_on_top", self.always_on_top_check.isChecked())
        self.config.set("volume", self.volume_slider.value())
        self.config.set("opacity", self.opacity_slider.value())
        self.config.set("pet_size", self.size_slider.value())
        self.config.set("stretch_interval", self.stretch_spin.value())
        self.config.set("pomodoro_work", self.pomodoro_work_spin.value())
        self.config.set("pomodoro_break", self.pomodoro_break_spin.value())
        self.config.set("skin", self.skin_combo.currentData())
        self.accept()

    def populate_skins(self):
        self.skin_combo.clear()
        for skin_id, skin_name in CAT_SKINS.items():
            self.skin_combo.addItem(skin_name, skin_id)
        index = self.skin_combo.findData(self.config.get("skin"))
        if index >= 0:
            self.skin_combo.setCurrentIndex(index)

    def import_custom_skin(self):
        from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox
        import shutil
        import os
        import time
        from src.utils.paths import ANIMATIONS_DIR
        from src.utils.bonding_utils import CAT_SKINS

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать файл SVG скина",
            "",
            "Векторная графика (*.svg)"
        )
        if not file_path:
            return

        # Валидация файла
        if not file_path.lower().endswith(".svg"):
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите файл в формате .svg.")
            return

        # Проверка структуры (простая)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(1024)
                if "<svg" not in content.lower():
                    QMessageBox.warning(self, "Ошибка", "Выбранный файл не является валидным SVG.")
                    return
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать файл: {e}")
            return

        # Спрашиваем название окраса
        default_name = os.path.splitext(os.path.basename(file_path))[0].capitalize()
        name, ok = QInputDialog.getText(
            self,
            "Импорт скина",
            "Введите название для нового окраса:",
            text=default_name
        )
        if not ok or not name.strip():
            return

        name = name.strip()

        # Генерация ID
        safe_name = "".join([c for c in name if c.isalnum() or c in ("_", "-")]).lower()
        if not safe_name:
            safe_name = "skin"
        skin_id = f"custom_{safe_name}_{int(time.time())}"

        # Копирование файла
        dest_dir = os.path.join(ANIMATIONS_DIR, "svg_skins")
        os.makedirs(dest_dir, exist_ok=True)
        dest_path = os.path.join(dest_dir, f"cat_{skin_id}.svg")

        try:
            shutil.copy(file_path, dest_path)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось скопировать файл: {e}")
            return

        # Сохранение в конфигурации
        custom_skins = self.config.get("custom_skins") or {}
        custom_skins[skin_id] = name
        self.config.set("custom_skins", custom_skins)

        # Регистрация в глобальном словаре
        CAT_SKINS[skin_id] = name

        # Обновление выпадающего списка и выбор нового скина
        self.populate_skins()
        new_index = self.skin_combo.findData(skin_id)
        if new_index >= 0:
            self.skin_combo.setCurrentIndex(new_index)

        QMessageBox.information(self, "Успех", f"Скин '{name}' успешно импортирован!")
