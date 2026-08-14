"""No-API integrity tests for the Chapter 1 benchmark-20 evidence package."""

import json
import unittest
from collections import Counter
from pathlib import Path

from evaluation.ch1.d3_light_loader import (
    build_agent_case,
    build_evaluator_case,
)


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
        cls.d3 = json.loads(
            (ROOT / "d3_light_panel_v1.json").read_text(encoding="utf-8")
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

    def test_d3_panel_is_an_exact_five_task_subset(self):
        original_by_id = {item["id"]: item for item in self.original}
        selected = self.d3["tasks"]
        self.assertEqual(
            [item["source_task_id"] for item in selected],
            self.d3["source"]["selected_task_ids"],
        )
        self.assertEqual(len(selected), 5)
        for item in selected:
            source = original_by_id[item["source_task_id"]]
            self.assertEqual(item["request"], source["request"])
            self.assertEqual(item["category"], source["category"])
            self.assertEqual(item["context"], source["context"])

    def test_d3_panel_covers_five_distinct_runtime_roles(self):
        roles = [item["panel_role"] for item in self.d3["tasks"]]
        self.assertEqual(len(roles), len(set(roles)))
        self.assertEqual(
            set(roles),
            {
                "clean_supported_control",
                "missing_registered_tool",
                "data_precondition_stop",
                "multi_step_seeded_recovery",
                "manager_clarification_boundary",
            },
        )

    def test_d3_contracts_cover_all_conditions_without_scientific_gold(self):
        conditions = set(self.d3["conditions"])
        self.assertEqual(conditions, {"B1_static", "B2_adaptive", "B3_checkpoint"})
        forbidden_global = set(
            self.d3["global_scoring_contract"]["never_score_as_chapter1_gold"]
        )
        self.assertIn("pixel-level thematic accuracy", forbidden_global)
        for item in self.d3["tasks"]:
            terminals = item["chapter1_contract"]["allowed_terminal_by_condition"]
            self.assertEqual(set(terminals), conditions)
            self.assertTrue(all(terminals[condition] for condition in conditions))

    def test_only_one_d3_task_has_a_seeded_failure(self):
        seeded = [
            item for item in self.d3["tasks"]
            if item["fixture"]["kind"] == "seeded_transient_tool_failure"
        ]
        self.assertEqual([item["source_task_id"] for item in seeded], [11])
        self.assertFalse(seeded[0]["fixture"]["scientific_semantics_changed"])

    def test_d3_api_gate_authorizes_only_the_three_reviewed_smokes(self):
        gate = self.d3["run_gate"]
        self.assertTrue(gate["api_calls_authorized"])
        self.assertTrue(gate["pilot_authorized"])
        self.assertIn("three fixed S1-S3 live smoke slots", gate["authorization_scope"])
        self.assertIn("15-case pilot remains separately gated", gate["authorization_scope"])
        selection = self.d3["proposed_run_protocol"]["model_selection"]
        self.assertEqual(selection["provider"], "Paratera")
        self.assertEqual(selection["default_model"], "DeepSeek-V4-Flash")

    def test_d3_agent_view_does_not_leak_fixture_or_gold(self):
        agent_case = build_agent_case(self.d3, 11, "B3_checkpoint")
        serialized = json.dumps(agent_case)
        self.assertNotIn("chapter1_contract", serialized)
        self.assertNotIn("fixture_transient_write_failure", serialized)
        self.assertNotIn("allowed_terminal", serialized)
        self.assertEqual(agent_case["request"], self.original[10]["request"])

        evaluator_case = build_evaluator_case(self.d3, 11, "B3_checkpoint")
        self.assertEqual(
            evaluator_case["fixture"]["kind"],
            "seeded_transient_tool_failure",
        )
        self.assertIn("chapter1_contract", evaluator_case)


if __name__ == "__main__":
    unittest.main(verbosity=2)
