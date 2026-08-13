"""system-offline: end-to-end contracts for the authoritative runtime."""

from __future__ import annotations

import asyncio
import time
import json
import tempfile
import unittest
from pathlib import Path
import sys

try:
    from ExpertsRS import ExpertsRSSystem, LocalToolExecutor, RunRequest, RunStatus
    from ExpertsRS.models import RunBudgets, RuntimeCapabilities
except ModuleNotFoundError:  # Support ``python -m unittest discover`` in ExpertsRS/.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ExpertsRS import ExpertsRSSystem, LocalToolExecutor, RunRequest, RunStatus
    from ExpertsRS.models import RunBudgets, RuntimeCapabilities


SCENE = Path(__file__).parent / "data" / "Sentinel2_Dongcheng_20230718.tif"


class UnifiedSystemTests(unittest.TestCase):
    """system-offline tests use scripted decisions and the real local tools."""

    def _run(self, request: str, directory: Path, *, system: ExpertsRSSystem | None = None, capabilities: RuntimeCapabilities | None = None):
        return asyncio.run((system or ExpertsRSSystem()).run(RunRequest(
            request=request,
            data_paths=[SCENE],
            output_dir=directory,
            run_id="case",
            capabilities=capabilities or RuntimeCapabilities(),
        )))

    def test_ndvi_returns_report_artifacts_and_a_redacted_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Map NDVI for Dongcheng in summer 2023", Path(directory))
            trace = result.trace_path.read_text(encoding="utf-8")
            result_payload = json.loads((Path(directory) / "case" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertIn("NDVI", result.report)
        self.assertIn("已验证制品", result.report)
        self.assertEqual({item.artifact_type for item in result.artifacts}, {"metadata", "index_raster", "map"})
        self.assertNotIn(str(SCENE), trace)
        self.assertEqual(result_payload["status"], "completed")

    def test_report_failure_preserves_artifacts_and_records_terminal_state(self):
        class ReportFailureProvider:
            async def decide(self, role, state):
                if role == "Manager" and state["phase"] == "report":
                    return {"kind": "report", "summary": "Incorrect report.", "artifact_refs": []}
                from ExpertsRS.decisions import ScriptedDecisionProvider
                return await ScriptedDecisionProvider().decide(role, state)

        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Map NDVI", Path(directory), system=ExpertsRSSystem(provider=ReportFailureProvider()))
            trace = result.trace_path.read_text(encoding="utf-8")
        self.assertEqual(result.status, RunStatus.REPORT_FAILED)
        self.assertEqual({item.artifact_type for item in result.artifacts}, {"metadata", "index_raster", "map"})
        self.assertIn("report_failed", trace)

    def test_report_does_not_expose_artifact_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Map NDVI", Path(directory))
        self.assertNotIn(str(SCENE), result.report)
        self.assertNotIn(".tif", result.report)

    def test_greenspace_recovery_completes_with_current_matplotlib(self):
        system = ExpertsRSSystem(executor=LocalToolExecutor(inject_failures={"apply_threshold": 1}))
        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Calculate green cover rate for Dongcheng", Path(directory), system=system)
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertIn("map", {artifact.artifact_type for artifact in result.artifacts})

    def test_recovery_reuses_ndvi_checkpoint_without_recomputing(self):
        system = ExpertsRSSystem(executor=LocalToolExecutor(inject_failures={"apply_threshold": 1}))
        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Calculate green cover rate for Dongcheng", Path(directory), system=system)
            events = [json.loads(line) for line in result.trace_path.read_text(encoding="utf-8").splitlines()]
        actions = [event["payload"].get("tool_name") for event in events if event["event_type"] == "action_started"]
        plans = [event for event in events if event["event_type"] == "plan_version_recorded"]
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(actions.count("calculate_ndvi"), 1)
        self.assertEqual(actions.count("apply_threshold"), 2)
        self.assertEqual(len(plans), 2)
        self.assertIsNotNone(result.checkpoint_id)
        self.assertIn("mask_raster", {item.artifact_type for item in result.artifacts})

    def test_static_condition_stops_after_tool_failure(self):
        system = ExpertsRSSystem(executor=LocalToolExecutor(inject_failures={"apply_threshold": 1}))
        with tempfile.TemporaryDirectory() as directory:
            result = self._run(
                "Calculate green cover rate for Dongcheng", Path(directory), system=system,
                capabilities=RuntimeCapabilities(allow_plan_revision=False, allow_checkpoint_recovery=False),
            )
        self.assertEqual(result.status, RunStatus.CONTROLLED_STOP)

    def test_unsupported_and_scientifically_invalid_requests_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            ndsi = self._run("Map NDSI for Dongcheng", Path(directory) / "ndsi")
            lst = self._run("Derive LST for Dongcheng", Path(directory) / "lst")
        self.assertEqual(ndsi.status, RunStatus.CONTROLLED_STOP)
        self.assertEqual(lst.status, RunStatus.CONTROLLED_STOP)

    def test_clarification_can_resume_the_same_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = ExpertsRSSystem()
            first = self._run("What is the vegetation health condition?", root, system=system)
            resumed = asyncio.run(system.resume(first.run_id, "Please produce an NDVI map.", root))
        self.assertEqual(first.status, RunStatus.NEEDS_CLARIFICATION)
        self.assertTrue(first.questions)
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(resumed.run_id, first.run_id)

    def test_data_outside_the_allowed_root_is_denied_without_tool_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = asyncio.run(ExpertsRSSystem(allowed_data_roots=[root / "allowed"]).run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="denied",
            )))
        self.assertEqual(result.status, RunStatus.CONTROLLED_STOP)
        self.assertEqual(result.validation.tool_calls, 0)

    def test_duplicate_run_id_never_overwrites_prior_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._run("Map NDVI", root)
            with self.assertRaises(FileExistsError):
                self._run("Map NDVI", root)

    def test_model_visible_catalog_is_the_runtime_bound_safe_subset(self):
        class InspectingProvider:
            async def decide(self, role, state):
                self.catalog = state["available_tools"]
                return {"kind": "clarify", "question": "Need a precise output."}

        provider = InspectingProvider()
        with tempfile.TemporaryDirectory() as directory:
            self._run("What is the vegetation health condition?", Path(directory), system=ExpertsRSSystem(provider=provider))
        self.assertEqual({item["tool_name"] for item in provider.catalog}, set(ExpertsRSSystem.TOOL_BINDINGS))
        self.assertNotIn("calculate_evi", {item["tool_name"] for item in provider.catalog})

    def test_invalid_model_json_is_traced_without_executing_a_tool(self):
        class InvalidProvider:
            async def decide(self, role, state):
                return ["not", "a", "decision"]

        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Map NDVI", Path(directory), system=ExpertsRSSystem(provider=InvalidProvider()))
            trace = result.trace_path.read_text(encoding="utf-8")
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(result.validation.tool_calls, 0)
        self.assertIn("invalid_model_decision", trace)

    def test_wall_time_budget_stops_before_provider_execution(self):
        class UnexpectedProvider:
            async def decide(self, role, state):
                raise AssertionError("provider must not run after wall-time expiry")

        with tempfile.TemporaryDirectory() as directory:
            system = ExpertsRSSystem(provider=UnexpectedProvider())
            state = system._initial_state(
                RunRequest(request="Map NDVI", data_paths=[SCENE], output_dir=Path(directory), run_id="wall", budgets=RunBudgets(max_wall_time_seconds=1)),
                "wall", Path(directory) / "wall",
            )
            state["started_at_unix"] = time.time() - 2
            (Path(directory) / "wall").mkdir()
            result = asyncio.run(system._drive(state))
        self.assertEqual(result.status, RunStatus.CONTROLLED_STOP)
        self.assertEqual(result.validation.tool_calls, 0)

    def test_unknown_tool_and_unsafe_action_contract_stop_without_execution(self):
        class ActionProvider:
            def __init__(self, action):
                self.action = action

            async def decide(self, role, state):
                if role == "Manager":
                    return {"kind": "handoff", "target": "Scientist"}
                if role == "Scientist":
                    return {"kind": "plan", "operation": "ndvi", "next_action": "read_raster_metadata"}
                return self.action

        actions = (
            {"kind": "action", "tool_name": "calculate_evi"},
            {"kind": "action", "tool_name": "read_raster_metadata", "parameters": {"file_path": "C:/secret.tif"}},
            {"kind": "action", "tool_name": "plot_index_map"},
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, action in enumerate(actions):
                result = self._run("Map NDVI", Path(directory) / str(index), system=ExpertsRSSystem(provider=ActionProvider(action)))
                self.assertIn(result.status, {RunStatus.FAILED, RunStatus.CONTROLLED_STOP})
                self.assertEqual(result.validation.tool_calls, 0)

    def test_action_requires_a_registered_artifact_id_not_a_type_or_path(self):
        class WrongReferenceProvider:
            async def decide(self, role, state):
                if role == "Manager":
                    return {"kind": "handoff", "target": "Scientist"}
                if role == "Scientist":
                    return {"kind": "plan", "operation": "ndvi", "next_action": "read_raster_metadata"}
                if not state["observations"]:
                    return {"kind": "action", "tool_name": "read_raster_metadata"}
                return {"kind": "action", "tool_name": "plot_index_map", "artifact_refs": ["index_raster"]}

        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Map NDVI", Path(directory), system=ExpertsRSSystem(provider=WrongReferenceProvider()))
        self.assertEqual(result.status, RunStatus.CONTROLLED_STOP)
        self.assertEqual(result.validation.tool_calls, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
