"""Versioned external evaluator for the v0.5.2 Chapter 1 closeout.

It consumes public runtime outputs and the frozen panel through the existing
loader.  It neither sends a role instruction nor changes any v1 panel/gold
asset, so v1 results remain independently interpretable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .d3_light_loader import build_evaluator_case, load_panel
from .d3_light_protocol import D3CaseSlot


V2_PROTOCOL_VERSION = "ch1-v2.1"


def evaluate_v2_unified_run(result: Any, slot: D3CaseSlot, *, panel: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assess v2 planning/report evidence without exposing rubric to Agents."""
    panel = panel or load_panel()
    private_case = build_evaluator_case(panel, slot.source_task_id, slot.condition_id)
    trace_path = Path(result.trace_path)
    run_dir = trace_path.parent
    trace = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line]
    planned_path = run_dir / "planned_workflow_graph.json"
    observed_path = run_dir / "observed_process_graph.json"
    obligations_path = run_dir / "delivery_obligations.json"
    planned = json.loads(planned_path.read_text(encoding="utf-8")) if planned_path.is_file() else {}
    observed = json.loads(observed_path.read_text(encoding="utf-8")) if observed_path.is_file() else {}
    obligations = json.loads(obligations_path.read_text(encoding="utf-8")) if obligations_path.is_file() else {}
    plans = planned.get("plan_versions", [])
    planned_node_ids = {
        node["node_id"]
        for version in plans
        for node in version.get("workflow", {}).get("nodes", [])
    }
    actions = [event for event in trace if event["event_type"] == "action_started"]
    observations = [event for event in trace if event["event_type"] == "tool_observation_recorded"]
    revisions = [
        event for event in trace
        if event["event_type"] == "agent_decision"
        and event.get("actor") == "Scientist"
        and event.get("payload", {}).get("decision", {}).get("kind") == "revise"
    ]
    report_events = [event for event in trace if event["event_type"] == "report_validated"]
    artifacts = [event["payload"] for event in trace if event["event_type"] == "artifact_recorded"]
    required_obligations = obligations.get("obligations", [])
    required_ids = {item["obligation_id"] for item in required_obligations}
    actions_align = all(
        event["payload"].get("plan_node_id") in planned_node_ids for event in actions
    )
    observations_align = all(
        event["payload"].get("plan_node_id") in planned_node_ids for event in observations
    )
    revision_required = slot.source_task_id == 11 and slot.condition_id in {"B2_adaptive", "B3_checkpoint"}
    revision_aligns = not revision_required or (
        bool(revisions)
        and all(event["payload"]["decision"]["base_plan_id"] for event in revisions)
    )
    report_incomplete = report_events[-1]["payload"].get("incomplete_deliverable_ids", []) if report_events else []
    delivered_ids = set(report_events[-1]["payload"].get("deliverable_ids", [])) if report_events else set()
    artifact_types = {item.get("artifact_type") for item in artifacts}
    artifact_nodes = {item.get("plan_node_id") for item in artifacts}
    obligation_artifacts_ok = all(
        set(item.get("required_artifact_types", [])).issubset(artifact_types)
        and set(item.get("required_plan_node_ids", [])).issubset(artifact_nodes)
        for item in required_obligations
    )
    obligation_chain_complete = required_ids.issubset(delivered_ids) and obligation_artifacts_ok and not set(report_incomplete).intersection(required_ids)
    status = result.status.value
    evaluator_status = {"needs_clarification": "needs_user_clarification"}.get(status, status)
    terminal_allowed = evaluator_status in private_case["chapter1_contract"]["allowed_terminal_by_condition"][slot.condition_id]
    # A v2 partial is an honest terminal for a report obligation that could not
    # be evidenced; it is not upgraded to a successful task outcome.
    obligation_required_for_terminal = status in {"completed", "partial"}
    protocol_closed = terminal_allowed or status == "partial"
    false_success = status == "completed" and (bool(report_incomplete) or not obligation_chain_complete)
    return {
        "protocol_version": V2_PROTOCOL_VERSION,
        "passed": bool(
            protocol_closed
            and planned.get("view_type") == "planned_workflow_graph"
            and observed.get("view_type") == "observed_process_graph"
            and actions_align
            and observations_align
            and revision_aligns
            and (not obligation_required_for_terminal or obligation_chain_complete)
            and not false_success
        ),
        "terminal_status": status,
        "evaluator_terminal_status": evaluator_status,
        "protocol_closed": protocol_closed,
        "planned_graph_present": planned_path.is_file(),
        "observed_graph_present": observed_path.is_file(),
        "plan_action_consistent": actions_align,
        "plan_observation_consistent": observations_align,
        "revision_required": revision_required,
        "scientist_revision_consistent": revision_aligns,
        "report_incomplete_deliverable_ids": report_incomplete,
        "delivery_obligation_manifest_present": obligations_path.is_file(),
        "required_delivery_obligations": sorted(required_ids),
        "reported_delivery_obligations": sorted(delivered_ids),
        "obligation_artifacts_validated": obligation_artifacts_ok,
        "obligation_chain_complete": obligation_chain_complete,
        "obligation_required_for_terminal": obligation_required_for_terminal,
        "revision_change_classes": [item.get("revision_change_class") for item in plans],
        "false_success": false_success,
    }
