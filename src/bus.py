"""Load the reviewed Chukotka timetable graph from tabular data."""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from pathlib import Path

import air
import engine
import roster

DATA = Path(__file__).resolve().parents[1] / "date"
EVENT_FILE = DATA / "transport_events_2026.csv"
SOURCE_FILE = DATA / "sources.csv"
PLACES = sorted(roster.RATED - {"Анадырь"})
ORIGINS = sorted(roster.RATED)
HORIZONS = air.HORIZONS
REQUIRED = {"event_id", "origin", "destination", "departure", "arrival", "mode",
            "service", "source_id", "evidence_status", "assumption", "boarding_stop"}


def load_sources() -> dict[str, str]:
    with SOURCE_FILE.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    sources = {row["source_id"]: row["url"] for row in rows}
    if len(sources) != len(rows) or not sources:
        raise ValueError("Source IDs must be unique and nonempty")
    return sources


def load_events() -> list[dict]:
    sources = load_sources()
    events = []
    ids = set()
    with EVENT_FILE.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(reader.fieldnames) != REQUIRED:
            raise ValueError(f"Unexpected event columns in {EVENT_FILE}")
        for line, row in enumerate(reader, 2):
            event_id = int(row["event_id"])
            departure = datetime.fromisoformat(row["departure"])
            arrival = datetime.fromisoformat(row["arrival"])
            if (event_id in ids or not row["origin"] or not row["destination"]
                    or row["origin"] == row["destination"] or departure >= arrival
                    or departure.utcoffset() != air.TZ.utcoffset(None)
                    or arrival.utcoffset() != air.TZ.utcoffset(None)
                    or row["source_id"] not in sources):
                raise ValueError(f"Invalid event on line {line} of {EVENT_FILE}")
            ids.add(event_id)
            events.append({
                "event_id": event_id,
                "from": row["origin"], "to": row["destination"],
                "depart": departure, "arrive": arrival,
                "mode": row["mode"], "flight": row["service"],
                "source_id": row["source_id"], "source": sources[row["source_id"]],
                "evidence_status": row["evidence_status"],
                "assumption": row["assumption"],
                "boarding_stop": row["boarding_stop"],
                "date": departure.date().isoformat(),
            })
    events.sort(key=lambda item: item["depart"])
    return events


def prepare(network: list[dict] | None = None) -> tuple[list, list, dict, list, list, dict]:
    network = sorted(load_events() if network is None else network,
                     key=lambda event: event["depart"])
    nodes = sorted(roster.RATED | {place for event in network
                                   for place in (event["from"], event["to"])})
    indexes = {node: i for i, node in enumerate(nodes)}
    compact = [(indexes[event["from"]], indexes[event["to"]],
                int((event["depart"] - engine.EPOCH).total_seconds() // 60),
                int((event["arrive"] - engine.EPOCH).total_seconds() // 60))
               for event in network]
    services = Counter(event["flight"] for event in network)
    counts = {
        "coal_bus_events": services["автобус № 2"],
        "coal_local_bus_events": services["автобус № 1"],
        "bilibino_bus_events": services["автобус № 100"],
        "airport_pier_taxi_events_removed": 2 * 15 * 110,
    }
    return network, nodes, indexes, compact, [event[2] for event in compact], counts
