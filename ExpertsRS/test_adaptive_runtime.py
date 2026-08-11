"""Focused no-API tests for the Chapter 1 run interfaces."""

import json
import tempfile
import unittest
from pathlib import Path

from tools.registry import list_tools
from workflow import (
    Checkpoint,
    EventReference,
    LocalPermissionPolicy,
    PermissionOutcome,
    PermissionRequest,
    PlanVersion,
    TOOL_EFFECTS,
    ToolEffect,
    WorkflowTrace,
    build_process_graph,
)


class AdaptiveRuntimeTests(unittest.TestCase):
    def test_revised_plan_requires_parent_and_real_trigger(self):
        with self.assertRaises(ValueError):
            PlanVersion("plan", 2, "goal", "analysis", "retry")
        revised = PlanVersion(
            "plan", 2, "goal", "analysis", "retry with another input",
            parent_version_id="plan:v1", trigger_event_id="run:e0004",
        )
        self.assertEqual(revised.object_id, "plan:v2")

    def test_trace_adds_stable_envelope_without_changing_payload(self):
        trace = WorkflowTrace("run")
        event_id = trace.record("legacy_event", {"answer": 42}, actor="Scientist")
        event = trace.events[0]
        self.assertEqual(event_id, "run:e0001")
        self.assertEqual(event["sequence_no"], 1)
        self.assertEqual(event["payload"], {"answer": 42})
        self.assertEqual(event["actor"], "Scientist")

    def test_complete_run_facts_build_a_deterministic_process_view(self):
        trace = self._example_trace()
        first = build_process_graph(trace.run_id, trace.events).to_dict()
        second = build_process_graph(trace.run_id, trace.events).to_dict()
        self.assertEqual(first, second)
        relations = {edge["relation"] for edge in first["edges"]}
        self.assertTrue({
            "implements", "authorized_by", "observes", "produced_by",
            "reuses_valid_artifact", "revises", "triggered_by", "restarts_from",
        }.issubset(relations))

    def test_plan_history_is_preserved_in_process_view(self):
        graph = build_process_graph("run", self._example_trace().events)
        node_ids = {node.node_id for node in graph.nodes}
        self.assertIn("plan:v1", node_ids)
        self.assertIn("plan:v2", node_ids)
        self.assertIn(
            ("plan:v1", "plan:v2", "revises"),
            {(edge.source, edge.target, edge.relation) for edge in graph.edges},
        )

    def test_checkpoint_references_instead_of_copying_valid_artifact(self):
        trace = self._example_trace()
        checkpoint_event = next(
            event for event in trace.events if event["event_type"] == "checkpoint_recorded"
        )
        self.assertEqual(checkpoint_event["payload"]["valid_artifact_ids"], ["metadata-1"])
        self.assertNotIn("artifact_payload", checkpoint_event["payload"])

    def test_dangling_process_reference_is_rejected(self):
        events = [{
            "event_id": "run:e0001",
            "sequence_no": 1,
            "event_type": "action_started",
            "payload": {},
            "references": [EventReference("missing-plan", "implements").to_dict()],
        }]
        with self.assertRaisesRegex(ValueError, "Unknown process reference"):
            build_process_graph("run", events)

    def test_permission_policy_allows_only_configured_local_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            results = root / "results"
            data.mkdir()
            results.mkdir()
            policy = LocalPermissionPolicy([data], [results])

            allowed_read = policy.evaluate(PermissionRequest(
                "read-1", "Scientist", "read_raster_metadata", ToolEffect.READ,
                str(data / "scene.tif"),
            ))
            denied_read = policy.evaluate(PermissionRequest(
                "read-2", "Scientist", "read_raster_metadata", ToolEffect.READ,
                str(root / "private" / "scene.tif"),
            ))
            allowed_write = policy.evaluate(PermissionRequest(
                "write-1", "Engineer", "calculate_ndvi",
                ToolEffect.WRITE_LOCAL_ARTIFACT, str(results / "ndvi.tif"),
            ))
            denied_write = policy.evaluate(PermissionRequest(
                "write-2", "Engineer", "calculate_ndvi",
                ToolEffect.WRITE_LOCAL_ARTIFACT, str(root / "ndvi.tif"),
            ))

        self.assertEqual(allowed_read.outcome, PermissionOutcome.ALLOW)
        self.assertEqual(allowed_write.outcome, PermissionOutcome.ALLOW)
        self.assertEqual(denied_read.outcome, PermissionOutcome.DENY)
        self.assertEqual(denied_write.outcome, PermissionOutcome.DENY)

    def test_unknown_and_misdeclared_tools_are_denied(self):
        policy = LocalPermissionPolicy([], [])
        unknown = policy.evaluate(PermissionRequest(
            "unknown", "Engineer", "delete_everything", ToolEffect.IRREVERSIBLE,
        ))
        mismatched = policy.evaluate(PermissionRequest(
            "mismatch", "Engineer", "calculate_area", ToolEffect.WRITE_LOCAL_ARTIFACT,
        ))
        self.assertEqual(unknown.outcome, PermissionOutcome.DENY)
        self.assertEqual(mismatched.reason, "declared_effect_does_not_match_tool")

    def test_effect_table_covers_exactly_the_public_tool_registry(self):
        self.assertEqual(set(TOOL_EFFECTS), set(list_tools()))
        self.assertEqual(
            sum(effect == ToolEffect.READ for effect in TOOL_EFFECTS.values()), 4
        )
        self.assertEqual(
            sum(effect == ToolEffect.COMPUTE for effect in TOOL_EFFECTS.values()), 2
        )

    def test_extended_trace_remains_portable_json(self):
        trace = self._example_trace()
        with tempfile.TemporaryDirectory() as directory:
            path = trace.write(Path(directory) / "trace.json")
            restored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(restored["run_id"], "run")
        self.assertEqual(len(restored["events"]), len(trace.events))

    @staticmethod
    def _example_trace() -> WorkflowTrace:
        trace = WorkflowTrace("run")
        plan_v1 = PlanVersion("plan", 1, "inspect a scene", "inspection", "read metadata")
        trace.record_plan_version(plan_v1)

        request = PermissionRequest(
            "permission-1", "Scientist", "read_raster_metadata", ToolEffect.READ,
            str(Path.cwd() / "data" / "scene.tif"),
        )
        policy = LocalPermissionPolicy([Path.cwd() / "data"], [Path.cwd() / "results"])
        decision = policy.evaluate(request)
        trace.record_permission(request, decision)
        action_event_id = trace.record_action(
            "action-1", "Scientist", request.tool_name, {"file_path": request.resource},
            plan_v1.object_id, decision.decision_id,
        )
        observation_event_id = trace.record_observation(
            "observation-1", "Executor", "action-1", True,
            {"band_descriptions": ["B2", "B3", "B4", "B8"]},
        )
        trace.record_artifact(
            "metadata-1", "Executor", "action-1", "memory://metadata-1", True
        )
        trace.record_checkpoint(Checkpoint(
            "checkpoint-1", plan_v1.object_id, action_event_id, ("metadata-1",),
            reason="metadata verified",
        ))
        trace.record_plan_version(PlanVersion(
            "plan", 2, "inspect a scene", "analysis", "select bands by description",
            parent_version_id=plan_v1.object_id,
            trigger_event_id=observation_event_id,
            restart_from_checkpoint_id="checkpoint-1",
        ))
        return trace


if __name__ == "__main__":
    unittest.main(verbosity=2)
