"""Behavioral and regression checks for the published pilot."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import engine  # noqa: E402
import index  # noqa: E402
import roster  # noqa: E402

EXPECTED_SCORES_SHA256 = "bc0812972857918ec623d718d0b81509d7c5ad8ddfe9c17c2f4a095fa70ec595"


class TransportIndexTests(unittest.TestCase):
    def test_transfer_requires_90_minutes(self) -> None:
        # A=0, B=1, C=2; all times are minutes after the synthetic start.
        events = [(0, 1, 10, 20), (1, 2, 80, 90)]
        best = engine.earliest_arrivals(0, 0, 3, events, [10, 80], max_hours=3)
        self.assertEqual(best[1], 20)
        self.assertEqual(best[2], engine.INF)

        events.append((1, 2, 120, 130))
        best = engine.earliest_arrivals(0, 0, 3, events, [10, 80, 120], max_hours=3)
        self.assertEqual(best[2], 130)

    def test_direct_onboard_leg_needs_no_transfer(self) -> None:
        # A through C is represented as one direct leg of the same service.
        events = [(0, 1, 10, 20), (0, 2, 10, 90), (1, 2, 80, 90)]
        best = engine.earliest_arrivals(0, 0, 3, events, [10, 10, 80], max_hours=3)
        self.assertEqual(best[2], 90)

    def test_published_results_match_reviewed_calculation(self) -> None:
        path = ROOT / "results/CORRECTED_ROSTER_37.json"
        self.assertTrue(path.exists(), "Run python src/index.py first")
        result = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(index.compute()["scores"], result["scores"])
        self.assertEqual(len(result["rated_settlements"]), 37)
        self.assertEqual(len(result["unrated_settlements"]), 9)
        self.assertEqual(set(result["rated_settlements"]) | set(result["unrated_settlements"]), roster.SETTLEMENTS)
        self.assertEqual(result["destination_denominator_per_origin"], 36)
        payload = json.dumps(result["scores"], sort_keys=True, ensure_ascii=False).encode()
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SCORES_SHA256)
        for season in result["scores"].values():
            for origin in season.values():
                for score in origin.values():
                    self.assertLessEqual(score["random_start"]["pct"], score["ever_reachable"]["pct"])


if __name__ == "__main__":
    unittest.main()
