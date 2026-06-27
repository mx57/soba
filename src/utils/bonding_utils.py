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
