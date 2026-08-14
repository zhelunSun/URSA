"""No-API tests for the shared D3-light runner and frozen protocol."""

import asyncio
from copy import deepcopy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.ch1.d3_light_loader import load_panel
from evaluation.ch1.d3_light_protocol import (
    API_GATE_ENV,
    api_calls_permitted,
    balanced_case_order,
    build_case_slots,
    write_dry_run_manifests,
)
from evaluation.ch1.d3_light_runner import (
    D3LightRunner, DeterministicDryRunProvider, run_authorized_d3_pilot,
    run_authorized_d3_smoke, run_unified_d3_case,
)
from evaluation.ch1.d3_light_tool_executor import D3LightToolExecutor
from evaluation.ch1 import run_d3_light_model_smoke
from evaluation.ch1.run_d3_light_dry_run import run_all_dry_cases, run_all_unified_dry_cases


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

    def test_reviewed_api_gate_still_requires_local_environment_flag(self):
        original = __import__("os").environ.get(API_GATE_ENV)
        try:
            __import__("os").environ.pop(API_GATE_ENV, None)
            self.assertFalse(api_calls_permitted(self.panel))
            __import__("os").environ[API_GATE_ENV] = "YES"
            self.assertTrue(api_calls_permitted(self.panel))
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

    def test_real_local_tools_close_checkpoint_recovery_without_an_api(self):
        runner = D3LightRunner(self.panel, DeterministicDryRunProvider(), D3LightToolExecutor())
        slot = next(
            slot for slot in build_case_slots(self.panel)
            if slot.source_task_id == 11 and slot.condition_id == "B3_checkpoint"
        )
        result = runner.run(slot)
        artifacts = [
            event["payload"] for event in result.trace.events
            if event["event_type"] == "artifact_recorded"
        ]
        self.assertTrue(result.evaluation["passed"])
        self.assertTrue(result.evaluation["recovery_locality"])
        self.assertTrue(any(
            item.get("artifact_type") == "index_raster" and item["uri"].endswith(".tif")
            for item in artifacts
        ))

    def test_unified_runtime_maps_d3_conditions_to_capability_policy_only(self):
        slots = {slot.condition_id: slot for slot in build_case_slots(self.panel) if slot.source_task_id == 11}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            static = asyncio.run(run_unified_d3_case(slots["B1_static"], destination=root / "b1"))
            adaptive = asyncio.run(run_unified_d3_case(slots["B2_adaptive"], destination=root / "b2"))
            checkpoint = asyncio.run(run_unified_d3_case(slots["B3_checkpoint"], destination=root / "b3"))
        self.assertEqual(static.status.value, "controlled_stop")
        self.assertEqual(adaptive.status.value, "completed")
        self.assertEqual(checkpoint.status.value, "completed")
        self.assertIsNone(adaptive.checkpoint_id)
        self.assertIsNotNone(checkpoint.checkpoint_id)

    def test_all_fifteen_unified_runtime_cases_pass_external_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = run_all_unified_dry_cases(Path(directory))
            payloads = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        self.assertEqual(len(paths), 15)
        self.assertTrue(all(payload["mode"] == "unified_runtime_scripted_offline" for payload in payloads))
        self.assertTrue(all(payload["evaluation"]["passed"] for payload in payloads))

    def test_live_smoke_refuses_to_run_without_both_gates(self):
        slot = next(slot for slot in build_case_slots(self.panel) if slot.source_task_id == 2)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "requires both"):
                asyncio.run(run_authorized_d3_smoke(Path(directory), object(), slots=[slot]))

    def test_live_pilot_requires_its_separate_panel_authorization(self):
        panel = deepcopy(self.panel)
        panel["run_gate"]["pilot_authorized"] = False
        old_gate = __import__("os").environ.get(API_GATE_ENV)
        __import__("os").environ[API_GATE_ENV] = "YES"
        try:
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(RuntimeError, "pilot_authorized"):
                    asyncio.run(run_authorized_d3_pilot(Path(directory) / "pilot", object(), panel=panel))
        finally:
            if old_gate is None:
                __import__("os").environ.pop(API_GATE_ENV, None)
            else:
                __import__("os").environ[API_GATE_ENV] = old_gate

    def test_opened_smoke_gate_uses_unified_live_runtime_without_network(self):
        from ExpertsRS import ExecutionMode, ExpertsRSSystem, ProviderConfig

        panel = deepcopy(self.panel)
        panel["run_gate"]["api_calls_authorized"] = True
        slot = next(
            item for item in build_case_slots(panel)
            if item.source_task_id == 13 and item.condition_id == "B2_adaptive"
        )

        class ClarifyingProvider:
            async def decide(self, role, state):
                self.assertEqual(role, "Manager")
                return {
                    "kind": "clarify", "question": "Please define vegetation health.",
                    "_provider_usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
                }

            def assertEqual(self, left, right):
                if left != right:
                    raise AssertionError(f"expected {right}, got {left}")

        old_gate = __import__("os").environ.get(API_GATE_ENV)
        __import__("os").environ[API_GATE_ENV] = "YES"
        try:
            with tempfile.TemporaryDirectory() as directory:
                records = asyncio.run(run_authorized_d3_smoke(
                    Path(directory), ProviderConfig(model="fake-live-model"), slots=[slot], panel=panel,
                    system_factory=lambda _: ExpertsRSSystem(provider=ClarifyingProvider()),
                ))
        finally:
            if old_gate is None:
                __import__("os").environ.pop(API_GATE_ENV, None)
            else:
                __import__("os").environ[API_GATE_ENV] = old_gate
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["mode"], "unified_runtime_autogen_live")
        self.assertEqual(records[0]["result"]["execution_mode"], ExecutionMode.AUTOGEN_LIVE.value)
        self.assertTrue(records[0]["evaluation"]["passed"])

    def test_smoke_entry_loads_only_the_untracked_expertsrs_environment_file(self):
        with patch("evaluation.ch1.run_d3_light_model_smoke.load_dotenv") as load_dotenv:
            run_d3_light_model_smoke._load_untracked_environment()
        configured_path = load_dotenv.call_args.args[0]
        self.assertEqual(configured_path.name, ".env")
        self.assertEqual(configured_path.parent.name, "ExpertsRS")
        self.assertFalse(load_dotenv.call_args.kwargs["override"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
