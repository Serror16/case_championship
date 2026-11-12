"""Temporary route changes for the interactive index demonstration."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timedelta

import air
import bus

REGION = "Чукотка"
MAX_ADDITIONS = 30


def group_id(event: dict) -> str:
    key = [event["from"], event["to"], event["mode"], event["flight"]]
    payload = json.dumps(key, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def catalog(events: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for event in events:
        key = group_id(event)
        if key not in groups:
            groups[key] = {
                "id": key, "origin": event["from"], "destination": event["to"],
                "mode": event["mode"], "service": event["flight"],
                "source_id": event["source_id"], "count": 0,
            }
        groups[key]["count"] += 1
    return sorted(groups.values(), key=lambda row: (row["origin"], row["destination"], row["service"]))


def _new_events(item: dict, nodes: set[str], number: int) -> list[dict]:
    if not isinstance(item, dict):
        raise ValueError("Некорректное описание нового маршрута")
    origin, destination = item.get("origin"), item.get("destination")
    if origin not in nodes or destination not in nodes or origin == destination:
        raise ValueError("Выберите два разных пункта из списка")
    try:
        first = date.fromisoformat(item["first_date"])
        last = date.fromisoformat(item.get("last_date") or item["first_date"])
        departure_time = time.fromisoformat(item["departure_time"])
        duration = int(item["duration_minutes"])
        repeat = int(item["repeat_days"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Проверьте дату, время, длительность и интервал") from exc
    if (first.year != 2026 or last.year != 2026 or first > last
            or not 1 <= duration <= 10080 or not 1 <= repeat <= 366):
        raise ValueError("Допустимы даты 2026 года, длительность до 7 суток и интервал 1–366 дней")
    reverse = item.get("reverse", False)
    if not isinstance(reverse, bool):
        raise ValueError("Некорректное значение обратного маршрута")
    service = f"Сценарный маршрут {number}"
    result = []
    day = first
    while day <= last:
        departure = datetime.combine(day, departure_time, air.TZ)
        arrival = departure + timedelta(minutes=duration)
        for start, finish in ([(origin, destination), (destination, origin)] if reverse
                              else [(origin, destination)]):
            result.append({
                "from": start, "to": finish, "depart": departure, "arrive": arrival,
                "mode": "scenario", "flight": service, "source_id": "SCENARIO",
                "source": "Пользовательский сценарий", "assumption": "Задано пользователем",
                "date": day.isoformat(),
            })
        day += timedelta(days=repeat)
    return result


def apply(base: list[dict], removed: list[str], additions: list[dict]) -> tuple[list[dict], dict]:
    if not isinstance(removed, list) or not isinstance(additions, list):
        raise ValueError("Некорректный формат сценария")
    if len(additions) > MAX_ADDITIONS:
        raise ValueError(f"Можно добавить не более {MAX_ADDITIONS} соединений за один расчёт")
    groups = {row["id"] for row in catalog(base)}
    if any(not isinstance(key, str) or key not in groups for key in removed):
        raise ValueError("В списке удаления есть неизвестное соединение")
    removed_set = set(removed)
    network = [event for event in base if group_id(event) not in removed_set]
    nodes = {place for event in base for place in (event["from"], event["to"])}
    added_count = 0
    for number, item in enumerate(additions, 1):
        new = _new_events(item, nodes, number)
        network.extend(new)
        added_count += len(new)
    return network, {
        "baseline_events": len(base), "removed_events": len(base) - len(network) + added_count,
        "added_events": added_count, "scenario_events": len(network),
    }
