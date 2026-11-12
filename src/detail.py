"""Destination-level diagnostics for one rated settlement."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import air
import bus
import engine
import roster


def compute(origin: str, horizon_key: str | None = None, network: list[dict] | None = None,
            horizon_hours: int | None = None) -> dict:
    if origin not in roster.RATED:
        raise ValueError("Выберите населённый пункт из расчёта индекса")
    if horizon_hours is not None:
        if horizon_key is not None:
            raise ValueError("Укажите H в часах или известное название порога")
        horizon_key = air.horizon_key(horizon_hours)
    elif horizon_key in bus.HORIZONS:
        horizon_hours = bus.HORIZONS[horizon_key]
    else:
        raise ValueError("Неизвестный порог H")
    horizon_minutes = horizon_hours * 60
    _, nodes, indexes, events, departures, _ = bus.prepare(network)
    destinations = sorted(roster.RATED - {origin})
    starts = defaultdict(int)
    successes = defaultdict(int)
    fastest = {}
    fastest_start = {}

    for day_number in range(365):
        season = air.season_for(air.FIRST + timedelta(days=day_number))
        for hour in engine.START_HOURS:
            start = day_number * 1440 + hour * 60
            if start + horizon_minutes >= engine.END_MINUTES:
                continue
            starts[season] += 1
            arrivals = engine.earliest_arrivals(indexes[origin], start, len(nodes),
                                                events, departures, max_hours=168)
            for destination in destinations:
                duration = arrivals[indexes[destination]] - start
                if duration <= 168 * 60:
                    key = season, destination
                    if key not in fastest or duration < fastest[key]:
                        fastest[key] = duration
                        fastest_start[key] = start
                if duration <= horizon_minutes:
                    successes[season, destination] += 1

    seasons = {}
    for season in air.SEASON_ORDER:
        rows = []
        for destination in destinations:
            yes = successes[season, destination]
            minimum = fastest.get((season, destination))
            rows.append({
                "destination": destination,
                "successful_starts": yes,
                "checked_starts": starts[season],
                "random_start_pct": round(100 * yes / starts[season], 1),
                "ever_reachable": yes > 0,
                "fastest_known_hours": round(minimum / 60, 1) if minimum is not None else None,
                "fastest_start": ((engine.EPOCH + timedelta(minutes=fastest_start[season, destination]))
                                  .isoformat(timespec="minutes") if minimum is not None else None),
                "diagnosis": ("reachable" if yes else
                              "over_h" if minimum is not None else "no_path_7d"),
            })
        seasons[season] = {
            "random_start_pct": round(100 * sum(row["successful_starts"] for row in rows)
                                      / (starts[season] * len(destinations)), 1),
            "ever_reachable_pct": round(100 * sum(row["ever_reachable"] for row in rows)
                                        / len(destinations), 1),
            "checked_starts": starts[season],
            "destinations": rows,
        }
    return {"origin": origin, "horizon": horizon_key, "seasons": seasons}


def journey(origin: str, destination: str, start_iso: str,
            network: list[dict] | None = None) -> dict:
    if origin not in roster.RATED or destination not in roster.RATED or origin == destination:
        raise ValueError("Выберите два разных пункта из расчёта индекса")
    try:
        moment = datetime.fromisoformat(start_iso)
    except (TypeError, ValueError) as exc:
        raise ValueError("Некорректное время начала поездки") from exc
    if (moment.year != 2026 or moment.utcoffset() != air.TZ.utcoffset(None)
            or moment.hour not in engine.START_HOURS or moment.minute != 0):
        raise ValueError("Время начала должно быть одним из проверяемых стартов 2026 года")
    network, nodes, indexes, events, departures, _ = bus.prepare(network)
    start = int((moment - engine.EPOCH).total_seconds() // 60)
    arrival, path = engine.earliest_path(indexes[origin], indexes[destination],
                                         start, len(nodes), events, departures)
    if arrival == engine.INF:
        return {"found": False, "legs": []}
    return {
        "found": True,
        "total_hours": round((arrival - start) / 60, 1),
        "legs": [{
            "origin": network[i]["from"], "destination": network[i]["to"],
            "departure": network[i]["depart"].isoformat(timespec="minutes"),
            "arrival": network[i]["arrive"].isoformat(timespec="minutes"),
            "service": network[i]["flight"], "mode": network[i]["mode"],
            "source": network[i]["source"], "assumption": network[i].get("assumption", ""),
        } for i in path],
    }
