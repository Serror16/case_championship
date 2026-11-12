"""Calendar and time settings for the Chukotka pilot."""
from datetime import date, timedelta, timezone

TZ = timezone(timedelta(hours=12))
FIRST, LAST = date(2026, 1, 1), date(2026, 12, 31)
HORIZONS = {"48ч": 48, "72ч": 72, "7сут": 168}
MAX_HORIZON_HOURS = 168
TRANSFER_MINUTES = 90
SEASONS = {
    "Зима": {12, 1, 2, 3},
    "Весеннее межсезонье": {4, 5},
    "Лето": {6, 7, 8, 9},
    "Осеннее межсезонье": {10, 11},
}
SEASON_ORDER = list(SEASONS)


def horizon_key(hours: int) -> str:
    if type(hours) is not int or not 1 <= hours <= MAX_HORIZON_HOURS:
        raise ValueError("Порог H должен быть целым числом часов от 1 до 168")
    return next((key for key, value in HORIZONS.items() if value == hours), f"{hours}ч")


def season_for(day: date) -> str:
    return next(name for name, months in SEASONS.items() if day.month in months)
