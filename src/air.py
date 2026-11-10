"""Selected 2026 ChukotAVIA flights and shared calendar constants."""
from __future__ import annotations
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "date"
SOURCE_URLS = {
    "512": "https://chukotavia.ru/ru/article/view/id/512/",
    "513": "https://chukotavia.ru/ru/article/view/id/513/",
    "514": "https://chukotavia.ru/ru/article/view/id/514/",
}
TECHNICAL_NODES = {"Аэропорт Анадырь", "Анадырь (Окружной)"}
TZ = timezone(timedelta(hours=12))
FIRST, LAST = date(2026, 1, 1), date(2026, 12, 31)
HORIZONS = {"48ч": 48, "72ч": 72, "7сут": 168}
TRANSFER_MINUTES = 90
MONTHS = {f"{m:02d}" for m in range(1, 13)}
SEASONS = {
    "Зима": {12, 1, 2, 3},
    "Весеннее межсезонье": {4, 5},
    "Лето": {6, 7, 8, 9},
    "Осеннее межсезонье": {10, 11},
}
SEASON_ORDER = list(SEASONS)

def parse_dates(raw: str, prior: dict[str, list[date]]) -> list[date]:
    if raw.startswith("="):
        return prior[raw[1:]].copy()
    dates = []
    for chunk in raw.split(";"):
        month, day_list = chunk.split(":")
        if month not in MONTHS:
            raise ValueError(f"Invalid month in flight dates: {chunk}")
        for day in day_list.split(","):
            dates.append(date(2026, int(month), int(day)))
    if not dates or len(dates) != len(set(dates)):
        raise ValueError(f"Empty or repeated flight dates: {raw}")
    return sorted(dates)


def parse_time(value: str) -> time:
    hour, minute = map(int, value.split(":"))
    return time(hour, minute)


def parse_stops(raw: str) -> list[dict]:
    stops = []
    for chunk in raw.split(">"):
        place, times = chunk.split("@")
        if "/" in times:
            arrival, departure = times.split("/")
        else:
            arrival = departure = times
        stops.append({
            "place": place,
            "arrive": parse_time(arrival),
            "depart": parse_time(departure),
        })
    if len(stops) < 2:
        raise ValueError(f"A flight needs at least two stops: {raw}")
    return stops


def load_routes() -> list[dict]:
    routes = []
    prior: dict[str, list[date]] = {}
    for line_number, raw in enumerate((DATA_DIR / "routes_2026.txt").read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        source, flight, dates_raw, stops_raw = raw.split("|")
        if source not in SOURCE_URLS:
            raise ValueError(f"Unknown source on line {line_number}: {source}")
        key = f"{source}:{flight}"
        if key in prior:
            raise ValueError(f"Repeated flight ID on line {line_number}: {key}")
        dates = parse_dates(dates_raw, prior)
        stops = parse_stops(stops_raw)
        for left, right in zip(stops, stops[1:]):
            if left["depart"] >= right["arrive"]:
                raise ValueError(f"Flight {key} on line {line_number} needs an explicit date change between stops")
        prior[key] = dates
        routes.append({
            "source": source, "flight": flight, "dates": dates,
            "stops": stops, "line": line_number,
        })
    control_counts = {
        ("512", "АД113"): 57, ("512", "АД117"): 60,
        ("512", "АД15"): 29, ("512", "АД21"): 26,
        ("513", "АД11"): 210, ("513", "АД3"): 29,
        ("513", "АД7"): 49, ("513", "АД49"): 7,
        ("514", "АД31"): 26, ("514", "АД33"): 10,
        ("514", "АД75"): 18, ("514", "АД77"): 22,
        ("514", "АД53"): 19, ("514", "АД59"): 12,
        ("514", "АД61"): 16, ("514", "АД63"): 15,
        ("514", "АД90"): 25, ("514", "АД71"): 21,
        ("514", "АД67"): 20,
    }
    observed = {(route["source"], route["flight"]): len(route["dates"]) for route in routes}
    for key, expected in control_counts.items():
        if observed.get(key) != expected:
            raise ValueError(f"Flight {key}: expected {expected} dates, found {observed.get(key)}")
    return routes


def build_events(routes: list[dict]) -> tuple[list[dict], list[str]]:
    events = []
    places = sorted({
        stop["place"] for route in routes for stop in route["stops"]
        if stop["place"] not in TECHNICAL_NODES
    })
    for route in routes:
        for day in route["dates"]:
            stops = route["stops"]
            for i, origin in enumerate(stops[:-1]):
                for destination in stops[i + 1:]:
                    if origin["place"] == destination["place"]:
                        continue
                    depart = datetime.combine(day, origin["depart"], TZ)
                    arrive = datetime.combine(day, destination["arrive"], TZ)
                    if depart >= arrive:
                        raise ValueError(f"Invalid flight chronology: {route['flight']} on {day}")
                    events.append({
                        "from": origin["place"], "to": destination["place"],
                        "depart": depart, "arrive": arrive, "flight": route["flight"],
                        "source": route["source"], "date": day.isoformat(),
                        "boarding_stop": i,
                    })
    events.sort(key=lambda x: x["depart"])
    if len(places) <= 4:
        raise ValueError("Too few settlements parsed from the flight input")
    return events, places
def season_for(day: date) -> str:
    return next(name for name, months in SEASONS.items() if day.month in months)
