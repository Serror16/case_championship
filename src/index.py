"""Calculate the 37-settlement Chukotka pilot for all seasons and horizons.

Run from the repository root: python src/index.py
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import air
import bus
import engine
import roster

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"
PLACES = sorted(set(bus.PLACES) | {"Анадырь"})
if len(PLACES) != 37 or not set(PLACES) <= roster.SETTLEMENTS:
    raise ValueError("The reviewed 37-settlement roster has changed")
MISSING = sorted(set(roster.SETTLEMENTS) - set(PLACES))
MAX_HOURS = max(bus.HORIZONS.values())


def compute(network: list[dict] | None = None, horizon_key: str | None = None,
            horizon_hours: int | None = None,
            transfer_minutes: int = engine.TRANSFER_MINUTES) -> dict:
    if horizon_key is not None and horizon_key not in bus.HORIZONS:
        raise ValueError(f"Unknown horizon: {horizon_key}")
    if horizon_hours is not None:
        if horizon_key is not None:
            raise ValueError("Укажите H в часах или известное название порога")
        key = air.horizon_key(horizon_hours)
        horizons = {key: horizon_hours}
    else:
        horizons = ({horizon_key: bus.HORIZONS[horizon_key]} if horizon_key
                    else bus.HORIZONS)
    _, nodes, indexes, events, departures, counts = bus.prepare(network)
    if not all(place in indexes for place in PLACES):
        raise ValueError("A rated settlement is absent from the transport graph")
    starts = defaultdict(int)
    yes = defaultdict(int)
    reached = defaultdict(set)
    for day_number in range(365):
        season = air.season_for(air.FIRST + timedelta(days=day_number))
        for hour in engine.START_HOURS:
            start = day_number * 1440 + hour * 60
            valid = [(key, horizon * 60) for key, horizon in horizons.items()
                     if start + horizon * 60 < engine.END_MINUTES]
            if not valid:
                continue
            for key, _ in valid:
                starts[season, key] += 1
            for origin in PLACES:
                best = engine.earliest_arrivals(indexes[origin], start, len(nodes),
                                                events, departures,
                                                max_hours=max(horizons.values()),
                                                transfer_minutes=transfer_minutes)
                for destination in PLACES:
                    if destination == origin:
                        continue
                    duration = best[indexes[destination]] - start
                    for key, limit in valid:
                        if duration <= limit:
                            token = season, origin, key
                            yes[token] += 1
                            reached[token].add(destination)
    scores = {}
    for season in air.SEASON_ORDER:
        scores[season] = {}
        for origin in PLACES:
            scores[season][origin] = {}
            for key in horizons:
                token = season, origin, key
                random_total = starts[season, key] * (len(PLACES) - 1)
                ever_total = len(PLACES) - 1
                scores[season][origin][key] = {
                    "random_start": {
                        "yes": yes[token], "total": random_total,
                        "pct": round(100 * yes[token] / random_total, 1),
                    },
                    "ever_reachable": {
                        "yes": len(reached[token]), "total": ever_total,
                        "pct": round(100 * len(reached[token]) / ever_total, 1),
                        "destinations": sorted(reached[token]),
                    },
                }
    return {
        "period": "2026",
        "status": "сценарный расчёт на неполной транспортной сети",
        "reference_roster_source": roster.SOURCE,
        "reference_settlements": len(roster.SETTLEMENTS),
        "rated_settlements": PLACES,
        "unrated_settlements": MISSING,
        "destination_denominator_per_origin": len(PLACES) - 1,
        "horizons_hours": horizons,
        "start_hours": list(engine.START_HOURS),
        "seasons": {name: sorted(months) for name, months in air.SEASONS.items()},
        "sources_manifest": "SOURCES.md",
        "assumptions": [
            "Транспортная сеть строится из выбранных рейсов и модельных подъездов; Анадырь включён в общий перечень адресатов",
            "Сценарий использует часы части автобусов из 2024/2025 годов и другие модельные трансферы",
            "Девять пунктов без достаточных маршрутных данных не входят в знаменатель; их балл не равен нулю",
            "Для аэропортов, совпадающих по имени с населёнными пунктами, местный подъезд может быть недостаточно учтён",
        ],
        "event_counts": {"total": len(events), **counts},
        "scores": scores,
    }


def write(result: dict) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / "CORRECTED_ROSTER_37.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Чукотка: единый рейтинг 37 населённых пунктов", "",
        f"[Региональный план 2025]({roster.SOURCE}) содержит 46 пунктов. В текущей транспортной сети есть 37, включая Анадырь; каждому соответствуют 36 адресатов. Остальные 9 пока не оценены из-за недостатка маршрутных данных.",
        "Сеть строится из выбранных рейсов и модельных подъездов. Движение части маршрутов подтверждено, но часы некоторых рейсов перенесены из 2024/2025 годов. Оценки ниже сценарные.",
        "В ячейке: **успешные варианты поездки / пункты, достижимые хотя бы раз**, %. Для первого числа проверяются поездки в каждый другой пункт при старте каждые 2 часа; второе число показывает долю пунктов, доступных хотя бы при одном старте за сезон. Ожидание и пересадки входят в порог H.", "",
    ]
    for key in bus.HORIZONS:
        lines += [f"## Порог {key}", "",
                  "| Пункт | Зима | Весеннее межсезонье | Лето | Осеннее межсезонье |",
                  "|---|---:|---:|---:|---:|"]
        for origin in PLACES:
            cells = []
            for season in air.SEASON_ORDER:
                item = result["scores"][season][origin][key]
                cells.append(f"{item['random_start']['pct']:.1f} / {item['ever_reachable']['pct']:.1f}")
            lines.append("| " + " | ".join([origin, *cells]) + " |")
        lines.append("")
    lines += ["## Ещё не оценены", "", ", ".join(MISSING) + ".", "",
              "Их нельзя записывать как недоступные: отсутствие данных в модели не является отсутствием сообщения. Опорный перечень приведён в `date/settlements.csv`.", "",
              "Машинные результаты с числителями, знаменателями и адресатами: `CORRECTED_ROSTER_37.json`."]
    (OUT / "CORRECTED_ROSTER_37.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    output = compute()
    write(output)
    print(json.dumps({"rated": len(PLACES), "unrated": len(MISSING), "events": output["event_counts"]["total"]}, ensure_ascii=False))
