"""No-API tests for the shared D3-light runner and frozen protocol."""

import json
import tempfile
import unittest
from pathlib import Path

from evaluation.ch1.d3_light_loader import load_panel
from evaluation.ch1.d3_light_protocol import (
    API_GATE_ENV,
    api_calls_permitted,
    balanced_case_order,
    build_case_slots,
    write_dry_run_manifests,
)
from evaluation.ch1.d3_light_runner import D3LightRunner, DeterministicDryRunProvider
from evaluation.ch1.run_d3_light_dry_run import run_all_dry_cases


class D3LightDryRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = load_panel()

    def test_case_matrix_has_fifteen_unique_slots(self):
        slots = build_case_slots(self.panel)
        self.assertEqual(len(slots), 15)
        self.assertEqual(len({slot.case_id for slot in slots}), 15)
        order = balanced_case_order(slots)
        self.assertEqual(len(order), 15)
        self.assertEqual({slot.case_id for slot in order}, {slot.case_id for slot in slots})

    def test_api_gate_remains_closed_even_with_environment_flag(self):
        original = __import__("os").environ.get(API_GATE_ENV)
        __import__("os").environ[API_GATE_ENV] = "YES"
        try:
            self.assertFalse(api_calls_permitted(self.panel))
        finally:
            if original is None:
                __import__("os").environ.pop(API_GATE_ENV, None)
            else:
                __import__("os").environ[API_GATE_ENV] = original

    def test_dry_run_manifest_writer_emits_all_fifteen_no_api_slots(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = write_dry_run_manifests(directory, self.panel)
            manifest = json.loads(paths[0].read_text(encoding="utf-8"))
        self.assertEqual(len(paths), 15)
        self.assertEqual(manifest["mode"], "no_api_dry_run")
        self.assertFalse(manifest["api_calls_permitted"])
        self.assertIn("max_total_tokens_recorded", manifest["protocol"]["per_run_budget"])

    def test_static_seeded_failure_stops_while_adaptive_conditions_complete(self):
        runner = D3LightRunner(self.panel, DeterministicDryRunProvider())
        slots = {slot.condition_id: slot for slot in build_case_slots(self.panel) if slot.source_task_id == 11}
        static = runner.run(slots["B1_static"])
        adaptive = runner.run(slots["B2_adaptive"])
        checkpoint = runner.run(slots["B3_checkpoint"])
        self.assertEqual(static.terminal_status, "controlled_stop")
        self.assertEqual(adaptive.terminal_status, "completed")
        self.assertEqual(checkpoint.terminal_status, "completed")
        self.assertIsNone(static.process_graph)
        self.assertIsNotNone(adaptive.process_graph)
        self.assertTrue(checkpoint.evaluation["checkpoint_present"])
        self.assertTrue(checkpoint.evaluation["artifacts_complete"])
        self.assertEqual(checkpoint.evaluation["ndvi_action_count"], 1)
        self.assertTrue(checkpoint.evaluation["recovery_locality"])
        self.assertTrue(checkpoint.evaluation["task_specific_evidence"])

    def test_all_fifteen_deterministic_cases_pass_external_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = run_all_dry_cases(Path(directory))
            payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        self.assertEqual(len(paths), 15)
        self.assertTrue(all(payload["evaluation"]["passed"] for payload in payloads))
        self.assertTrue(all(payload["evaluation"]["task_specific_evidence"] for payload in payloads))
        self.assertEqual(
            sum(payload["terminal_status"] == "completed" for payload in payloads),
            5,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
