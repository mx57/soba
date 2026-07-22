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
        self.always_on_top_cb = QCheckBox("Поверх всех окон")
        self.always_on_top_cb.setChecked(self.config.get("always_on_top"))
        layout.addWidget(self.always_on_top_cb)

        # Громкость
        layout.addWidget(QLabel("Громкость звука:"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.config.get("volume"))
        layout.addWidget(self.volume_slider)

        # Прозрачность
        layout.addWidget(QLabel("Прозрачность окна:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(self.config.get("opacity"))
        layout.addWidget(self.opacity_slider)

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
        self.skin_combo = QComboBox()
        for skin_id, skin_name in CAT_SKINS.items():
            self.skin_combo.addItem(skin_name, skin_id)

        index = self.skin_combo.findData(self.config.get("skin"))
        if index >= 0:
            self.skin_combo.setCurrentIndex(index)
        layout.addWidget(self.skin_combo)

        # Кнопки
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def save_settings(self):
        self.config.set("username", self.name_edit.text())
        self.config.set("always_on_top", self.always_on_top_cb.isChecked())
        self.config.set("volume", self.volume_slider.value())
        self.config.set("opacity", self.opacity_slider.value())
        self.config.set("stretch_interval", self.stretch_spin.value())
        self.config.set("pomodoro_work", self.pomodoro_work_spin.value())
        self.config.set("pomodoro_break", self.pomodoro_break_spin.value())
        self.config.set("skin", self.skin_combo.currentData())
        self.accept()
