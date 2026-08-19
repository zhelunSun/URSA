"""v0.5.2 closeout tests for structured planning, report honesty and privacy."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from ExpertsRS import ExpertsRSSystem, LocalToolExecutor, RunRequest, RunStatus
from ExpertsRS.decisions import ScriptedDecisionProvider
from ExpertsRS.evaluation.ch1.d3_light_loader import load_panel
from ExpertsRS.evaluation.ch1.d3_light_protocol import build_case_slots
from ExpertsRS.evaluation.ch1.d3_light_runner import run_unified_d3_case
from ExpertsRS.evaluation.ch1.v2_evaluator import evaluate_v2_unified_run


SCENE = Path(__file__).parent / "data" / "Sentinel2_Dongcheng_20230718.tif"


class V2CloseoutTests(unittest.TestCase):
    def _run(self, request: str, destination: Path, *, system: ExpertsRSSystem | None = None):
        return asyncio.run((system or ExpertsRSSystem()).run(RunRequest(
            request=request, data_paths=[SCENE], output_dir=destination, run_id="v2",
        )))

    def test_planned_and_observed_graphs_align_without_input_paths(self):
        system = ExpertsRSSystem(executor=LocalToolExecutor(inject_failures={"apply_threshold": 1}))
        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Calculate green cover rate for Dongcheng", Path(directory), system=system)
            run_dir = Path(directory) / "v2"
            planned = json.loads((run_dir / "planned_workflow_graph.json").read_text(encoding="utf-8"))
            observed = json.loads((run_dir / "observed_process_graph.json").read_text(encoding="utf-8"))
            trace = [json.loads(line) for line in result.trace_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(planned["view_type"], "planned_workflow_graph")
        self.assertEqual(observed["view_type"], "observed_process_graph")
        self.assertEqual(len(planned["plan_versions"]), 2)
        self.assertNotIn(str(SCENE), json.dumps(planned))
        node_ids = {
            node["node_id"]
            for version in planned["plan_versions"]
            for node in version["workflow"]["nodes"]
        }
        actions = [event["payload"] for event in trace if event["event_type"] == "action_started"]
        self.assertTrue(actions)
        self.assertTrue(all(action["plan_node_id"] in node_ids for action in actions))
        revisions = [event for event in trace if event["event_type"] == "agent_decision" and event["actor"] == "Scientist"]
        self.assertTrue(any(event["payload"]["decision"]["kind"] == "revise" for event in revisions))
        self.assertFalse(any(
            event["payload"].get("decision", {}).get("kind") == "revise" and event["actor"] == "Engineer"
            for event in trace if event["event_type"] == "agent_decision"
        ))

    def test_invalid_graph_dependency_stops_before_tools(self):
        class InvalidPlanProvider:
            async def decide(self, role, state):
                if role == "Manager":
                    return {"kind": "handoff", "target": "Scientist"}
                if role == "Scientist":
                    task, workflow = ScriptedDecisionProvider._workflow("ndvi", state["request"])
                    workflow["nodes"][0]["depends_on"] = ["index_map"]
                    return {"kind": "plan", "task": task, "workflow": workflow}
                raise AssertionError("invalid plan must not reach Engineer")

        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Map NDVI", Path(directory), system=ExpertsRSSystem(provider=InvalidPlanProvider()))
        self.assertEqual(result.status, RunStatus.CONTROLLED_STOP)
        self.assertEqual(result.validation.tool_calls, 0)

    def test_missing_report_deliverable_is_partial_not_false_success(self):
        class IncompleteReportProvider:
            def __init__(self):
                self.delegate = ScriptedDecisionProvider()

            async def decide(self, role, state):
                decision = await self.delegate.decide(role, state)
                if role == "Manager" and state["phase"] == "report":
                    decision["deliverables"] = []
                return decision

        with tempfile.TemporaryDirectory() as directory:
            result = self._run(
                "Calculate green cover rate for Dongcheng", Path(directory),
                system=ExpertsRSSystem(provider=IncompleteReportProvider()),
            )
            report = result.report or ""
        self.assertEqual(result.status, RunStatus.PARTIAL)
        self.assertIn("未完全交付", report)
        self.assertIn("green_cover_rate", report)

    def test_task11_ratio_is_scoped_to_valid_image_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Calculate green cover rate for Dongcheng", Path(directory))
            report = result.report or ""
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertIn("有效影像像元范围内", report)
        self.assertIn("40.76", report)
        self.assertNotIn("东城区绿地覆盖率", report)

    def test_vegetation_coverage_map_is_a_delivered_report_obligation(self):
        class CoverageMapProvider:
            def __init__(self):
                self.delegate = ScriptedDecisionProvider()

            async def decide(self, role, state):
                decision = await self.delegate.decide(role, state)
                if role == "Scientist" and decision.get("kind") == "plan":
                    decision["task"]["requested_outputs"] = ["vegetation_coverage_map", "green_cover_rate"]
                return decision

        with tempfile.TemporaryDirectory() as directory:
            result = self._run(
                "Calculate vegetation coverage and green cover rate for Dongcheng", Path(directory),
                system=ExpertsRSSystem(provider=CoverageMapProvider()),
            )
            report = result.report or ""
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertIn("vegetation_coverage_map: delivered", report)

    def test_persisted_provider_state_excludes_thought_events_and_resumes(self):
        class ThoughtStateProvider:
            def __init__(self):
                self.loaded = None

            async def decide(self, role, state):
                if role == "Manager" and state["phase"] == "initial":
                    return {"kind": "clarify", "question": "Please choose NDVI or green cover."}
                return await ScriptedDecisionProvider().decide(role, state)

            async def save_state(self):
                return {
                    "agent_states": {"manager": {"messages": [
                        {"type": "TextMessage", "content": "safe structured context"},
                        {"type": "ThoughtEvent", "content": "secret chain of thought", "reasoning": "hidden"},
                    ]}},
                    "reasoning_content": "also hidden",
                }

            async def load_state(self, state):
                self.loaded = state

        provider = ThoughtStateProvider()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = ExpertsRSSystem(provider=provider)
            first = self._run("What is the vegetation health condition?", root, system=system)
            saved = (root / "v2" / "state.json").read_text(encoding="utf-8")
            resumed = asyncio.run(system.resume(first.run_id, "Please produce an NDVI map.", root))
        self.assertEqual(first.status, RunStatus.NEEDS_CLARIFICATION)
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertNotIn("ThoughtEvent", saved)
        self.assertNotIn("chain of thought", saved)
        self.assertNotIn("reasoning_content", saved)
        self.assertIsNotNone(provider.loaded)
        self.assertNotIn("reasoning_content", json.dumps(provider.loaded))

    def test_v2_evaluator_separates_honest_partial_from_false_success(self):
        panel = load_panel()
        slot = next(
            item for item in build_case_slots(panel)
            if item.source_task_id == 11 and item.condition_id == "B3_checkpoint"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(run_unified_d3_case(slot, destination=Path(directory)))
            evaluation = evaluate_v2_unified_run(result, slot, panel=panel)
        self.assertTrue(evaluation["passed"])
        self.assertTrue(evaluation["plan_action_consistent"])
        self.assertTrue(evaluation["scientist_revision_consistent"])
        self.assertFalse(evaluation["false_success"])

    def test_v2_evaluator_accepts_a_no_action_controlled_stop(self):
        panel = load_panel()
        slot = next(
            item for item in build_case_slots(panel)
            if item.source_task_id == 3 and item.condition_id == "B2_adaptive"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(run_unified_d3_case(slot, destination=Path(directory)))
            evaluation = evaluate_v2_unified_run(result, slot, panel=panel)
        self.assertEqual(result.status, RunStatus.CONTROLLED_STOP)
        self.assertTrue(evaluation["passed"])
        self.assertTrue(evaluation["plan_action_consistent"])

    def test_v2_evaluator_maps_public_clarification_terminal(self):
        panel = load_panel()
        slot = next(
            item for item in build_case_slots(panel)
            if item.source_task_id == 13 and item.condition_id == "B3_checkpoint"
        )
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(run_unified_d3_case(slot, destination=Path(directory)))
            evaluation = evaluate_v2_unified_run(result, slot, panel=panel)
        self.assertEqual(result.status, RunStatus.NEEDS_CLARIFICATION)
        self.assertEqual(evaluation["evaluator_terminal_status"], "needs_user_clarification")
        self.assertTrue(evaluation["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
