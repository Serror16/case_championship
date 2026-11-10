"""Selected coastal, ferry, local access, and ice-road events."""
from __future__ import annotations
from datetime import date, datetime, time, timedelta
import air

PORT_SCHEDULE = "https://app.morport-anadyr.ru/uploads/Raspisanie_Kapitan_Sotnikov_2026_f8b58ccb20.pdf"
FERRY_SCHEDULE = "https://app.morport-anadyr.ru/uploads/Raspisanie_katera_Kamchatka_2026_756c391415.pdf"
TAXI_DESCRIPTION = "https://chukotka.travel/useful-info/kak-dobratsya-iz-aeroporta-do-goroda/"
ICE_OPEN = "https://chukotka-news.ru/economy/2026/02/11/16950.html"

def moment(month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=air.TZ)


def add(events: list[dict], start: datetime, origin: str, end: datetime,
        destination: str, service: str, source: str, mode: str,
        assumption: str = "") -> None:
    if start >= end or origin == destination:
        raise ValueError(f"Invalid transport leg: {origin} {start} to {destination} {end}")
    events.append({"from": origin, "to": destination, "depart": start,
                   "arrive": end, "flight": service, "source": source,
                   "date": start.date().isoformat(), "mode": mode,
                   "assumption": assumption})


def marine_events() -> list[dict]:
    """Ручной перенос окрашенных строк трёх листов утверждённого расписания."""
    events: list[dict] = []
    ana, ber, egv, pro, lav = "Анадырь", "Беринговский", "Эгвекинот", "Провидения", "Лаврентия"

    def voyage(month: int, stops: list[tuple[int, str, int, int | None]]) -> None:
        # (число, пункт, время прибытия, время отхода). У первой остановки прибытия нет.
        for (d0, p0, _a0, h0), (d1, p1, h1, _o1) in zip(stops, stops[1:]):
            if p0 == p1:
                continue
            if h0 is None or h1 is None:
                raise ValueError("A coastal leg lacks a departure or arrival time")
            add(events, moment(month, d0, h0), p0, moment(month, d1, h1), p1,
                "Капитан Сотников", PORT_SCHEDULE, "coastal_ship")

    def bering(month: int, day: int) -> None:
        voyage(month, [(day, ana, None, 21), (day+1, ber, 9, 20), (day+2, ana, 9, None)])

    def egvekinot(month: int, day: int, depart_day: int | None = None) -> None:
        depart_day = depart_day or day + 1
        voyage(month, [(day, ana, None, 17), (day+1, egv, 11, None),
                       (depart_day, egv, None, 16), (depart_day+1, ana, 9, None)])

    for d in (1, 12, 18): bering(7, d)
    for d in (4, 15): egvekinot(7, d)
    voyage(7, [(7, ana, None, 10), (8, pro, 15, 20), (9, lav, 9, 20),
               (10, pro, 9, 15), (11, ana, 21, None)])
    voyage(7, [(21, ana, None, 10), (22, pro, 15, None), (23, pro, None, 9),
               (23, lav, 20, None), (27, lav, None, 9), (27, pro, 20, None),
               (28, pro, None, 9), (29, ana, 15, None)])

    for d in (4, 12, 18, 26): bering(8, d)
    for d in (1, 15, 29): egvekinot(8, d)
    for d in (7, 21):
        voyage(8, [(d, ana, None, 10), (d+1, pro, 15, 20),
                   (d+2, lav, 9, 20), (d+3, pro, 9, 15), (d+4, ana, 21, None)])

    for d in (1, 16, 28): bering(9, d)
    for d in (4, 13): egvekinot(9, d)
    egvekinot(9, 24, depart_day=26)
    voyage(9, [(7, ana, None, 10), (8, pro, 15, 20), (9, lav, 9, 20),
               (10, pro, 9, None), (11, pro, None, 9), (12, ana, 15, None)])
    voyage(9, [(19, ana, None, 10), (20, pro, 15, 20),
               (21, lav, 9, 20), (22, pro, 9, 15), (23, ana, 21, None)])
    return events


def ferry_events() -> list[dict]:
    """Катер 18.06–05.10; 30 мин хода оценены по 07:00→07:30 в графике."""
    events: list[dict] = []
    start, end = date(2026, 6, 18), date(2026, 10, 5)
    ana, pier = "Анадырь", "Причал №10 (Угольные Копи)"
    for offset in range((end-start).days + 1):
        day = start + timedelta(days=offset)
        if day.weekday() == 5:
            city_times, pier_times = [(8, 0), (14, 0), (17, 0)], [(9, 0), (15, 0), (18, 0)]
        elif day.weekday() == 6:
            city_times, pier_times = [(18, 0)], [(19, 0)]
        else:
            city_times = [(8, 0) if day.weekday() == 2 else (7, 0),
                          (8, 0) if day.weekday() == 2 else (8, 30),
                          (11, 0), (13, 0), (15, 0), (17, 0)]
            # По средам нет 07:00, а первый рейс — 08:00.
            city_times = list(dict.fromkeys(city_times))
            pier_times = ([] if day.weekday() == 2 else [(7, 30)]) + [
                (9, 0), (12, 0), (14, 0), (16, 0), (18, 0)]
        for h, m in city_times:
            depart = datetime.combine(day, time(h, m), air.TZ)
            add(events, depart, ana, depart+timedelta(minutes=30), pier,
                "Камчатка", FERRY_SCHEDULE, "ferry", "30 минут в пути")
        for h, m in pier_times:
            depart = datetime.combine(day, time(h, m), air.TZ)
            add(events, depart, pier, depart+timedelta(minutes=30), ana,
                "Камчатка", FERRY_SCHEDULE, "ferry", "30 минут в пути")
    return events


def access_events() -> list[dict]:
    """Такси по дороге: наличие пути подтверждено; время и доступность — допущения.

    Почасовые отправления 06–20 не являются расписанием перевозчика. Они нужны для
    сценарной оценки верхней границы мультимодальной достижимости.
    """
    events: list[dict] = []
    for offset in range(365):
        day = air.FIRST + timedelta(days=offset)
        for h in range(6, 21):
            depart = datetime.combine(day, time(h), air.TZ)
            for left, right, minutes in [
                ("Анадырь", "Анадырь (Окружной)", 30),
                ("Анадырь (Окружной)", "Анадырь", 30),
            ]:
                add(events, depart, left, depart+timedelta(minutes=minutes), right,
                    "доступ к причалу/площадке", TAXI_DESCRIPTION, "taxi_assumption",
                    f"почасовая доступность 06–20, {minutes} мин — допущение")
    start, end = date(2026, 6, 18), date(2026, 10, 5)
    for offset in range((end-start).days + 1):
        day = start + timedelta(days=offset)
        for h in range(6, 21):
            depart = datetime.combine(day, time(h), air.TZ)
            for left, right in [
                ("Аэропорт Анадырь", "Причал №10 (Угольные Копи)"),
                ("Причал №10 (Угольные Копи)", "Аэропорт Анадырь"),
            ]:
                add(events, depart, left, depart+timedelta(hours=1), right,
                    "доступ к причалу/площадке", TAXI_DESCRIPTION, "taxi_assumption",
                    "почасовая доступность 06–20, 60 мин — допущение")
    return events


def ice_road_events() -> list[dict]:
    """Федеральная ледовая дорога 11.02–30.04, поездка на такси — сценарная."""
    events: list[dict] = []
    start, end = date(2026, 2, 12), date(2026, 4, 30)
    for offset in range((end-start).days + 1):
        day = start + timedelta(days=offset)
        for h in range(6, 21):
            depart = datetime.combine(day, time(h), air.TZ)
            for left, right in [("Аэропорт Анадырь", "Анадырь"),
                                ("Анадырь", "Аэропорт Анадырь")]:
                add(events, depart, left, depart+timedelta(hours=2), right,
                    "ледовая дорога + такси", ICE_OPEN, "ice_road_taxi",
                    "дорога открыта; 2 ч и почасовое такси 06–20 — допущение")
    return events
