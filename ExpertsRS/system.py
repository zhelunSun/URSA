"""Authoritative input-to-output ExpertsRS research runtime."""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .decisions import DecisionProvider, ScriptedDecisionProvider
from .models import (
    ArtifactRecord,
    RunRequest,
    RunResult,
    RunStatus,
    ValidationSummary,
)
from .tools.output_context import use_output_directory
from .tools.registry import get_tool_by_name, list_tools
from .workflow import (
    ArtifactSpec,
    ArtifactType,
    Checkpoint,
    LocalPermissionPolicy,
    PermissionOutcome,
    PermissionRequest,
    PlanVersion,
    ToolEffect,
    WorkflowTrace,
    build_process_graph,
)


@dataclass
class LocalToolExecutor:
    """Single deterministic tool boundary for every new runtime action."""

    inject_failures: dict[str, int] = field(default_factory=dict)
    injected_failure_ids: dict[str, str] = field(default_factory=dict)
    _calls: dict[str, int] = field(default_factory=dict, init=False)

    def execute(self, tool_name: str, arguments: dict[str, Any], output_dir: Path) -> dict[str, Any]:
        self._calls[tool_name] = self._calls.get(tool_name, 0) + 1
        if self.inject_failures.get(tool_name) == self._calls[tool_name]:
            failure = {
                "success": False,
                "message": "The tool failed before creating its requested output.",
                "data": None,
                "error_code": "transient_tool_failure",
            }
            if tool_name in self.injected_failure_ids:
                failure["fixture_id"] = self.injected_failure_ids[tool_name]
            return failure
        tool = get_tool_by_name(tool_name)
        if tool is None:
            return {
                "success": False,
                "message": f"No registered tool named {tool_name}.",
                "data": None,
                "error_code": "tool_not_registered",
            }
        with use_output_directory(output_dir):
            try:
                return tool(**arguments)
            except Exception as error:  # Defensive boundary around legacy tools.
                return {
                    "success": False,
                    "message": f"{tool_name} raised {type(error).__name__}: {error}",
                    "data": None,
                    "error_code": "tool_execution_exception",
                }


class ExpertsRSSystem:
    """One authoritative run/resume API for the research prototype."""

    def __init__(
        self,
        provider: DecisionProvider | None = None,
        executor: LocalToolExecutor | None = None,
        allowed_data_roots: list[str | Path] | None = None,
    ) -> None:
        self.provider = provider or ScriptedDecisionProvider()
        self.executor = executor or LocalToolExecutor()
        self.allowed_data_roots = tuple(Path(path).resolve() for path in (allowed_data_roots or []))

    async def run(self, request: RunRequest) -> RunResult:
        run_id = request.run_id or f"run_{uuid.uuid4().hex[:12]}"
        run_dir = self._new_run_dir(request.output_dir, run_id)
        state = self._initial_state(request, run_id, run_dir)
        return await self._drive(state)

    async def resume(self, run_id: str, answer: str, output_dir: str | Path) -> RunResult:
        run_dir = Path(output_dir).resolve() / run_id
        state_path = run_dir / "state.json"
        if not state_path.is_file():
            raise FileNotFoundError(f"No resumable ExpertsRS run at {run_dir}")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state["status"] != RunStatus.NEEDS_CLARIFICATION:
            raise ValueError(f"Run {run_id} is not waiting for clarification")
        state.setdefault("user_answers", []).append(answer.strip())
        state["status"] = "running"
        state["phase"] = "planning"
        self._append_trace(state, "user_clarification_received", {"answer": answer.strip()}, actor="User")
        return await self._drive(state)

    def _new_run_dir(self, output_dir: Path, run_id: str) -> Path:
        root = Path(output_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        run_dir = root / run_id
        if run_dir.exists():
            raise FileExistsError(f"Refusing to overwrite existing run directory: {run_dir}")
        run_dir.mkdir()
        return run_dir

    def _initial_state(self, request: RunRequest, run_id: str, run_dir: Path) -> dict[str, Any]:
        paths = [Path(path).resolve() for path in request.data_paths]
        allowed_roots = self.allowed_data_roots or tuple(path.parent for path in paths)
        trace = WorkflowTrace(run_id)
        return {
            "schema_version": 1,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "request": request.request,
            "data_paths": [str(path) for path in paths],
            "allowed_data_roots": [str(path) for path in allowed_roots],
            "budgets": request.budgets.model_dump(),
            "capabilities": request.capabilities.model_dump(),
            "status": "running",
            "phase": "initial",
            "user_answers": [],
            "observations": [],
            "artifacts": [],
            "trace": trace.to_dict(),
            "active_plan_id": None,
            "plan_count": 0,
            "checkpoint_id": None,
            "tool_calls": 0,
            "model_turns": 0,
            "messages": [],
        }

    async def _drive(self, state: dict[str, Any]) -> RunResult:
        trace = self._trace(state)
        try:
            await self._restore_provider_state(state)
            manager = await self._decide(state, "Manager")
            if manager["kind"] == "clarify":
                state["status"] = RunStatus.NEEDS_CLARIFICATION
                state["questions"] = [manager["question"]]
                self._append_trace(state, "manager_clarification_requested", {"question": manager["question"]}, actor="Manager")
                return self._finish(state, report=None)

            scientist = await self._decide(state, "Scientist")
            if scientist["kind"] == "stop":
                return self._stop(state, scientist["reason"], actor="Scientist")
            if scientist["kind"] != "plan":
                return self._stop(state, "Scientist did not produce a safe plan.", actor="Runtime")

            self._create_plan(state, scientist["operation"], scientist["next_action"])
            state["phase"] = "execution"
            while True:
                engineer = await self._decide(state, "Engineer")
                kind = engineer.get("kind")
                if kind == "handoff":
                    state["status"] = RunStatus.COMPLETED
                    return self._finish(state, report=self._report(state))
                if kind == "stop":
                    return self._stop(state, engineer.get("reason", "Engineer stopped safely."), actor="Engineer")
                if kind == "revise":
                    if not state["capabilities"]["allow_plan_revision"]:
                        return self._stop(state, "Tool failure requires a plan revision, but this condition forbids revision.", actor="Runtime")
                    self._revise_plan(state, engineer["next_action"])
                    state["phase"] = "recovery"
                    continue
                if kind != "action":
                    return self._stop(state, "Engineer produced an invalid decision.", actor="Runtime")
                observation = self._execute_action(state, engineer.get("tool"))
                state["observations"].append(observation)
                if not observation["success"]:
                    if observation.get("error_code") == "permission_denied":
                        return self._stop(state, observation["message"], actor="Runtime")
                    if not state["capabilities"]["allow_plan_revision"]:
                        return self._stop(state, observation["message"], actor="Runtime")
        except Exception as error:
            state["status"] = RunStatus.FAILED
            self._append_trace(state, "runtime_failed", {"error_type": type(error).__name__, "message": str(error)}, actor="Runtime")
            return self._finish(state, report=None)

    async def _decide(self, state: dict[str, Any], role: str) -> dict[str, Any]:
        budgets = state["budgets"]
        if state["model_turns"] >= budgets["max_model_turns"]:
            raise RuntimeError("model_turn_budget_exhausted")
        state["model_turns"] += 1
        view = {
            "request": state["request"],
            "phase": state["phase"],
            "user_answers": state["user_answers"],
            "available_tools": list_tools(),
            "observations": [self._redact_observation(item) for item in state["observations"]],
            "remaining_tool_budget": budgets["max_tool_calls"] - state["tool_calls"],
        }
        decision = await self.provider.decide(role, view)
        await self._persist_provider_state(state)
        self._append_trace(state, "agent_decision", {"role": role, "decision": decision}, actor=role)
        return decision

    async def _restore_provider_state(self, state: dict[str, Any]) -> None:
        """Restore only optional framework state; runtime state remains canonical."""
        saved = state.get("provider_state")
        loader = getattr(self.provider, "load_state", None)
        if saved is not None and callable(loader):
            await loader(saved)

    async def _persist_provider_state(self, state: dict[str, Any]) -> None:
        saver = getattr(self.provider, "save_state", None)
        if callable(saver):
            state["provider_state"] = await saver()

    def _create_plan(self, state: dict[str, Any], operation: str, next_action: str) -> None:
        plan = PlanVersion(
            f"{state['run_id']}:plan", 1, state["request"], operation, next_action, owner="Scientist"
        )
        state["active_plan_id"] = plan.object_id
        state["plan_count"] = 1
        self._trace(state).record_plan_version(plan)
        self._sync_trace(state)

    def _revise_plan(self, state: dict[str, Any], next_action: str) -> None:
        prior = state["active_plan_id"]
        trigger = self._trace(state).events[-1]["event_id"]
        version = state["plan_count"] + 1
        checkpoint_id = state["checkpoint_id"] if state["capabilities"]["allow_checkpoint_recovery"] else None
        plan = PlanVersion(
            f"{state['run_id']}:plan", version, state["request"], "recovery", next_action,
            owner="Scientist", branch_id="recovery", parent_version_id=prior,
            trigger_event_id=trigger, restart_from_checkpoint_id=checkpoint_id,
        )
        state["active_plan_id"] = plan.object_id
        state["plan_count"] = version
        self._trace(state).record_plan_version(plan)
        self._sync_trace(state)

    def _execute_action(self, state: dict[str, Any], tool_name: str | None) -> dict[str, Any]:
        if not tool_name or tool_name not in list_tools():
            return {"tool": tool_name or "unknown", "success": False, "message": "Tool is not registered.", "error_code": "tool_not_registered"}
        if state["tool_calls"] >= state["budgets"]["max_tool_calls"]:
            return {"tool": tool_name, "success": False, "message": "tool_call_budget_exhausted", "error_code": "budget_exhausted"}
        arguments = self._tool_arguments(state, tool_name)
        if arguments is None:
            return {"tool": tool_name, "success": False, "message": "Required artifact is unavailable.", "error_code": "missing_artifact"}
        action_id = f"{state['run_id']}:action:{state['tool_calls'] + 1:02d}"
        effect = self._effect(tool_name)
        resource = self._resource_for_permission(tool_name, arguments, state, action_id)
        policy = LocalPermissionPolicy(state["allowed_data_roots"], [Path(state["run_dir"]) / "artifacts"])
        permission = policy.evaluate(PermissionRequest(action_id, "Engineer", tool_name, effect, resource))
        trace = self._trace(state)
        trace.record_permission(PermissionRequest(action_id, "Engineer", tool_name, effect, resource), permission)
        if permission.outcome != PermissionOutcome.ALLOW:
            self._sync_trace(state)
            return {"tool": tool_name, "success": False, "message": permission.reason, "error_code": "permission_denied"}
        trace.record_action(action_id, "Engineer", tool_name, self._redact_arguments(arguments), state["active_plan_id"], permission.decision_id)
        state["tool_calls"] += 1
        result = self.executor.execute(tool_name, arguments, Path(state["run_dir"]) / "artifacts" / action_id.replace(":", "_"))
        if isinstance(result.get("fixture_id"), str):
            # Evaluation provenance is trace-only.  It is never placed in the
            # compact observation supplied to a decision provider.
            trace.record("evaluation_fixture_injected", {"tool_name": tool_name, "fixture_id": result["fixture_id"]}, actor="Evaluator")
        payload = self._compact_result(tool_name, result)
        trace.record_observation(f"{action_id}:observation", "Executor", action_id, bool(result.get("success")), payload)
        artifact = self._record_artifact(state, trace, action_id, tool_name, result)
        self._sync_trace(state)
        observation = {"tool": tool_name, "success": bool(result.get("success")), **payload}
        if artifact:
            observation["artifact_id"] = artifact.artifact_id
        if result.get("success") and tool_name == "calculate_ndvi" and state["capabilities"]["allow_checkpoint_recovery"]:
            checkpoint = Checkpoint(
                f"{state['run_id']}:checkpoint:ndvi", state["active_plan_id"], action_id,
                (artifact.artifact_id,) if artifact else (), reason="NDVI artifact validated",
            )
            trace.record_checkpoint(checkpoint)
            state["checkpoint_id"] = checkpoint.checkpoint_id
            self._sync_trace(state)
        return observation

    def _tool_arguments(self, state: dict[str, Any], tool_name: str) -> dict[str, Any] | None:
        source = state["data_paths"][0] if state["data_paths"] else None
        by_type = {item["artifact_type"]: item["uri"] for item in state["artifacts"]}
        if tool_name == "read_raster_metadata":
            return {"file_path": source} if source else None
        if tool_name == "calculate_ndvi":
            return {"file_path": source, "nir_band": "B8", "red_band": "B4"} if source else None
        if tool_name == "plot_index_map":
            return {"file_path": by_type.get("index_raster"), "index_name": "NDVI"} if by_type.get("index_raster") else None
        if tool_name == "apply_threshold":
            return {"file_path": by_type.get("index_raster"), "threshold_low": 0.3, "output_name": "greenspace"} if by_type.get("index_raster") else None
        if tool_name == "plot_thematic_map":
            return {"file_path": by_type.get("mask_raster"), "output_name": "greenspace"} if by_type.get("mask_raster") else None
        if tool_name == "calculate_area":
            return {"file_path": by_type.get("mask_raster"), "class_values": [1]} if by_type.get("mask_raster") else None
        return None

    @staticmethod
    def _effect(tool_name: str) -> ToolEffect:
        from .workflow.runtime import TOOL_EFFECTS

        return TOOL_EFFECTS[tool_name]

    @staticmethod
    def _resource_for_permission(tool_name: str, arguments: dict[str, Any], state: dict[str, Any], action_id: str) -> str:
        if tool_name in {"read_raster_metadata"}:
            return str(arguments["file_path"])
        if tool_name in {"calculate_ndvi", "plot_index_map", "apply_threshold", "plot_thematic_map"}:
            return str(Path(state["run_dir"]) / "artifacts" / action_id.replace(":", "_"))
        return str(Path(state["run_dir"]) / "artifacts")

    def _record_artifact(self, state: dict[str, Any], trace: WorkflowTrace, action_id: str, tool_name: str, result: dict[str, Any]) -> ArtifactRecord | None:
        if not result.get("success") or not isinstance(result.get("data"), dict):
            return None
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
        uri = result["data"].get("output_path")
        if uri is None:
            uri = str(Path(state["run_dir"]) / "metadata" / f"{action_id.replace(':', '_')}.json")
            metadata_path = Path(uri)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps(result["data"], indent=2, default=str), encoding="utf-8")
        record = ArtifactRecord(
            artifact_id=f"{action_id}:{artifact_type}", artifact_type=artifact_type, uri=Path(uri),
            producer_action_id=action_id, metadata={key: value for key, value in result["data"].items() if key != "output_path"},
        )
        state["artifacts"].append(record.model_dump(mode="json"))
        trace.record_artifact(record.artifact_id, "Executor", action_id, str(record.uri), True, artifact_type=artifact_type)
        return record

    def _stop(self, state: dict[str, Any], reason: str, actor: str) -> RunResult:
        state["status"] = RunStatus.CONTROLLED_STOP
        self._append_trace(state, "run_terminal", {"status": RunStatus.CONTROLLED_STOP, "reason": reason}, actor=actor)
        return self._finish(state, report=None)

    def _finish(self, state: dict[str, Any], report: str | None) -> RunResult:
        trace = self._trace(state)
        status = RunStatus(state["status"])
        trace.record_final_status(status, [item["artifact_id"] for item in state["artifacts"]])
        self._sync_trace(state)
        result = RunResult(
            run_id=state["run_id"], status=status, report=report, questions=state.get("questions", []),
            artifacts=[ArtifactRecord.model_validate(item) for item in state["artifacts"]],
            validation=ValidationSummary(
                valid=status in {RunStatus.COMPLETED, RunStatus.NEEDS_CLARIFICATION, RunStatus.CONTROLLED_STOP},
                messages=state["messages"], tool_calls=state["tool_calls"], model_turns=state["model_turns"], plan_versions=state["plan_count"],
            ),
            trace_path=Path(state["run_dir"]) / "trace.jsonl", checkpoint_id=state.get("checkpoint_id"),
        )
        self._write_files(state, result)
        return result

    def _write_files(self, state: dict[str, Any], result: RunResult) -> None:
        run_dir = Path(state["run_dir"])
        trace = self._trace(state)
        trace_path = run_dir / "trace.jsonl"
        trace_path.write_text("\n".join(json.dumps(event, ensure_ascii=False) for event in trace.events) + "\n", encoding="utf-8")
        state["trace"] = trace.to_dict()
        (run_dir / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        (run_dir / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        if result.report:
            (run_dir / "report.md").write_text(result.report + "\n", encoding="utf-8")
        if state["capabilities"].get("allow_plan_revision"):
            try:
                process_graph = build_process_graph(state["run_id"], trace.events).to_dict()
            except ValueError as error:
                process_graph = {"status": "unavailable", "reason": str(error)}
            (run_dir / "process_graph.json").write_text(json.dumps(process_graph, indent=2), encoding="utf-8")

    def _report(self, state: dict[str, Any]) -> str:
        artifact_names = ", ".join(item["artifact_type"] for item in state["artifacts"])
        return f"分析完成：{state['request']}。已生成并验证的制品：{artifact_names}。"

    @staticmethod
    def _redact_observation(observation: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in observation.items() if key in {"tool", "success", "message", "error_code", "artifact_id"}}

    @staticmethod
    def _redact_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
        return {key: ("<local-path>" if "path" in key or "file" in key else value) for key, value in arguments.items()}

    @staticmethod
    def _compact_result(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
        data = result.get("data") if isinstance(result.get("data"), dict) else {}
        return {
            "tool": tool_name,
            "message": str(result.get("message", "")),
            "error_code": result.get("error_code"),
            "artifact_type": {
                "read_raster_metadata": "metadata", "calculate_ndvi": "index_raster", "apply_threshold": "mask_raster",
                "plot_index_map": "map", "plot_thematic_map": "map", "calculate_area": "area_statistics",
            }.get(tool_name),
            "valid_pixels": data.get("valid_pixels"),
        }

    def _append_trace(self, state: dict[str, Any], event_type: str, payload: dict[str, Any], actor: str = "Runtime") -> None:
        self._trace(state).record(event_type, payload, actor=actor)
        self._sync_trace(state)

    @staticmethod
    def _trace(state: dict[str, Any]) -> WorkflowTrace:
        return WorkflowTrace(state["run_id"], events=state["trace"]["events"])

    @staticmethod
    def _sync_trace(state: dict[str, Any]) -> None:
        # Events are mutated in place, but assigning makes the invariant explicit.
        state["trace"] = {"run_id": state["run_id"], "events": state["trace"]["events"]}


def run_sync(system: ExpertsRSSystem, request: RunRequest) -> RunResult:
    """Small convenience wrapper for non-async CLI callers."""
    return asyncio.run(system.run(request))
