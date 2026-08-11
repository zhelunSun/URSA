"""No-API integrity tests for the Chapter 1 benchmark-20 evidence package."""

import json
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parent / "evaluation" / "ch1"


class Chapter1BenchmarkIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(
            (ROOT / "benchmark_20_original.json").read_text(encoding="utf-8")
        )
        cls.gold = json.loads(
            (ROOT / "benchmark_20_admission_gold_v0.json").read_text(encoding="utf-8")
        )

    def test_original_has_stable_ids_and_historical_split(self):
        self.assertEqual([item["id"] for item in self.original], list(range(1, 21)))
        self.assertEqual(
            Counter(item["category"] for item in self.original),
            {"single step": 10, "multi step": 10},
        )

    def test_admission_gold_is_one_to_one_with_original(self):
        self.assertEqual(
            [item["id"] for item in self.gold["tasks"]],
            [item["id"] for item in self.original],
        )

    def test_preferred_actions_are_declared_and_acceptable(self):
        vocabulary = set(self.gold["action_vocabulary"])
        for item in self.gold["tasks"]:
            self.assertIn(item["preferred_action"], vocabulary)
            self.assertIn(item["preferred_action"], item["acceptable_actions"])
            self.assertTrue(set(item["acceptable_actions"]).issubset(vocabulary))

    def test_draft_distribution_is_intentionally_small_and_mixed(self):
        self.assertEqual(
            Counter(item["preferred_action"] for item in self.gold["tasks"]),
            {"execute": 7, "ask_or_downgrade": 6, "controlled_stop": 7},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
