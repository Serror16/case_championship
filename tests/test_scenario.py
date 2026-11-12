"""Scenario edits must change a temporary graph without touching source data."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import bus  # noqa: E402
import scenario  # noqa: E402


class ScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = bus.load_events()

    def test_regular_bidirectional_route_expands_into_dated_edges(self) -> None:
        addition = {
            "origin": "Анадырь", "destination": "Билибино",
            "first_date": "2026-07-01", "last_date": "2026-07-07",
            "departure_time": "09:00", "duration_minutes": 120,
            "repeat_days": 2, "reverse": True,
        }
        network, counts = scenario.apply(self.base, [], [addition])
        self.assertEqual(counts["added_events"], 8)
        self.assertEqual(counts["scenario_events"], len(self.base) + 8)
        self.assertEqual(len(self.base), 29142)
        self.assertEqual({event["date"] for event in network if event["mode"] == "scenario"},
                         {"2026-07-01", "2026-07-03", "2026-07-05", "2026-07-07"})

    def test_exclusion_removes_only_selected_direction_and_service(self) -> None:
        group = next(row for row in scenario.catalog(self.base)
                     if row["origin"] == "Билибино" and row["destination"] == "Кепервеем"
                     and row["service"] == "автобус № 100")
        network, counts = scenario.apply(self.base, [group["id"]], [])
        self.assertEqual(counts["removed_events"], group["count"])
        self.assertFalse(any(scenario.group_id(event) == group["id"] for event in network))
        self.assertTrue(any(event["from"] == "Кепервеем" and event["to"] == "Билибино"
                            and event["flight"] == "автобус № 100" for event in network))

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            scenario.apply(self.base, ["unknown"], [])
        with self.assertRaises(ValueError):
            scenario.apply(self.base, [], [{"origin": "Анадырь", "destination": "Анадырь"}])


if __name__ == "__main__":
    unittest.main()
