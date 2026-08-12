"""One condition-aware D3-light runner with a deterministic no-API provider.

The fake provider exists only to exercise the runner, evaluator separation, and
all 15 condition/task slots.  A future live provider must implement the same
``next_step`` interface and may be added only after the API gate is approved.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from workflow import (
    Checkpoint,
    LocalPermissionPolicy,
    PermissionOutcome,
    PermissionRequest,
    PlanVersion,
    TOOL_EFFECTS,
    ToolEffect,
    WorkflowTrace,
    build_process_graph,
)

from .d3_light_loader import build_agent_case, build_evaluator_case, load_panel
from .d3_light_protocol import D3CaseSlot


class DecisionProvider(Protocol):
    """The deliberately narrow interface shared by fake and future live models."""

    def next_step(self, agent_case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]: ...


class DeterministicDryRunProvider:
    """A fixed policy that never reads hidden evaluator contracts."""

    def next_step(self, agent_case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        task_id = agent_case["source_task_id"]
        phase = state["phase"]
        if task_id == 2:
            return {"kind": "action", "tool": {"metadata": "read_raster_metadata", "ndvi": "calculate_ndvi", "map": "plot_index_map"}[phase]}
        if task_id == 3:
            return {"kind": "stop", "status": "controlled_stop", "reason": "registered NDSI operator unavailable"}
        if task_id == 10:
            if phase == "metadata":
                return {"kind": "action", "tool": "read_raster_metadata"}
            return {"kind": "stop", "status": "controlled_stop", "reason": "thermal precondition unavailable"}
        if task_id == 11:
            mapping = {"metadata": "read_raster_metadata", "ndvi": "calculate_ndvi", "threshold": "apply_threshold", "threshold_retry": "apply_threshold", "map": "plot_thematic_map", "area": "calculate_area"}
            return {"kind": "action", "tool": mapping[phase]}
        if task_id == 13:
            return {"kind": "clarify", "question": "What operational definition of vegetation health should be used?"}
        raise ValueError(f"Unsupported dry-run task: {task_id}")


@dataclass(frozen=True)
class DryRunResult:
    case_id: str
    source_task_id: int
    condition_id: str
    terminal_status: str
    trace: WorkflowTrace
    process_graph: dict[str, Any] | None
    evaluation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "source_task_id": self.source_task_id,
            "condition_id": self.condition_id,
            "terminal_status": self.terminal_status,
            "trace": self.trace.to_dict(),
            "process_graph": self.process_graph,
            "evaluation": self.evaluation,
        }


class D3LightRunner:
    """Runs B1/B2/B3 through a shared execution skeleton and evaluator view."""

    def __init__(self, panel: dict[str, Any], provider: DecisionProvider) -> None:
        self.panel = panel
        self.provider = provider
        root = Path(__file__).resolve().parents[2]
        self.data_root = root / "data"
        self.results_root = root / "results"
        self.policy = LocalPermissionPolicy([self.data_root], [self.results_root])

    def run(self, slot: D3CaseSlot) -> DryRunResult:
        agent_case = build_agent_case(self.panel, slot.source_task_id, slot.condition_id)
        evaluator_case = build_evaluator_case(self.panel, slot.source_task_id, slot.condition_id)
        condition = evaluator_case["condition"]
        trace = WorkflowTrace(f"dry_{slot.case_id}")
        state: dict[str, Any] = {"phase": "metadata", "actions": 0, "failure_injected": False}
        plan_id = self._record_initial_plan(trace, agent_case, condition)

        if slot.source_task_id == 3:
            terminal = self._record_stop(trace, "controlled_stop", "registered NDSI operator unavailable")
        elif slot.source_task_id == 13:
            trace.record(
                "manager_clarification_requested",
                {"question": self.provider.next_step(agent_case, {"phase": "clarify"})["question"]},
                actor="Manager",
                object_id="clarification-request",
                references=(),
            )
            terminal = self._record_stop(trace, "needs_user_clarification", "unresolved user definition")
        else:
            terminal = self._run_tool_path(trace, agent_case, evaluator_case, plan_id, state)

        graph = None
        if condition["process_graph_from_run_facts"]:
            graph = build_process_graph(trace.run_id, trace.events).to_dict()
        evaluation = evaluate_dry_run(trace, evaluator_case, terminal, graph)
        return DryRunResult(slot.case_id, slot.source_task_id, slot.condition_id, terminal, trace, graph, evaluation)

    def _record_initial_plan(
        self, trace: WorkflowTrace, agent_case: dict[str, Any], condition: dict[str, Any]
    ) -> str:
        if condition["plan_revision_after_tool_observation"]:
            plan = PlanVersion(
                f"{agent_case['condition_id']}-task-{agent_case['source_task_id']}", 1,
                agent_case["request"], "initial", "inspect available data and execute the next supported action",
            )
            trace.record_plan_version(plan)
            return plan.object_id
        trace.record(
            "static_plan_recorded",
            {"goal": agent_case["request"], "mode": "upfront_static"},
            actor="Scientist",
            object_id="static-plan",
        )
        return "static-plan"

    def _run_tool_path(
        self,
        trace: WorkflowTrace,
        agent_case: dict[str, Any],
        evaluator_case: dict[str, Any],
        plan_id: str,
        state: dict[str, Any],
    ) -> str:
        task_id = agent_case["source_task_id"]
        condition = evaluator_case["condition"]
        artifact_ids: list[str] = []
        while state["actions"] < 8:
            decision = self.provider.next_step(agent_case, state)
            if decision["kind"] == "stop":
                return self._record_stop(trace, decision["status"], decision["reason"])
            tool_name = decision["tool"]
            action_id, observation_id, success = self._record_mock_action(
                trace, plan_id, tool_name, state, task_id, evaluator_case["fixture"], condition
            )
            state["actions"] += 1
            if not success:
                if not condition["plan_revision_after_tool_observation"]:
                    return self._record_stop(trace, "controlled_stop", "tool observation failed in static condition")
                plan_id = self._record_revised_plan(trace, plan_id, observation_id, condition, artifact_ids)
                state["phase"] = "threshold_retry"
                continue
            artifact_id = self._artifact_for_tool(trace, action_id, tool_name, condition, task_id)
            if artifact_id:
                artifact_ids.append(artifact_id)
            if task_id == 10 and state["phase"] == "metadata":
                state["phase"] = "thermal_check"
                continue
            if task_id == 2:
                state["phase"] = {"metadata": "ndvi", "ndvi": "map", "map": "done"}[state["phase"]]
                if state["phase"] == "done":
                    return self._record_stop(trace, "completed", "all requested artifacts recorded")
            if task_id == 11:
                state["phase"] = {
                    "metadata": "ndvi",
                    "ndvi": "threshold",
                    "threshold": "map",
                    "threshold_retry": "map",
                    "map": "area",
                    "area": "done",
                }[state["phase"]]
                if state["phase"] == "ndvi" and condition["checkpoint_recovery"]:
                    trace.record_checkpoint(Checkpoint(
                        "checkpoint-after-ndvi", plan_id, observation_id, tuple(artifact_ids),
                        reason="NDVI artifact observed and recorded",
                    ))
                if state["phase"] == "done":
                    return self._record_stop(trace, "completed", "all requested artifacts recorded")
        return self._record_stop(trace, "budget_exhausted", "dry-run action budget exhausted")

    def _record_mock_action(
        self,
        trace: WorkflowTrace,
        plan_id: str,
        tool_name: str,
        state: dict[str, Any],
        task_id: int,
        fixture: dict[str, Any],
        condition: dict[str, Any],
    ) -> tuple[str, str, bool]:
        effect = TOOL_EFFECTS[tool_name]
        resource = str(self.data_root / "Sentinel2_Dongcheng_20230718.tif") if effect == ToolEffect.READ else str(self.results_root)
        request_id = f"permission-{state['actions'] + 1}-{tool_name}"
        request = PermissionRequest(request_id, "Engineer", tool_name, effect, resource)
        permission = self.policy.evaluate(request)
        trace.record_permission(request, permission)
        if permission.outcome != PermissionOutcome.ALLOW:
            raise RuntimeError(f"Dry-run permission unexpectedly denied: {permission.reason}")
        action_id = f"action-{state['actions'] + 1}-{tool_name}"
        trace.record_action(
            action_id, "Engineer", tool_name, {"fixture": "dry-run"}, plan_id, permission.decision_id
        )
        inject = (
            fixture["kind"] == "seeded_transient_tool_failure"
            and tool_name == "apply_threshold"
            and not state["failure_injected"]
        )
        if inject:
            state["failure_injected"] = True
            observation_payload = fixture["injected_observation"]
            success = False
        else:
            observation_payload = {"message": f"deterministic dry-run {tool_name} success"}
            success = True
        observation_id = f"observation-{state['actions'] + 1}-{tool_name}"
        trace.record_observation(observation_id, "Executor", action_id, success, observation_payload)
        return action_id, observation_id, success

    @staticmethod
    def _artifact_for_tool(
        trace: WorkflowTrace, action_id: str, tool_name: str, condition: dict[str, Any], task_id: int
    ) -> str | None:
        artifact_type = {
            "read_raster_metadata": "metadata",
            "calculate_ndvi": "index_raster",
            "apply_threshold": "mask_raster",
            "plot_index_map": "map",
            "plot_thematic_map": "map",
            "calculate_area": "area_statistics",
        }.get(tool_name)
        if artifact_type is None:
            return None
        artifact_id = f"artifact-{artifact_type}-{action_id}"
        trace.record_artifact(
            artifact_id,
            "Executor",
            action_id,
            f"memory://{artifact_id}",
            True,
            artifact_type=artifact_type,
        )
        return artifact_id

    @staticmethod
    def _record_stop(trace: WorkflowTrace, status: str, reason: str) -> str:
        trace.record("run_terminal", {"status": status, "reason": reason}, actor="Runtime")
        trace.record_final_status(status, [])
        return status

    @staticmethod
    def _record_revised_plan(
        trace: WorkflowTrace,
        previous_plan_id: str,
        trigger_event_id: str,
        condition: dict[str, Any],
        artifact_ids: list[str],
    ) -> str:
        version = 2
        restart = "checkpoint-after-ndvi" if condition["checkpoint_recovery"] else None
        plan = PlanVersion(
            previous_plan_id.rsplit(":v", 1)[0], version,
            "continue only the failed task region", "recover", "retry threshold then downstream steps",
            branch_id="recovery", parent_version_id=previous_plan_id,
            trigger_event_id=trigger_event_id, restart_from_checkpoint_id=restart,
        )
        trace.record_plan_version(plan)
        return plan.object_id


def evaluate_dry_run(
    trace: WorkflowTrace,
    evaluator_case: dict[str, Any],
    terminal_status: str,
    graph: dict[str, Any] | None,
) -> dict[str, Any]:
    """Minimal external evaluator used only for deterministic pre-flight checks."""
    contract = evaluator_case["chapter1_contract"]
    condition_id = evaluator_case["condition_id"]
    event_types = [event["event_type"] for event in trace.events]
    actions = [
        event["payload"].get("tool_name")
        for event in trace.events
        if event["event_type"] == "action_started"
    ]
    observations = [
        event["payload"] for event in trace.events
        if event["event_type"] == "tool_observation_recorded"
    ]
    terminal_events = [
        event["payload"] for event in trace.events
        if event["event_type"] == "run_terminal"
    ]
    observed_artifacts = {
        event["payload"].get("artifact_type")
        for event in trace.events
        if event["event_type"] == "artifact_recorded"
    }
    allowed = terminal_status in contract["allowed_terminal_by_condition"][condition_id]
    has_final = event_types[-1:] == ["run_completed"]
    revision_required = condition_id in {"B2_adaptive", "B3_checkpoint"} and evaluator_case["source_task_id"] == 11
    has_revision = "plan_version_recorded" in event_types and sum(
        event["event_type"] == "plan_version_recorded" for event in trace.events
    ) >= 2
    checkpoint_required = condition_id == "B3_checkpoint" and evaluator_case["source_task_id"] == 11
    has_checkpoint = "checkpoint_recorded" in event_types
    graph_required = evaluator_case["condition"]["process_graph_from_run_facts"]
    required_artifacts = set(
        contract.get("required_artifact_types", contract.get("required_artifact_types_on_completion", []))
    )
    artifacts_complete = terminal_status != "completed" or required_artifacts.issubset(observed_artifacts)
    ndvi_action_count = sum(
        event["event_type"] == "action_started"
        and event["payload"].get("tool_name") == "calculate_ndvi"
        for event in trace.events
    )
    recovery_locality = (
        not checkpoint_required or ndvi_action_count == 1
    )
    task_id = evaluator_case["source_task_id"]
    task_specific_evidence = {
        2: {"read_raster_metadata", "calculate_ndvi", "plot_index_map"}.issubset(actions),
        3: not actions and bool(terminal_events) and "NDSI" in terminal_events[-1]["reason"],
        10: "read_raster_metadata" in actions and bool(terminal_events) and "thermal" in terminal_events[-1]["reason"],
        11: any(item.get("error_code") == "fixture_transient_write_failure" for item in observations),
        13: "manager_clarification_requested" in event_types and not actions,
    }[task_id]
    complete = allowed and has_final and artifacts_complete and recovery_locality and task_specific_evidence and (not revision_required or has_revision) and (not checkpoint_required or has_checkpoint) and (not graph_required or graph is not None)
    return {
        "passed": complete,
        "terminal_allowed": allowed,
        "final_event_present": has_final,
        "required_artifacts": sorted(required_artifacts),
        "observed_artifacts": sorted(item for item in observed_artifacts if item),
        "artifacts_complete": artifacts_complete,
        "revision_required": revision_required,
        "revision_present": has_revision,
        "checkpoint_required": checkpoint_required,
        "checkpoint_present": has_checkpoint,
        "graph_required": graph_required,
        "graph_present": graph is not None,
        "ndvi_action_count": ndvi_action_count,
        "recovery_locality": recovery_locality,
        "task_specific_evidence": task_specific_evidence,
    }
