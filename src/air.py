"""Calendar and time settings for the Chukotka pilot."""
from datetime import date, timedelta, timezone

TZ = timezone(timedelta(hours=12))
FIRST, LAST = date(2026, 1, 1), date(2026, 12, 31)
HORIZONS = {"48ч": 48, "72ч": 72, "7сут": 168}
TRANSFER_MINUTES = 90
SEASONS = {
    "Зима": {12, 1, 2, 3},
    "Весеннее межсезонье": {4, 5},
    "Лето": {6, 7, 8, 9},
    "Осеннее межсезонье": {10, 11},
}
SEASON_ORDER = list(SEASONS)


def season_for(day: date) -> str:
    return next(name for name, months in SEASONS.items() if day.month in months)
