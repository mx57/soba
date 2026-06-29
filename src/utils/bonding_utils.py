def get_level_info(points):
    """
    Возвращает информацию об уровне на основе очков привязанности.
    Returns: (level, title, points_in_level, points_for_next_level)
    """
    thresholds = [
        (0, "Знакомый"),
        (100, "Приятель"),
        (250, "Друг"),
        (500, "Верный спутник"),
        (1000, "Лучший друг"),
        (2500, "Родственная душа")
    ]

    current_level = 0
    current_title = thresholds[0][1]
    next_threshold = None

    for i, (threshold, title) in enumerate(thresholds):
        if points >= threshold:
            current_level = i
            current_title = title
            if i + 1 < len(thresholds):
                next_threshold = thresholds[i+1][0]
            else:
                next_threshold = None
        else:
            break

    if next_threshold is None:
        # Максимальный уровень достигнут
        return current_level, current_title, points - thresholds[-1][0], 0

    prev_threshold = thresholds[current_level][0]
    points_in_level = points - prev_threshold
    points_for_next_level = next_threshold - prev_threshold

    return current_level, current_title, points_in_level, points_for_next_level

def get_level(points):
    level, _, _, _ = get_level_info(points)
    return level

ACHIEVEMENTS = {
    "first_friend": {"title": "Первый друг", "desc": "Достигните 1 уровня привязанности", "icon": "❤️"},
    "worker": {"title": "Трудоголик", "desc": "Проведите 10 минут в режиме работы", "icon": "🛠"},
    "hunter": {"title": "Охотник", "desc": "Поймайте курсор 10 раз", "icon": "🎯"},
    "gourmet": {"title": "Гурман", "desc": "Покормите котика 5 раз", "icon": "🐟"},
    "clicker": {"title": "Кликер", "desc": "Нажмите 1000 клавиш", "icon": "⌨️"}
}

def check_achievements(db, unlocked_ids):
    """Проверяет условия достижений и возвращает список новых открытых ID."""
    new_unlocked = []

    # 1. Первый друг
    if "first_friend" not in unlocked_ids:
        if get_level(db.get_affection_points()) >= 1:
            new_unlocked.append("first_friend")

    # 2. Трудоголик (10 мин = 600 сек)
    if "worker" not in unlocked_ids:
        if db.get_stat("work_seconds") >= 600:
            new_unlocked.append("worker")

    # 3. Охотник (10 поимок)
    if "hunter" not in unlocked_ids:
        if db.get_stat("cursor_catches") >= 10:
            new_unlocked.append("hunter")

    # 4. Гурман (5 кормлений)
    if "gourmet" not in unlocked_ids:
        if db.get_stat("total_feedings") >= 5:
            new_unlocked.append("gourmet")

    # 5. Кликер (1000 нажатий)
    if "clicker" not in unlocked_ids:
        if db.get_stat("total_clicks") >= 1000:
            new_unlocked.append("clicker")

    return new_unlocked
