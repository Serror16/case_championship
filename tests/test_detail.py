"""Destination diagnostics should explain the published settlement score."""
from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import air  # noqa: E402
import detail  # noqa: E402
import index  # noqa: E402
import scenario  # noqa: E402
import bus  # noqa: E402


class DetailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.published = json.loads((ROOT / "results/CORRECTED_ROSTER_37.json").read_text(encoding="utf-8"))
        cls.baseline = detail.compute("Билибино", "72ч")

    def test_destination_rows_reproduce_published_settlement_scores(self) -> None:
        for season, data in self.baseline["seasons"].items():
            expected = self.published["scores"][season]["Билибино"]["72ч"]
            self.assertEqual(data["random_start_pct"], expected["random_start"]["pct"])
            self.assertEqual(data["ever_reachable_pct"], expected["ever_reachable"]["pct"])
            self.assertEqual(len(data["destinations"]), 36)

    def test_example_journey_is_chronological_and_has_cited_legs(self) -> None:
        row = next(item for item in self.baseline["seasons"]["Зима"]["destinations"]
                   if item["fastest_start"] is not None and item["destination"] == "Кепервеем")
        trip = detail.journey("Билибино", "Кепервеем", row["fastest_start"])
        self.assertTrue(trip["found"])
        self.assertEqual(trip["total_hours"], row["fastest_known_hours"])
        self.assertEqual(trip["legs"][0]["origin"], "Билибино")
        self.assertEqual(trip["legs"][-1]["destination"], "Кепервеем")
        self.assertTrue(all(leg["source"] for leg in trip["legs"]))
        self.assertTrue(all(datetime.fromisoformat(a["arrival"]) + timedelta(minutes=90)
                            <= datetime.fromisoformat(b["departure"])
                            for a, b in zip(trip["legs"], trip["legs"][1:])))

    def test_added_connection_appears_in_destination_diagnostics(self) -> None:
        addition = {"origin": "Билибино", "destination": "Анюйск",
                    "first_date": "2026-01-01", "last_date": "2026-02-28",
                    "departure_time": "09:00", "duration_minutes": 120,
                    "repeat_days": 7, "reverse": False}
        network, _ = scenario.apply(bus.load_events(), [], [addition])
        changed = detail.compute("Билибино", "72ч", network)
        before = next(row for row in self.baseline["seasons"]["Зима"]["destinations"]
                      if row["destination"] == "Анюйск")
        after = next(row for row in changed["seasons"]["Зима"]["destinations"]
                     if row["destination"] == "Анюйск")
        self.assertFalse(before["ever_reachable"])
        self.assertTrue(after["ever_reachable"])
        self.assertGreater(after["random_start_pct"], before["random_start_pct"])

    def test_custom_horizon_matches_full_index(self) -> None:
        detailed = detail.compute("Билибино", horizon_hours=96)
        full = index.compute(horizon_hours=96)
        key = air.horizon_key(96)
        self.assertEqual(key, "96ч")
        for season, row in detailed["seasons"].items():
            score = full["scores"][season]["Билибино"][key]
            self.assertEqual(row["random_start_pct"], score["random_start"]["pct"])
            self.assertEqual(row["ever_reachable_pct"], score["ever_reachable"]["pct"])

    def test_horizon_limits(self) -> None:
        for value in (0, 169, 1.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                air.horizon_key(value)


if __name__ == "__main__":
    unittest.main()
