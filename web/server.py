"""Local, dependency-free HTTP server for transport-index scenarios."""
from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import air  # noqa: E402
import bus  # noqa: E402
import detail  # noqa: E402
import index  # noqa: E402
import scenario  # noqa: E402

WEB = Path(__file__).resolve().parent
BASE = bus.load_events()
CATALOG = scenario.catalog(BASE)
NODES = sorted({name for event in BASE for name in (event["from"], event["to"])})
SITE_TRANSFER_MINUTES = 60


@lru_cache(maxsize=1)
def site_baseline() -> dict:
    return index.compute(network=BASE, transfer_minutes=SITE_TRANSFER_MINUTES)


@lru_cache(maxsize=120)
def baseline_detail(place: str, hours: int) -> dict:
    return detail.compute(place, network=BASE, horizon_hours=hours,
                          transfer_minutes=SITE_TRANSFER_MINUTES)


def table(result: dict, horizon: str) -> list[dict]:
    return [{
        "place": place,
        "seasons": {season: {
            "random_start": result["scores"][season][place][horizon]["random_start"]["pct"],
            "ever_reachable": result["scores"][season][place][horizon]["ever_reachable"]["pct"],
        } for season in result["scores"]},
    } for place in index.PLACES]


@lru_cache(maxsize=32)
def baseline_table(hours: int) -> list[dict]:
    key = air.horizon_key(hours)
    result = (site_baseline() if key in bus.HORIZONS else
              index.compute(network=BASE, horizon_hours=hours,
                            transfer_minutes=SITE_TRANSFER_MINUTES))
    return table(result, key)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/bootstrap":
            baseline = site_baseline()
            self.send_json({
                "regions": [scenario.REGION], "region": scenario.REGION,
                "places": index.PLACES, "nodes": NODES,
                "horizons": bus.HORIZONS, "seasons": list(baseline["scores"]),
                "catalog": CATALOG, "baseline": {
                    key: table(baseline, key) for key in bus.HORIZONS
                },
                "baseline_events": len(BASE),
            })
            return
        assets = {"/": ("index.html", "text/html"),
                  "/place": ("place.html", "text/html"),
                  "/app.js": ("app.js", "text/javascript"),
                  "/place.js": ("place.js", "text/javascript"),
                  "/style.css": ("style.css", "text/css")}
        path = self.path.split("?", 1)[0]
        if path not in assets:
            self.send_error(404)
            return
        filename, mime = assets[path]
        body = (WEB / filename).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path not in {"/api/calculate", "/api/place", "/api/journey"}:
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 100_000:
                raise ValueError("Слишком большой или пустой запрос")
            request = json.loads(self.rfile.read(size))
            if not isinstance(request, dict) or request.get("region") != scenario.REGION:
                raise ValueError("Неизвестный регион")
            hours = (request["horizon_hours"] if "horizon_hours" in request
                     else bus.HORIZONS.get(request.get("horizon")))
            key = air.horizon_key(hours)
            network, counts = scenario.apply(BASE, request.get("removed", []),
                                             request.get("additions", []))
            if self.path == "/api/journey":
                self.send_json(detail.journey(request.get("place"),
                                              request.get("destination"),
                                              request.get("start"), network,
                                              transfer_minutes=SITE_TRANSFER_MINUTES))
                return
            if self.path == "/api/place":
                place = request.get("place")
                original = baseline_detail(place, hours)
                current = (original if not request.get("removed") and not request.get("additions")
                           else detail.compute(place, network=network, horizon_hours=hours,
                                               transfer_minutes=SITE_TRANSFER_MINUTES))
                self.send_json({"current": current, "baseline": original, "counts": counts})
                return
            original = baseline_table(hours)
            rows = (original if not request.get("removed") and not request.get("additions")
                    else table(index.compute(network, horizon_hours=hours,
                                             transfer_minutes=SITE_TRANSFER_MINUTES), key))
            self.send_json({"rows": rows, "baseline": original, "counts": counts})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)


def main() -> None:
    parser = argparse.ArgumentParser(description="Локальный сайт транспортного индекса")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Откройте http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
