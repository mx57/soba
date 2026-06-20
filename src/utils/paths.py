import os

# Базовые директории
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ANIMATIONS_DIR = os.path.join(ASSETS_DIR, "animations")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

# Пути к файлам
TRAY_ICON_PATH = os.path.join(ICONS_DIR, "tray_icon.png")

def get_animation_path(pet_type, state, index=None):
    if index:
        filename = f"{pet_type}_{state}_{index}.gif"
    else:
        filename = f"{pet_type}_{state}.gif"
    return os.path.join(ANIMATIONS_DIR, filename)
