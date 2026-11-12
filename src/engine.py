"""Earliest-arrival scan for a dated, directed transport network."""
from __future__ import annotations
from bisect import bisect_left, bisect_right
from datetime import datetime
import air

EPOCH = datetime(2026, 1, 1, tzinfo=air.TZ)
END = datetime(2027, 1, 1, tzinfo=air.TZ)
END_MINUTES = int((END - EPOCH).total_seconds() // 60)
MAX_HOURS = 168
TRANSFER_MINUTES = air.TRANSFER_MINUTES
START_HOURS = tuple(range(0, 24, 2))
INF = 10**12

def earliest_arrivals(origin_index: int, start: int, node_count: int,
                      events: list[tuple[int, int, int, int]],
                      departures: list[int], max_hours: int | None = None) -> list[int]:
    """Расписание уже отсортировано по отправлению; возврат только времени, без путей."""
    latest = start + (MAX_HOURS if max_hours is None else max_hours)*60
    best = [INF]*node_count
    best[origin_index] = start
    first = bisect_left(departures, start)
    last = bisect_right(departures, latest)
    for i in range(first, last):
        src, dst, depart, arrive = events[i]
        if arrive > latest or best[src] == INF:
            continue
        ready = best[src] + (0 if src == origin_index else TRANSFER_MINUTES)
        if ready <= depart and arrive < best[dst]:
            best[dst] = arrive
    return best


def earliest_path(origin_index: int, destination_index: int, start: int,
                  node_count: int, events: list[tuple[int, int, int, int]],
                  departures: list[int], max_hours: int = 168) -> tuple[int, tuple[int, ...]]:
    """Return arrival time and event indexes for one concrete earliest journey."""
    latest = start + max_hours * 60
    best = [INF] * node_count
    paths: list[tuple[int, ...]] = [()] * node_count
    best[origin_index] = start
    first = bisect_left(departures, start)
    last = bisect_right(departures, latest)
    for i in range(first, last):
        src, dst, depart, arrive = events[i]
        if arrive > latest or best[src] == INF:
            continue
        ready = best[src] + (0 if src == origin_index else TRANSFER_MINUTES)
        if ready <= depart and arrive < best[dst]:
            best[dst] = arrive
            paths[dst] = paths[src] + (i,)
    return best[destination_index], paths[destination_index]
