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
    "first_friend": {"title": "Первый друг", "desc": "Достигните 1 уровня привязанности", "icon": "❤️", "goal": 1, "stat": "level"},
    "worker": {"title": "Трудоголик", "desc": "Проведите 10 минут в режиме работы", "icon": "🛠", "goal": 600, "stat": "work_seconds"},
    "hunter": {"title": "Охотник", "desc": "Поймайте курсор 10 раз", "icon": "🎯", "goal": 10, "stat": "cursor_catches"},
    "gourmet": {"title": "Гурман", "desc": "Покормите котика 5 раз", "icon": "🐟", "goal": 5, "stat": "total_feedings"},
    "clicker": {"title": "Кликер", "desc": "Нажмите 1000 клавиш", "icon": "⌨️", "goal": 1000, "stat": "total_clicks"},
    "speed_demon": {"title": "Демон скорости", "desc": "Достигните скорости печати 15 кл/сек", "icon": "⚡", "goal": 15, "stat": "max_kps"},
    "pomodoro_master": {"title": "Мастер Pomodoro", "desc": "Завершите 5 сессий Pomodoro", "icon": "🍎", "goal": 5, "stat": "pomodoros_completed"},
    "shake_it": {"title": "Встряска", "desc": "Встряхните котика 10 раз", "icon": "🌪", "goal": 10, "stat": "shakes_count"},
    "pet_lover": {"title": "Любимец", "desc": "Погладьте котика 50 раз", "icon": "🐾", "goal": 50, "stat": "petting_count"},
    "marathoner": {"title": "Марафонец", "desc": "Проработайте 1 час суммарно", "icon": "🏆", "goal": 3600, "stat": "work_seconds"}
}

def check_achievements(stats, unlocked_ids):
    """
    Проверяет условия достижений на основе словаря статистик.
    stats должен содержать все необходимые ключи (bonding_points, work_seconds, и т.д.)
    """
    new_unlocked = []

    # Расчет уровня для проверки first_friend
    current_level = get_level(stats.get("bonding_points", 0))

    for ach_id, info in ACHIEVEMENTS.items():
        if ach_id in unlocked_ids:
            continue

        stat_value = stats.get(info["stat"], 0)

        # Специальный случай для уровня
        if info["stat"] == "level":
            stat_value = current_level

        if stat_value >= info["goal"]:
            new_unlocked.append(ach_id)

    return new_unlocked
