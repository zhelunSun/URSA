"""One condition-aware D3-light local mechanism runner.

The deterministic substitute exists only to exercise the runner, evaluator
separation, and all 15 condition/task slots. Its task/phase transitions are
purposefully constrained and do not implement real multi-agent scheduling. A
future live experiment must bridge the existing AG2/AutoGen routing rather than
replace it with this runner's ``next_step`` interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

try:  # Source-tree compatibility for historical tests.
    from ...workflow import (
        Checkpoint, LocalPermissionPolicy, PermissionOutcome, PermissionRequest,
        PlanVersion, TOOL_EFFECTS, ToolEffect, WorkflowTrace, build_process_graph,
    )
except ImportError:  # pragma: no cover - legacy invocation from ExpertsRS/.
    from workflow import (
        Checkpoint, LocalPermissionPolicy, PermissionOutcome, PermissionRequest,
        PlanVersion, TOOL_EFFECTS, ToolEffect, WorkflowTrace, build_process_graph,
    )

# The legacy D3 runner below is retained only to reproduce previously frozen
# no-API manifests.  New evaluator integrations call the authoritative system
# entry point through ``run_unified_d3_case`` at the end of this module.

from .d3_light_loader import build_agent_case, build_evaluator_case, load_panel
from .d3_light_protocol import D3CaseSlot, api_calls_permitted, balanced_case_order, build_case_slots


ROOT = Path(__file__).resolve().parents[2]


class DecisionProvider(Protocol):
    """Narrow local test interface; deliberately not an Agent framework interface."""

    def next_step(self, agent_case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]: ...


class ToolExecutor(Protocol):
    """Local execution boundary used by the same runner in a real-tool check."""

    def begin_case(self) -> None: ...

    def execute(
        self, tool_name: str, artifacts: dict[str, str], *, inject_transient_failure: bool = False
    ) -> dict[str, Any]: ...


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

    def __init__(
        self,
        panel: dict[str, Any],
        provider: DecisionProvider,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        self.panel = panel
        self.provider = provider
        self.tool_executor = tool_executor
        root = Path(__file__).resolve().parents[2]
        self.data_root = root / "data"
        self.results_root = root / "results"
        self.policy = LocalPermissionPolicy([self.data_root], [self.results_root])

    def run(self, slot: D3CaseSlot) -> DryRunResult:
        agent_case = build_agent_case(self.panel, slot.source_task_id, slot.condition_id)
        evaluator_case = build_evaluator_case(self.panel, slot.source_task_id, slot.condition_id)
        condition = evaluator_case["condition"]
        trace = WorkflowTrace(f"dry_{slot.case_id}")
        state: dict[str, Any] = {
            "phase": "metadata",
            "actions": 0,
            "failure_injected": False,
            "artifacts": {},
            "available_tools": self._available_tools(slot.source_task_id),
            "remaining_tool_budget": 10,
            "last_observation": {},
        }
        if self.tool_executor is not None:
            self.tool_executor.begin_case()
        plan_id = self._record_initial_plan(trace, agent_case, condition)

        if slot.source_task_id == 3:
            if self._model_budget_exhausted(state):
                terminal = self._record_stop(trace, "budget_exhausted", "model-turn budget exhausted")
                return self._finish(trace, evaluator_case, slot, terminal, condition)
            decision = self.provider.next_step(agent_case, state)
            self._record_decision(trace, decision, state)
            if decision.get("kind") != "stop":
                terminal = self._record_stop(trace, "protocol_violation", "missing operator task requires an explicit stop")
            else:
                terminal = self._record_stop(trace, decision["status"], decision["reason"])
        elif slot.source_task_id == 13:
            if self._model_budget_exhausted(state):
                terminal = self._record_stop(trace, "budget_exhausted", "model-turn budget exhausted")
                return self._finish(trace, evaluator_case, slot, terminal, condition)
            decision = self.provider.next_step(agent_case, {**state, "phase": "clarify"})
            self._record_decision(trace, decision, {**state, "phase": "clarify"})
            if decision.get("kind") != "clarify":
                terminal = self._record_stop(trace, "protocol_violation", "unresolved user definition requires clarification")
            else:
                trace.record(
                    "manager_clarification_requested",
                    {"question": decision["question"]},
                    actor="Manager",
                    object_id="clarification-request",
                    references=(),
                )
                terminal = self._record_stop(trace, "needs_user_clarification", "unresolved user definition")
        else:
            terminal = self._run_tool_path(trace, agent_case, evaluator_case, plan_id, state)

        return self._finish(trace, evaluator_case, slot, terminal, condition)

    @staticmethod
    def _finish(
        trace: WorkflowTrace,
        evaluator_case: dict[str, Any],
        slot: D3CaseSlot,
        terminal: str,
        condition: dict[str, Any],
    ) -> DryRunResult:
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
        while state["actions"] < self.panel["proposed_run_protocol"]["per_run_budget"]["max_tool_calls"]:
            if self._model_budget_exhausted(state):
                return self._record_stop(trace, "budget_exhausted", "model-turn budget exhausted")
            decision = self.provider.next_step(agent_case, state)
            self._record_decision(trace, decision, state)
            state["model_turns"] = state.get("model_turns", 0) + 1
            if decision["kind"] == "stop":
                return self._record_stop(trace, decision["status"], decision["reason"])
            tool_name = decision["tool"]
            if tool_name not in state["available_tools"]:
                return self._record_stop(trace, "protocol_violation", f"unavailable tool proposed: {tool_name}")
            action_id, observation_id, success = self._record_tool_action(
                trace, plan_id, tool_name, state, task_id, evaluator_case["fixture"], condition
            )
            state["actions"] += 1
            state["remaining_tool_budget"] -= 1
            if not success:
                if not condition["plan_revision_after_tool_observation"]:
                    return self._record_stop(trace, "controlled_stop", "tool observation failed in static condition")
                plan_id = self._record_revised_plan(trace, plan_id, observation_id, condition, artifact_ids)
                state["phase"] = "threshold_retry"
                continue
            artifact_id = self._artifact_for_tool(trace, action_id, tool_name, state)
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

    def _model_budget_exhausted(self, state: dict[str, Any]) -> bool:
        return state.get("model_turns", 0) >= self.panel["proposed_run_protocol"]["per_run_budget"]["max_model_turns"]

    @staticmethod
    def _record_decision(
        trace: WorkflowTrace, decision: dict[str, Any], state: dict[str, Any]
    ) -> None:
        """Record the decision boundary, never the model's hidden reasoning text."""
        payload = {key: decision[key] for key in ("kind", "tool", "status", "reason", "question", "plan_update") if key in decision}
        if isinstance(decision.get("usage"), dict):
            payload["usage"] = {
                key: value for key, value in decision["usage"].items()
                if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
                and isinstance(value, (int, float))
            }
        if isinstance(decision.get("provider_model"), str):
            payload["provider_model"] = decision["provider_model"]
        actor = "Manager" if decision.get("kind") == "clarify" else (
            "Scientist" if state["phase"] in {"metadata", "thermal_check"} else "Engineer"
        )
        trace.record("role_decision_recorded", payload, actor=actor, object_id=f"decision-{state['actions'] + 1}")

    def _record_tool_action(
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
        arguments = {"fixture": "dry-run"} if self.tool_executor is None else {"mode": "registered_local_tool"}
        trace.record_action(action_id, "Engineer", tool_name, arguments, plan_id, permission.decision_id)
        if self.tool_executor is not None:
            result = self.tool_executor.execute(
                tool_name,
                state["artifacts"],
                inject_transient_failure=(
                    fixture["kind"] == "seeded_transient_tool_failure"
                ),
            )
            success = bool(result.get("success"))
            observation_payload = self._compact_tool_result(tool_name, result)
            state["last_observation"] = observation_payload
            observation_id = f"observation-{state['actions'] + 1}-{tool_name}"
            trace.record_observation(observation_id, "Executor", action_id, success, observation_payload)
            return action_id, observation_id, success
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
        state["last_observation"] = observation_payload
        observation_id = f"observation-{state['actions'] + 1}-{tool_name}"
        trace.record_observation(observation_id, "Executor", action_id, success, observation_payload)
        return action_id, observation_id, success

    @staticmethod
    def _compact_tool_result(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
        """Keep a useful local trace without embedding full tool data or paths in an observation."""
        data = result.get("data")
        payload: dict[str, Any] = {
            "tool_name": tool_name,
            "message": str(result.get("message", "")),
        }
        if not result.get("success"):
            payload["error_code"] = str(result.get("error_code", "tool_failed"))
        if isinstance(data, dict):
            for key in ("output_path", "file_name", "shape", "valid_pixels", "total_pixels", "nodata_pixels"):
                if key in data:
                    payload[key] = data[key]
        return payload

    @staticmethod
    def _available_tools(task_id: int) -> list[str]:
        return {
            2: ["read_raster_metadata", "calculate_ndvi", "plot_index_map"],
            3: [],
            10: ["read_raster_metadata"],
            11: [
                "read_raster_metadata",
                "calculate_ndvi",
                "apply_threshold",
                "plot_thematic_map",
                "calculate_area",
            ],
            13: [],
        }[task_id]

    @staticmethod
    def _artifact_for_tool(
        trace: WorkflowTrace, action_id: str, tool_name: str, state: dict[str, Any]
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
        output_path = state.get("last_observation", {}).get("output_path")
        uri = str(output_path) if output_path else f"memory://{artifact_id}"
        state["artifacts"][artifact_type] = uri
        trace.record_artifact(
            artifact_id,
            "Executor",
            action_id,
            uri,
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


async def run_unified_d3_case(
    slot: D3CaseSlot,
    *,
    destination: str | Path,
    system: Any | None = None,
    provider_config: Any | None = None,
) -> Any:
    """Run one D3 case through the authoritative ExpertsRS API.

    The evaluator converts B1/B2/B3 only into capability policy.  It never
    supplies an action sequence, a role phase, hidden gold, or fixture content
    to the decision provider.  A caller may inject a local Executor failure for
    the reviewed task-11 fixture.
    """
    try:
        from ExpertsRS import ExpertsRSSystem, LocalToolExecutor, RunBudgets, RunRequest, RuntimeCapabilities
    except ModuleNotFoundError:  # Legacy test invocation executes from ExpertsRS/.
        import sys
        sys.path.insert(0, str(ROOT.parent))
        from ExpertsRS import ExpertsRSSystem, LocalToolExecutor, RunBudgets, RunRequest, RuntimeCapabilities

    panel = load_panel()
    agent_case = build_agent_case(panel, slot.source_task_id, slot.condition_id)
    condition = panel["conditions"][slot.condition_id]
    if system is None:
        failures = {"apply_threshold": 1} if slot.source_task_id == 11 else {}
        fixture_ids = {"apply_threshold": "d3-task-11-threshold-once"} if failures else {}
        system = ExpertsRSSystem(executor=LocalToolExecutor(
            inject_failures=failures, injected_failure_ids=fixture_ids,
        ))
    capabilities = RuntimeCapabilities(
        allow_plan_revision=bool(condition["plan_revision_after_tool_observation"]),
        allow_checkpoint_recovery=bool(condition["checkpoint_recovery"]),
    )
    source = Path(panel["fixed_context"]["raster"])
    if not source.is_absolute():
        source = ROOT / "data" / source.name
    budget_config = panel["proposed_run_protocol"]["per_run_budget"]
    budgets = RunBudgets(
        max_model_turns=budget_config["max_model_turns"],
        max_tool_calls=budget_config["max_tool_calls"],
        max_tool_calls_scientist=budget_config["max_tool_calls_scientist"],
        max_tool_calls_engineer=budget_config["max_tool_calls_engineer"],
        max_wall_time_seconds=budget_config["max_wall_time_seconds"],
        max_total_tokens_recorded=budget_config["max_total_tokens_recorded"],
    )
    return await system.run(RunRequest(
        request=agent_case["request"], data_paths=[source], output_dir=Path(destination),
        run_id=slot.case_id.replace("__", "_"), capabilities=capabilities, budgets=budgets,
        execution_mode=("autogen-live" if provider_config is not None else "scripted-offline"),
        provider=provider_config,
    ))


async def run_authorized_d3_smoke(
    destination: str | Path,
    provider_config: Any,
    *,
    slots: list[D3CaseSlot] | None = None,
    panel: dict[str, Any] | None = None,
    system_factory: Any | None = None,
) -> list[dict[str, Any]]:
    """Run reviewed smoke slots via the authoritative live runtime only.

    The frozen panel must explicitly open its reviewed gate *and* the local
    environment must set ``EXPERTSRS_D3_LIGHT_ALLOW_API=YES``.  Each slot keeps
    its own non-overwriting run directory; any failed evaluator result stops
    the batch immediately and preserves the partial run for review.
    """
    panel = panel or load_panel()
    if not api_calls_permitted(panel):
        raise RuntimeError("D3 live smoke requires both the reviewed panel gate and EXPERTSRS_D3_LIGHT_ALLOW_API=YES")
    selected = slots or balanced_case_order(build_case_slots(panel))
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for slot in selected:
        system = system_factory(slot) if system_factory is not None else None
        result = await run_unified_d3_case(
            slot, destination=root, system=system, provider_config=provider_config,
        )
        evaluation = evaluate_unified_d3_run(
            result, build_evaluator_case(panel, slot.source_task_id, slot.condition_id),
        )
        record = {
            "case_id": slot.case_id,
            "mode": "unified_runtime_autogen_live",
            "result": result.model_dump(mode="json"),
            "evaluation": evaluation,
        }
        path = root / f"{len(results) + 1:02d}_{slot.case_id}.json"
        path.write_text(__import__("json").dumps(record, indent=2), encoding="utf-8")
        results.append(record)
        if not evaluation["passed"]:
            raise RuntimeError(f"D3 live smoke evaluator failed: {slot.case_id}: {evaluation}")
    return results


def evaluate_unified_d3_run(result: Any, evaluator_case: dict[str, Any]) -> dict[str, Any]:
    """Grade a unified-runtime trace without entering its hidden contract into Agent context."""
    import json

    trace_path = Path(result.trace_path)
    events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line]
    terminal_status = result.status.value
    condition_id = evaluator_case["condition_id"]
    contract = evaluator_case["chapter1_contract"]
    event_types = [event["event_type"] for event in events]
    actions = [
        event["payload"].get("tool_name") for event in events
        if event["event_type"] == "action_started"
    ]
    observed_artifacts = {
        event["payload"].get("artifact_type") for event in events
        if event["event_type"] == "artifact_recorded"
    }
    terminal_events = [event["payload"] for event in events if event["event_type"] == "run_terminal"]
    task_id = evaluator_case["source_task_id"]
    revision_required = task_id == 11 and condition_id in {"B2_adaptive", "B3_checkpoint"}
    checkpoint_required = task_id == 11 and condition_id == "B3_checkpoint"
    required_artifacts = set(contract.get("required_artifact_types", contract.get("required_artifact_types_on_completion", [])))
    ndvi_action_count = actions.count("calculate_ndvi")
    task_specific_evidence = {
        2: {"read_raster_metadata", "calculate_ndvi", "plot_index_map"}.issubset(actions),
        3: not actions and bool(terminal_events) and "NDSI" in terminal_events[-1].get("reason", ""),
        10: "read_raster_metadata" in actions and bool(terminal_events) and "thermal" in terminal_events[-1].get("reason", "").lower(),
        11: "evaluation_fixture_injected" in event_types,
        13: "manager_clarification_requested" in event_types and not actions,
    }[task_id]
    revision_present = sum(event_type == "plan_version_recorded" for event_type in event_types) >= 2
    checkpoint_present = "checkpoint_recorded" in event_types
    graph_present = trace_path.with_name("process_graph.json").is_file()
    artifacts_complete = terminal_status != "completed" or required_artifacts.issubset(observed_artifacts)
    # The historical panel predates the public RunStatus contract.  Preserve
    # its wording in the evaluator while keeping ``needs_clarification`` as
    # the single API value exposed by the unified runtime.
    evaluator_terminal_status = {
        "needs_clarification": "needs_user_clarification",
    }.get(terminal_status, terminal_status)
    passed = (
        evaluator_terminal_status in contract["allowed_terminal_by_condition"][condition_id]
        and event_types[-1:] == ["run_completed"]
        and artifacts_complete
        and task_specific_evidence
        and (not revision_required or revision_present)
        and (not checkpoint_required or checkpoint_present)
        and (not checkpoint_required or ndvi_action_count == 1)
        and (not evaluator_case["condition"]["process_graph_from_run_facts"] or graph_present)
    )
    return {
        "passed": passed,
        "terminal_status": terminal_status,
        "evaluator_terminal_status": evaluator_terminal_status,
        "actions": actions,
        "observed_artifacts": sorted(item for item in observed_artifacts if item),
        "revision_present": revision_present,
        "checkpoint_present": checkpoint_present,
        "graph_present": graph_present,
        "ndvi_action_count": ndvi_action_count,
        "task_specific_evidence": task_specific_evidence,
    }
