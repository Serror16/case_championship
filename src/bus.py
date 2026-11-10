"""Selected buses and construction of the final multimodal graph."""
from __future__ import annotations
from datetime import date, datetime, time, timedelta
import air
import engine
import water_access as multi

OLD_PLACES = air.build_events(air.load_routes())[1]
NEW_PLACES = ["Билибино", "Угольные Копи"]
PLACES = sorted(set(OLD_PLACES + NEW_PLACES))
ORIGINS = PLACES + ["Анадырь"]
HORIZONS = {key: air.HORIZONS[key] for key in ("48ч", "72ч", "7сут")}

SOURCES = {
    "coal_2026_operation": "https://prochukotku.ru/news/transport/kater_kamchatka_zamenil_aeroglissery_na_pereprave_cherez_anadyrskiy_liman/",
    "coal_2025_schedule": "https://www.ks87.ru/729844.pdf",
    "coal_local_2025_report": "https://anadyr-mo.ru/filesfordownload/2026/2026-04-15_doklad-sost-konk-sredy_2025.pdf",
    "coal_local_2024_schedule": "https://xn----etbgnjdogfk9a8gl.xn--p1ai/files/head/adm-2024.01.29-09.pdf",
    "bilibino_2026_operation": "https://www.mk-chukotka.ru/social/2026/05/08/park-bilibinskogo-municipalnogo-avtopredpriyatiya-popolnilsya-novym-passazhirskim-avtobusom.html",
    "bilibino_2024_schedule": "https://poezd-avtobus.ru/rossiya/bilibino/avtobus-100-bilibino-keperveem",
    "bilibino_2026_closure": "https://prochukotku.ru/news/infrastruktura/v_bilibinskom_rayone_vosstanovili_prervannoe_pavodkom_soobshchenie_po_avtodoroge/",
}


def at(day: date, hhmm: str) -> datetime:
    return datetime.combine(day, time.fromisoformat(hhmm), air.TZ)


def bus_leg(events: list[dict], day: date, origin: str, departure: str,
            destination: str, arrival: str, service: str, source: str,
            assumption: str) -> None:
    multi.add(events, at(day, departure), origin, at(day, arrival), destination,
              service, source, "bus_schedule_proxy", assumption)


def all_stop_pairs(events: list[dict], day: date,
                   stops: list[tuple[str, str]], service: str,
                   source: str, assumption: str) -> None:
    """Прямые дуги внутри одного автобуса: не взимать 90 мин пересадки на остановке."""
    for i in range(len(stops)):
        for j in range(i + 1, len(stops)):
            a, t0 = stops[i]
            b, t1 = stops[j]
            bus_leg(events, day, a, t0, b, t1, service, source, assumption)


def coal_bus_events() -> list[dict]:
    """Маршрут № 2. Даты работы 2026; часы — официальный график 2025."""
    events: list[dict] = []
    first, last = date(2026, 6, 18), date(2026, 10, 23)
    town, airport, pier = ("Угольные Копи", "Аэропорт Анадырь",
                            "Причал №10 (Угольные Копи)")
    for offset in range((last - first).days + 1):
        day = first + timedelta(days=offset)
        if day.weekday() < 5:
            outbound = [("07:50", "08:20", "08:40"),
                        ("10:40", "11:10", "11:30"),
                        ("12:40", "13:10", "13:30"),
                        ("14:40", "15:10", "15:30"),
                        ("16:40", "17:10", "17:30")]
            inbound = [("08:50", "09:10", "09:40"),
                       ("11:50", "12:10", "12:40"),
                       ("13:50", "14:10", "14:40"),
                       ("15:50", "16:10", "16:40"),
                       ("17:50", "18:10", "18:40")]
        elif day.weekday() == 5:
            outbound = [("07:50", "08:20", "08:40"),
                        ("13:50", "14:20", "14:40"),
                        ("16:50", "17:20", "17:40")]
            inbound = [("08:50", "09:10", "09:40"),
                       ("13:50", "14:10", "14:40"),
                       ("17:50", "18:10", "18:40")]
        else:
            outbound = [("17:50", "18:20", "18:40")]
            inbound = [("18:50", "19:10", "19:40")]
        for t0, t1, t2 in outbound:
            all_stop_pairs(events, day, [(town, t0), (airport, t1), (pier, t2)],
                           "автобус № 2", SOURCES["coal_2025_schedule"],
                           "Работа в 2026 подтверждена; точные часы перенесены из 2025")
        for t0, t1, t2 in inbound:
            all_stop_pairs(events, day, [(pier, t0), (airport, t1), (town, t2)],
                           "автобус № 2", SOURCES["coal_2025_schedule"],
                           "Работа в 2026 подтверждена; точные часы перенесены из 2025")
    return events


def coal_local_bus_events() -> list[dict]:
    """Круглогодичный маршрут № 1. Официальные часы 2024 как приближение."""
    events: list[dict] = []
    weekday_out = [("07:10", "07:20"), ("08:10", "08:20"),
                   ("10:10", "10:20"), ("11:25", "11:35"),
                   ("13:40", "13:50"), ("14:50", "15:00"),
                   ("16:10", "16:20"), ("17:10", "17:20"),
                   ("19:00", "19:15"), ("20:20", "20:35")]
    weekday_back = [("07:40", "07:50"), ("08:40", "08:50"),
                    ("10:50", "11:00"), ("12:05", "12:15"),
                    ("14:15", "14:25"), ("15:20", "15:30"),
                    ("16:40", "16:50"), ("17:45", "18:00"),
                    ("19:40", "19:55"), ("21:10", "21:25")]
    sunday_out = [("08:10", "08:20"), ("12:10", "12:20"),
                  ("16:10", "16:20"), ("18:15", "18:30")]
    sunday_back = [("08:40", "08:50"), ("12:50", "13:00"),
                   ("16:40", "16:50"), ("18:55", "19:10")]
    town, airport = "Угольные Копи", "Аэропорт Анадырь"
    for offset in range(365):
        day = air.FIRST + timedelta(days=offset)
        out, back = ((sunday_out, sunday_back) if day.weekday() == 6
                     else (weekday_out, weekday_back))
        for t0, t1 in out:
            bus_leg(events, day, town, t0, airport, t1, "автобус № 1",
                    SOURCES["coal_local_2024_schedule"],
                    "Круглогодичная работа в 2025; часы 2024; статус 2026 не подтверждён")
        for t0, t1 in back:
            bus_leg(events, day, airport, t0, town, t1, "автобус № 1",
                    SOURCES["coal_local_2024_schedule"],
                    "Круглогодичная работа в 2025; часы 2024; статус 2026 не подтверждён")
    return events


def bilibino_bus_events() -> list[dict]:
    """Маршрут № 100. Работа 2026 подтверждена; часы 2024, 60 мин — допущение."""
    events: list[dict] = []
    for offset in range(365):
        day = air.FIRST + timedelta(days=offset)
        if day == date(2026, 8, 17):
            continue  # дорога закрыта с 11:00; утренние часы тоже не восстанавливаем
        if day.weekday() == 6:
            outbound = ["07:56", "16:56"]
            inbound = ["09:10", "18:10"]
        elif day.weekday() == 5:
            outbound = ["07:56", "12:56", "16:56"]
            inbound = ["09:10", "14:00", "18:10"]
        else:
            outbound = ["07:56", "12:56", "16:56"]
            inbound = ["09:20", "14:00", "18:10"]
        if day == date(2026, 8, 18):
            outbound = [x for x in outbound if x >= "12:00"]
            inbound = [x for x in inbound if x >= "12:00"]
        for clock in outbound:
            departure = at(day, clock)
            multi.add(events, departure, "Билибино", departure + timedelta(hours=1),
                      "Кепервеем", "автобус № 100", SOURCES["bilibino_2024_schedule"],
                      "bus_schedule_proxy",
                      "Работа в 2026 подтверждена; часы 2024, путь 60 мин — допущение")
        for clock in inbound:
            departure = at(day, clock)
            multi.add(events, departure, "Кепервеем", departure + timedelta(hours=1),
                      "Билибино", "автобус № 100", SOURCES["bilibino_2024_schedule"],
                      "bus_schedule_proxy",
                      "Работа в 2026 подтверждена; часы 2024, путь 60 мин — допущение")
    return events


def prepare() -> tuple[list, list, dict, list, list, dict]:
    air_events, air_places = air.build_events(air.load_routes())
    if air_places != OLD_PLACES or len(OLD_PLACES) != 34:
        raise ValueError("The reviewed flight settlement set has changed")
    base_access = [e for e in multi.access_events()
                   if {e["from"], e["to"]} !=
                   {"Аэропорт Анадырь", "Причал №10 (Угольные Копи)"}]
    coal = coal_bus_events()
    coal_local = coal_local_bus_events()
    bilibino = bilibino_bus_events()
    network = (air_events + multi.marine_events() + multi.ferry_events()
               + base_access + multi.ice_road_events() + coal + coal_local + bilibino)
    network.sort(key=lambda e: e["depart"])
    nodes = sorted({p for e in network for p in (e["from"], e["to"])})
    indexes = {node: i for i, node in enumerate(nodes)}
    compact = [(indexes[e["from"]], indexes[e["to"]],
                int((e["depart"]-engine.EPOCH).total_seconds()//60),
                int((e["arrive"]-engine.EPOCH).total_seconds()//60))
               for e in network]
    return network, nodes, indexes, compact, [e[2] for e in compact], {
        "coal_bus_events": len(coal),
        "coal_local_bus_events": len(coal_local),
        "bilibino_bus_events": len(bilibino),
        "airport_pier_taxi_events_removed": 2 * 15 * 110,
    }
