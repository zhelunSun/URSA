"""Authoritative input-to-output ExpertsRS research runtime."""

from __future__ import annotations

import asyncio
import json
import shutil
import hashlib
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .decisions import DecisionProvider, ScriptedDecisionProvider, parse_role_decision
from .models import (
    ArtifactRecord,
    ExecutionMode,
    RunRequest,
    RunResult,
    RunStatus,
    ToolBinding,
    ValidationSummary,
)
from .provider import ProviderFailure, create_autogen_live_provider, redacted_provider_base_url
from .tools.output_context import use_output_directory
from .tools.registry import get_tool_by_name
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
    build_operator_catalog,
    build_process_graph,
    classify_graph_diff,
    derive_delivery_obligations,
    hydrate_task,
    hydrate_workflow,
    validate_plan_obligations,
    validate_workflow,
)


class BudgetExhausted(RuntimeError):
    """A normal, auditable terminal condition rather than an unclassified crash."""


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
        tool = get_tool_by_name(tool_name, "classification-v1" if tool_name in {"summarize_classification", "plot_classification_map"} else "legacy")
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
        self.provider = provider
        self._provider_is_injected = provider is not None
        self.executor = executor or LocalToolExecutor()
        self.allowed_data_roots = tuple(Path(path).resolve() for path in (allowed_data_roots or []))

    # This deliberately exposes a safe subset of the registered legacy tool
    # layer.  Each binding has runtime argument resolution and permission
    # enforcement; registered tools without both remain model-invisible.
    TOOL_BINDINGS: dict[str, ToolBinding] = {
        "read_raster_metadata": ToolBinding(tool_name="read_raster_metadata"),
        "calculate_ndvi": ToolBinding(tool_name="calculate_ndvi"),
        "plot_index_map": ToolBinding(tool_name="plot_index_map", required_artifact_types=("index_raster",)),
        "apply_threshold": ToolBinding(
            tool_name="apply_threshold", required_artifact_types=("index_raster",), safe_parameters={"threshold_low": 0.3},
        ),
        "plot_thematic_map": ToolBinding(tool_name="plot_thematic_map", required_artifact_types=("mask_raster",)),
        "calculate_area": ToolBinding(tool_name="calculate_area", required_artifact_types=("mask_raster",)),
    }

    @staticmethod
    def _file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _request_obligations(request):
        if request.domain_profile == "classification-v1":
            from .domain import obligations
            return obligations()
        return [item.to_dict() for item in derive_delivery_obligations(request.request)]

    def _bindings(self, state):
        if state.get("domain_profile") == "classification-v1":
            from .domain import bindings
            return bindings(state["product_year"])
        return self.TOOL_BINDINGS

    @staticmethod
    def _input_paths(state):
        if state.get("input_resources"):
            return {key: value["path"] for key, value in state["input_resources"].items()}
        return {"input_raster": state["data_paths"][0]} if state["data_paths"] else {}

    async def run(self, request: RunRequest) -> RunResult:
        if not self._provider_is_injected:
            self.provider = self._provider_for_request(request)
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
        state["started_at_unix"] = time.time()
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
        resources = {key: value.model_dump(mode="json") for key, value in request.input_resources.items()}
        for resource in resources.values():
            resource["path"] = str(Path(resource["path"]).resolve())
            paths.append(Path(resource["path"]))
        allowed_roots = self.allowed_data_roots or tuple(path.parent for path in paths)
        for resource in resources.values():
            path = Path(resource["path"])
            if not path.is_file() or not LocalPermissionPolicy._is_within(str(path), tuple(Path(p).resolve() for p in allowed_roots)):
                raise ValueError("Input resource is missing or outside allowed data roots")
            actual = self._file_hash(path)
            if resource.get("sha256") and resource["sha256"].lower() != actual:
                raise ValueError("Input resource hash does not match declared identity")
            resource["sha256"] = actual
            if resource["artifact_type"] == "aoi":
                resource["components"] = {}
                suffixes = (".shp", ".shx", ".dbf", ".prj")
                if path.with_suffix(".cpg").exists():
                    suffixes += (".cpg",)
                for suffix in suffixes:
                    component = path.with_suffix(suffix).resolve()
                    if not component.is_file() or not LocalPermissionPolicy._is_within(str(component), tuple(Path(p).resolve() for p in allowed_roots)):
                        raise ValueError("AOI component missing or outside allowed data roots")
                    resource["components"][suffix] = self._file_hash(component)
        trace = WorkflowTrace(run_id)
        return {
            "schema_version": 2 if resources else 1,
            "domain_profile": request.domain_profile,
            "product_year": request.product_year,
            "input_resources": resources,
            "run_id": run_id,
            "run_dir": str(run_dir),
            "request": request.request,
            "data_paths": [str(path) for path in paths],
            "allowed_data_roots": [str(path) for path in allowed_roots],
            "budgets": request.budgets.model_dump(),
            "capabilities": request.capabilities.model_dump(),
            "execution_mode": request.execution_mode.value,
            "provider": self._provider_manifest(request),
            "status": "running",
            "phase": "initial",
            "user_answers": [],
            "observations": [],
            "artifacts": [],
            "trace": trace.to_dict(),
            "active_plan_id": None,
            "current_plan": None,
            "planned_graph": None,
            "delivery_obligations": self._request_obligations(request),
            "plan_history": [],
            "node_states": {},
            "workflow_artifact_records": {},
            "last_failed_node_id": None,
            "plan_count": 0,
            "checkpoint_id": None,
            "tool_calls": 0,
            "model_turns": 0,
            "role_tool_calls": {"Scientist": 0, "Engineer": 0},
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "started_at_unix": time.time(),
            "messages": [],
        }

    async def _drive(self, state: dict[str, Any]) -> RunResult:
        elapsed = max(0.0, time.time() - float(state.get("started_at_unix", time.time())))
        remaining = state["budgets"]["max_wall_time_seconds"] - elapsed
        if remaining <= 0:
            return self._stop(state, "wall_time_budget_exhausted", actor="Runtime")
        try:
            return await asyncio.wait_for(self._drive_within_wall_budget(state), timeout=remaining)
        except TimeoutError:
            return self._stop(state, "wall_time_budget_exhausted", actor="Runtime")

    async def _drive_within_wall_budget(self, state: dict[str, Any]) -> RunResult:
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
            try:
                self._accept_plan(state, scientist)
            except (KeyError, ValueError) as error:
                self._append_trace(state, "planned_workflow_rejected", {"reason": str(error)}, actor="Runtime")
                return self._stop(state, "Scientist workflow failed runtime validation.", actor="Runtime")
            state["phase"] = "execution"
            while True:
                if state["phase"] == "revision_required":
                    if not state["capabilities"]["allow_plan_revision"]:
                        return self._stop(state, "Tool failure requires a plan revision, but this condition forbids revision.", actor="Runtime")
                    revision = await self._decide(state, "Scientist")
                    if revision.get("kind") != "revise":
                        return self._stop(
                            state, "A recoverable tool failure requires a Scientist plan revision before another action.",
                            actor="Runtime",
                        )
                    try:
                        self._accept_plan(state, revision)
                    except (KeyError, ValueError) as error:
                        self._append_trace(state, "planned_workflow_rejected", {"reason": str(error)}, actor="Runtime")
                        return self._stop(state, "Scientist workflow revision failed runtime validation.", actor="Runtime")
                    state["phase"] = "execution"
                    continue
                engineer = await self._decide(state, "Engineer")
                kind = engineer.get("kind")
                if kind == "handoff":
                    if not self._plan_is_complete(state):
                        return self._stop(state, "Engineer attempted report handoff before the planned workflow completed.", actor="Runtime")
                    return await self._generate_manager_report(state)
                if kind == "stop":
                    return self._stop(state, engineer.get("reason", "Engineer stopped safely."), actor="Engineer")
                if kind != "action":
                    return self._stop(state, "Engineer produced an invalid decision.", actor="Runtime")
                observation = self._execute_action(state, engineer)
                state["observations"].append(observation)
                if not observation["success"]:
                    if observation.get("error_code") in {"permission_denied", "tool_not_registered", "unsafe_action_contract", "missing_artifact", "budget_exhausted"}:
                        return self._stop(state, observation["message"], actor="Runtime")
                    if not state["capabilities"]["allow_plan_revision"]:
                        return self._stop(state, observation["message"], actor="Runtime")
                    state["phase"] = "revision_required"
        except BudgetExhausted as error:
            return self._stop(state, str(error), actor="Runtime")
        except ProviderFailure as error:
            state["status"] = RunStatus.FAILED
            self._append_trace(
                state, "provider_failed", {"code": error.code, "message": str(error)}, actor="Runtime"
            )
            return self._finish(state, report=None)
        except Exception as error:
            state["status"] = RunStatus.FAILED
            self._append_trace(state, "runtime_failed", {"error_type": type(error).__name__, "message": str(error)}, actor="Runtime")
            return self._finish(state, report=None)

    async def _decide(self, state: dict[str, Any], role: str) -> dict[str, Any]:
        budgets = state["budgets"]
        if state["model_turns"] >= budgets["max_model_turns"]:
            raise BudgetExhausted("model_turn_budget_exhausted")
        state["model_turns"] += 1
        view = {
            "request": state["request"],
            "phase": state["phase"],
            "user_answers": state["user_answers"],
            "input_data_available": bool(state["data_paths"]),
            "input_data_count": len(state["data_paths"]),
            "available_tools": [binding.model_dump(mode="json") for binding in self._bindings(state).values()],
            "observations": [self._redact_observation(item) for item in state["observations"]],
            "artifact_manifest": [self._model_artifact_record(item) for item in state["artifacts"]],
            "current_plan": state.get("current_plan"),
            "active_plan_id": state.get("active_plan_id"),
            "eligible_node_ids": self._eligible_node_ids(state),
            "delivery_obligations": state.get("delivery_obligations", []),
            "report_deliverables": self._report_deliverables(state),
            "remaining_tool_budget": budgets["max_tool_calls"] - state["tool_calls"],
        }
        if state.get("domain_profile") == "classification-v1":
            view.update({"domain_profile": state["domain_profile"], "product_year": state["product_year"],
                         "input_resources": [{"artifact_id": key, "artifact_type": item["artifact_type"]}
                                             for key, item in state["input_resources"].items()]})
        raw_decision = await self.provider.decide(role, view)
        self._record_provider_usage(state, raw_decision)
        try:
            decision = parse_role_decision(role, raw_decision)
        except ValueError as error:
            self._append_trace(
                state, "invalid_model_decision", {"role": role, "reason": str(error)}, actor="Runtime"
            )
            raise RuntimeError(f"invalid_model_decision:{role}") from error
        await self._persist_provider_state(state)
        self._append_trace(state, "agent_decision", {"role": role, "decision": decision}, actor=role)
        return decision

    def _record_provider_usage(self, state: dict[str, Any], raw_decision: dict[str, Any]) -> None:
        """Account for provider-reported tokens before the next model request."""
        if not isinstance(raw_decision, dict):
            if state["execution_mode"] == ExecutionMode.AUTOGEN_LIVE.value:
                raise ProviderFailure("provider_response_invalid", "The provider response is not a decision object.")
            return
        usage = raw_decision.pop("_provider_usage", None)
        if state["execution_mode"] != ExecutionMode.AUTOGEN_LIVE.value:
            return
        if not isinstance(usage, dict) or any(
            not isinstance(usage.get(key), int) or usage[key] < 0
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        ):
            raise ProviderFailure("provider_usage_missing", "The provider response omitted valid token usage metadata.")
        if usage["total_tokens"] != usage["prompt_tokens"] + usage["completion_tokens"]:
            raise ProviderFailure("provider_usage_invalid", "The provider response reported inconsistent token usage.")
        totals = state.setdefault("token_usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
        for key in totals:
            totals[key] += usage[key]
        state["provider"]["actual_usage"] = dict(totals)
        self._append_trace(state, "provider_usage_recorded", dict(totals), actor="Runtime")
        if totals["total_tokens"] > state["budgets"]["max_total_tokens_recorded"]:
            raise BudgetExhausted("total_token_budget_exhausted")

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

    def _accept_plan(self, state: dict[str, Any], decision: dict[str, Any]) -> None:
        """Validate, hydrate and version a Scientist plan before execution."""
        catalog = build_operator_catalog(state.get("domain_profile", "legacy"))
        task_payload = decision["task"]
        graph_payload = decision["workflow"]
        input_paths = self._input_paths(state)
        for item in graph_payload["input_artifacts"]:
            actual = state.get("input_resources", {}).get(item["artifact_id"])
            if actual and actual["artifact_type"] != item["artifact_type"]:
                raise ValueError("Plan input type disagrees with caller-owned resource binding")
        task = hydrate_task(task_payload)
        graph = hydrate_workflow(graph_payload, catalog, input_paths)
        report = validate_workflow(task, graph, catalog)
        validate_plan_obligations(state.get("delivery_obligations", []), task_payload, graph_payload)
        unsafe_nodes = [
            node.node_id for node in graph.nodes
            if catalog.get(node.operator_id) is None
            or catalog[node.operator_id].tool_name not in self._bindings(state)
            or node.config != self._bindings(state)[catalog[node.operator_id].tool_name].safe_parameters
        ]
        if not report.valid or unsafe_nodes:
            details = report.to_dict()
            details["unsafe_node_ids"] = unsafe_nodes
            self._append_trace(state, "planned_workflow_rejected", details, actor="Runtime")
            raise ValueError("Scientist workflow failed runtime validation")

        is_revision = decision["kind"] == "revise"
        previous_graph = state.get("planned_graph")
        prior = state.get("active_plan_id")
        version = state["plan_count"] + 1
        trigger = None
        affected: list[str] = []
        if is_revision:
            if decision["base_plan_id"] != prior:
                raise ValueError("Scientist revision does not name the active plan as its base")
            if task_payload != state.get("planned_graph", {}).get("task"):
                raise ValueError("Scientist revision may not rewrite the accepted task specification")
            trigger = self._trace(state).events[-1]["event_id"]
            affected = list(decision["affected_node_ids"])
            self._validate_local_patch(state, graph, affected)
        elif prior is not None:
            raise ValueError("Only the initial Scientist decision may create plan version 1")

        plan = PlanVersion(
            f"{state['run_id']}:plan", version, task.goal,
            "recovery" if is_revision else "planned", "execute_eligible_node", owner="Scientist",
            branch_id="recovery" if is_revision else "main", parent_version_id=prior if is_revision else None,
            trigger_event_id=trigger, restart_from_checkpoint_id=(state["checkpoint_id"] if is_revision and state["capabilities"]["allow_checkpoint_recovery"] else None),
            workflow_id=graph.workflow_id, affected_node_ids=tuple(affected),
        )
        state["active_plan_id"] = plan.object_id
        state["plan_count"] = version
        state["current_plan"] = {
            "plan_version_id": plan.object_id, "task_id": task.task_id, "workflow_id": graph.workflow_id,
            "expected_outputs": [item.value for item in task.expected_outputs],
            "required_metrics": list(task.required_metrics),
        }
        state["planned_graph"] = {"task": task_payload, "workflow": graph_payload}
        change_class = classify_graph_diff(previous_graph, state["planned_graph"], is_revision=is_revision)
        if not is_revision:
            state["node_states"] = {node.node_id: "pending" for node in graph.nodes}
            state["workflow_artifact_records"] = {}
        else:
            for node_id in affected:
                state["node_states"][node_id] = "pending"
                node = graph.node_by_id(node_id)
                if node:
                    state["workflow_artifact_records"].pop(node.output_artifact_id, None)
        state["last_failed_node_id"] = None
        trace = self._trace(state)
        trace.record_plan_version(plan)
        trace.record("planned_workflow_recorded", {
            "task": task_payload, "workflow": graph_payload, "node_states": dict(state["node_states"]),
        }, actor="Scientist", object_id=f"{plan.object_id}:workflow")
        state["plan_history"].append({
            "plan_version_id": plan.object_id, "task": task_payload, "workflow": graph_payload,
            "affected_node_ids": affected, "revision_change_class": change_class,
        })
        self._append_trace(state, "plan_graph_diff_classified", {
            "plan_version_id": plan.object_id, "classification": change_class,
            "parent_plan_id": prior,
        }, actor="Runtime")
        self._sync_trace(state)

    def _validate_local_patch(self, state: dict[str, Any], graph: Any, affected: list[str]) -> None:
        if len(set(affected)) != len(affected) or not affected:
            raise ValueError("Scientist revision must name distinct affected nodes")
        previous = self._hydrated_graph(state)
        failed = state.get("last_failed_node_id")
        if not failed or failed not in affected:
            raise ValueError("Scientist revision must include the observed failed node")
        allowed = {failed, *previous.descendant_ids(failed)}
        if not set(affected).issubset(allowed):
            raise ValueError("Scientist revision expands beyond the failed node's downstream subgraph")
        previous_nodes = {node.node_id: node.to_dict() for node in previous.nodes}
        revised_nodes = {node.node_id: node.to_dict() for node in graph.nodes}
        if set(previous_nodes) != set(revised_nodes):
            raise ValueError("Local revisions may not add or remove workflow nodes in v0.5.2")
        for node_id, prior_node in previous_nodes.items():
            if node_id not in affected and revised_nodes[node_id] != prior_node:
                raise ValueError("Scientist revision rewrote an unaffected workflow node")

    def _hydrated_graph(self, state: dict[str, Any]) -> Any:
        if not state.get("planned_graph"):
            raise ValueError("No active planned workflow")
        catalog = build_operator_catalog(state.get("domain_profile", "legacy"))
        paths = self._input_paths(state)
        return hydrate_workflow(state["planned_graph"]["workflow"], catalog, paths)

    def _eligible_node_ids(self, state: dict[str, Any]) -> list[str]:
        if not state.get("planned_graph"):
            return []
        return self._hydrated_graph(state).eligible_node_ids(state.get("node_states", {}))

    def _plan_is_complete(self, state: dict[str, Any]) -> bool:
        graph = self._hydrated_graph(state)
        return all(state["node_states"].get(node.node_id) == "succeeded" for node in graph.nodes)

    def _report_deliverables(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        """Build a small, path-free factual view for the Manager report role."""
        if state.get("domain_profile") == "classification-v1":
            from .domain import deliverables
            return deliverables(state)
        artifacts = state.get("artifacts", [])
        by_type: dict[str, list[dict[str, Any]]] = {}
        by_node: dict[str, list[dict[str, Any]]] = {}
        for artifact in artifacts:
            by_type.setdefault(artifact["artifact_type"], []).append(artifact)
            by_node.setdefault(artifact.get("producer_plan_node_id") or "", []).append(artifact)
        required = {item["obligation_id"] for item in state.get("delivery_obligations", [])}
        deliverables: list[dict[str, Any]] = []
        if "ndvi_map" in required:
            maps = by_node.get("index_map", [])
            if maps:
                deliverables.append({
                    "deliverable_id": "ndvi_map", "status": "delivered", "value": "NDVI map",
                    "unit": None, "scope": "supplied raster extent", "artifact_refs": [maps[-1]["artifact_id"]],
                })
        if "vegetation_coverage_map" in required:
            maps = by_node.get("thematic_map", [])
            if maps:
                deliverables.append({
                    "deliverable_id": "vegetation_coverage_map", "status": "delivered",
                    "value": "vegetation coverage thematic map", "unit": None,
                    "scope": "supplied raster extent", "artifact_refs": [maps[-1]["artifact_id"]],
                })
        if "green_cover_rate" in required:
            masks = by_node.get("threshold", [])
            areas = by_node.get("area_statistics", [])
            if masks and areas:
                metadata = masks[-1].get("metadata", {})
                percentage = (metadata.get("percentages") or {}).get("class_1")
                refs = [masks[-1]["artifact_id"], areas[-1]["artifact_id"]]
                if isinstance(percentage, (int, float)):
                    deliverables.append({
                        "deliverable_id": "green_cover_rate", "status": "delivered", "value": percentage,
                        "unit": "%", "scope": "有效影像像元范围内；未验证为行政区面积分母",
                        "artifact_refs": refs,
                    })
                else:
                    deliverables.append({
                        "deliverable_id": "green_cover_rate", "status": "partial", "value": None,
                        "unit": "%", "scope": "有效影像像元范围内；比例证据不可用",
                        "artifact_refs": refs,
                    })
        return deliverables

    def _execute_action(self, state: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        node_id = decision["node_id"]
        graph = self._hydrated_graph(state)
        node = graph.node_by_id(node_id)
        if node is None:
            return {"tool": None, "plan_node_id": node_id, "success": False, "message": "Engineer selected an unknown planned node.", "error_code": "unknown_plan_node"}
        if node_id not in self._eligible_node_ids(state):
            return {"tool": None, "plan_node_id": node_id, "success": False, "message": "Engineer selected a non-eligible planned node.", "error_code": "node_not_eligible"}
        catalog = build_operator_catalog(state.get("domain_profile", "legacy"))
        tool_name = catalog[node.operator_id].tool_name
        binding = self._bindings(state).get(tool_name)
        if binding is None:
            return {"tool": tool_name, "success": False, "message": "Tool is not in the runtime-visible catalog.", "error_code": "tool_not_registered"}
        if state["tool_calls"] >= state["budgets"]["max_tool_calls"]:
            return {"tool": tool_name, "success": False, "message": "tool_call_budget_exhausted", "error_code": "budget_exhausted"}
        role_calls = state.setdefault("role_tool_calls", {"Scientist": 0, "Engineer": 0})
        if role_calls["Engineer"] >= state["budgets"]["max_tool_calls_engineer"]:
            return {"tool": tool_name, "success": False, "message": "engineer_tool_budget_exhausted", "error_code": "budget_exhausted"}
        if state.get("domain_profile") == "classification-v1":
            arguments, contract_error = self._domain_arguments(state, node, catalog[node.operator_id])
        else:
            planned_refs = [
                state["workflow_artifact_records"].get(artifact_id)
                for artifact_id in node.inputs.values() if artifact_id != "input_raster"
            ]
            if any(reference is None for reference in planned_refs):
                return {"tool": tool_name, "plan_node_id": node_id, "success": False, "message": "Planned input artifact is unavailable.", "error_code": "missing_artifact"}
            arguments, contract_error = self._tool_arguments(state, binding, [item for item in planned_refs if item], node.config)
        if contract_error:
            return {"tool": tool_name, "success": False, "message": contract_error, "error_code": "unsafe_action_contract"}
        if arguments is None:
            return {"tool": tool_name, "success": False, "message": "Required artifact is unavailable.", "error_code": "missing_artifact"}
        action_id = f"{state['run_id']}:action:{state['tool_calls'] + 1:02d}"
        effect = self._effect(tool_name)
        resource = self._resource_for_permission(tool_name, arguments, state, action_id)
        from .workflow.runtime import TOOL_EFFECTS
        policy = LocalPermissionPolicy(state["allowed_data_roots"], [Path(state["run_dir"]) / "artifacts"],
            tool_effects={**TOOL_EFFECTS, "summarize_classification": ToolEffect.WRITE_LOCAL_ARTIFACT,
                          "plot_classification_map": ToolEffect.WRITE_LOCAL_ARTIFACT})
        permission = policy.evaluate(PermissionRequest(action_id, "Engineer", tool_name, effect, resource))
        trace = self._trace(state)
        trace.record_permission(PermissionRequest(action_id, "Engineer", tool_name, effect, resource), permission)
        if permission.outcome != PermissionOutcome.ALLOW:
            self._sync_trace(state)
            return {"tool": tool_name, "success": False, "message": permission.reason, "error_code": "permission_denied"}
        trace.record_action(action_id, "Engineer", tool_name, self._redact_arguments(arguments), state["active_plan_id"], permission.decision_id, plan_node_id=node_id)
        state["tool_calls"] += 1
        role_calls["Engineer"] += 1
        result = self.executor.execute(tool_name, arguments, Path(state["run_dir"]) / "artifacts" / action_id.replace(":", "_"))
        if isinstance(result.get("fixture_id"), str):
            # Evaluation provenance is trace-only.  It is never placed in the
            # compact observation supplied to a decision provider.
            trace.record("evaluation_fixture_injected", {"tool_name": tool_name, "fixture_id": result["fixture_id"]}, actor="Evaluator")
        try:
            artifact = self._record_artifact(state, trace, action_id, tool_name, result, plan_node_id=node_id)
        except (OSError, ValueError, TypeError) as error:
            trace.record("artifact_rejected", {"tool_name": tool_name, "returned_success": bool(result.get("success")),
                         "reason": type(error).__name__}, actor="Runtime")
            result = {"success": False, "data": None, "message": "Tool output failed artifact existence, scope or integrity checks.",
                      "error_code": "invalid_artifact"}
            artifact = None
        payload = {"plan_node_id": node_id, **self._compact_result(tool_name, result)}
        trace.record_observation(f"{action_id}:observation", "Executor", action_id, bool(result.get("success")), payload)
        self._sync_trace(state)
        observation = {"tool": tool_name, "success": bool(result.get("success")), **payload}
        if artifact:
            observation["artifact_id"] = artifact.artifact_id
            state["workflow_artifact_records"][node.output_artifact_id] = artifact.artifact_id
        state["node_states"][node_id] = "succeeded" if result.get("success") else "failed"
        if not result.get("success"):
            state["last_failed_node_id"] = node_id
        if result.get("success") and tool_name == "calculate_ndvi" and state["capabilities"]["allow_checkpoint_recovery"]:
            checkpoint = Checkpoint(
                f"{state['run_id']}:checkpoint:ndvi", state["active_plan_id"], action_id,
                (artifact.artifact_id,) if artifact else (), reason="NDVI artifact validated", source_plan_node_id=node_id,
            )
            trace.record_checkpoint(checkpoint)
            state["checkpoint_id"] = checkpoint.checkpoint_id
            self._sync_trace(state)
        return observation

    def _domain_arguments(self, state, node, operator):
        """Resolve exact named graph inputs; validate source and upstream identities."""
        if set(node.inputs) != set(operator.input_types):
            return None, "Domain tool inputs disagree with declared contract"
        arguments = dict(node.config)
        records = {a["artifact_id"]: a for a in state["artifacts"]}
        try:
            for parameter, logical_id in node.inputs.items():
                source = state["input_resources"].get(logical_id)
                if source:
                    path = Path(source["path"])
                    if not LocalPermissionPolicy._is_within(str(path), tuple(Path(p) for p in state["allowed_data_roots"])):
                        return None, "Domain input is outside allowed read roots"
                    if self._file_hash(path) != source["sha256"]:
                        return None, "Domain input changed since request admission"
                    for suffix, expected in source.get("components", {}).items():
                        component = path.with_suffix(suffix).resolve()
                        if not LocalPermissionPolicy._is_within(str(component), tuple(Path(p) for p in state["allowed_data_roots"])) or self._file_hash(component) != expected:
                            return None, "AOI component changed since request admission"
                else:
                    record = records.get(state["workflow_artifact_records"].get(logical_id))
                    if not record or record["artifact_type"] not in [a.value for a in operator.input_types[parameter]]:
                        return None, "Domain upstream artifact is unavailable or incompatible"
                    path = Path(record["uri"]).resolve()
                    if not path.is_relative_to(Path(state["run_dir"]).resolve()) or self._file_hash(path) != record["metadata"].get("artifact_sha256"):
                        return None, "Domain upstream artifact changed or leaves the run"
                arguments[parameter] = str(path)
        except OSError:
            return None, "Domain input or upstream artifact is missing"
        return arguments, None

    def _tool_arguments(
        self,
        state: dict[str, Any],
        binding: ToolBinding,
        artifact_refs: list[str],
        parameters: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        tool_name = binding.tool_name
        artifacts_by_id = {item["artifact_id"]: item for item in state["artifacts"]}
        referenced_artifacts = [artifacts_by_id.get(artifact_id) for artifact_id in artifact_refs]
        if (
            len(artifact_refs) != len(binding.required_artifact_types)
            or any(item is None for item in referenced_artifacts)
            or [item["artifact_type"] for item in referenced_artifacts] != list(binding.required_artifact_types)
        ):
            return None, "Action artifact references do not match the approved tool binding."
        if parameters != binding.safe_parameters:
            return None, "Action parameters do not match the approved tool binding."
        source = state["data_paths"][0] if state["data_paths"] else None
        by_type = {item["artifact_type"]: item["uri"] for item in referenced_artifacts if item is not None}
        if tool_name == "read_raster_metadata":
            return ({"file_path": source} if source else None), None
        if tool_name == "calculate_ndvi":
            return ({"file_path": source, "nir_band": "B8", "red_band": "B4"} if source else None), None
        if tool_name == "plot_index_map":
            return ({"file_path": by_type.get("index_raster"), "index_name": "NDVI"} if by_type.get("index_raster") else None), None
        if tool_name == "apply_threshold":
            return ({"file_path": by_type.get("index_raster"), "threshold_low": 0.3, "output_name": "greenspace"} if by_type.get("index_raster") else None), None
        if tool_name == "plot_thematic_map":
            return ({"file_path": by_type.get("mask_raster"), "output_name": "greenspace"} if by_type.get("mask_raster") else None), None
        if tool_name == "calculate_area":
            return ({"file_path": by_type.get("mask_raster"), "class_values": [1]} if by_type.get("mask_raster") else None), None
        return None, "No runtime argument resolver exists for this tool."

    @staticmethod
    def _effect(tool_name: str) -> ToolEffect:
        from .workflow.runtime import TOOL_EFFECTS

        if tool_name in {"summarize_classification", "plot_classification_map"}:
            return ToolEffect.WRITE_LOCAL_ARTIFACT
        return TOOL_EFFECTS[tool_name]

    @staticmethod
    def _resource_for_permission(tool_name: str, arguments: dict[str, Any], state: dict[str, Any], action_id: str) -> str:
        if tool_name in {"read_raster_metadata"}:
            return str(arguments["file_path"])
        if tool_name in {"calculate_ndvi", "plot_index_map", "apply_threshold", "plot_thematic_map", "summarize_classification", "plot_classification_map"}:
            return str(Path(state["run_dir"]) / "artifacts" / action_id.replace(":", "_"))
        return str(Path(state["run_dir"]) / "artifacts")

    def _record_artifact(
        self,
        state: dict[str, Any],
        trace: WorkflowTrace,
        action_id: str,
        tool_name: str,
        result: dict[str, Any],
        *,
        plan_node_id: str | None = None,
    ) -> ArtifactRecord | None:
        if not result.get("success") or not isinstance(result.get("data"), dict):
            if result.get("success"):
                raise ValueError("Successful tool must supply an artifact payload")
            return None
        artifact_type = {
            "read_raster_metadata": "metadata",
            "calculate_ndvi": "index_raster",
            "apply_threshold": "mask_raster",
            "plot_index_map": "map",
            "plot_thematic_map": "map",
            "calculate_area": "area_statistics",
            "summarize_classification": "composition_table",
            "plot_classification_map": "map",
        }.get(tool_name)
        if artifact_type is None:
            raise ValueError("Successful tool has no registered artifact type")
        uri = result["data"].get("output_path")
        if uri is None:
            if artifact_type not in {"metadata", "area_statistics"}:
                raise ValueError("File-producing tool returned no output path")
            uri = str(Path(state["run_dir"]) / "metadata" / f"{action_id.replace(':', '_')}.json")
            metadata_path = Path(uri)
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps(result["data"], indent=2, default=str), encoding="utf-8")
        path = Path(uri).resolve()
        expected_root = (Path(state["run_dir"]) / "artifacts" / action_id.replace(":", "_")).resolve()
        metadata_root = (Path(state["run_dir"]) / "metadata").resolve()
        if not path.is_file() or not (path.is_relative_to(expected_root) or (artifact_type in {"metadata", "area_statistics"} and path.is_relative_to(metadata_root))):
            raise ValueError("Artifact does not exist in this action's permitted output directory")
        if path.stat().st_size == 0:
            raise ValueError("Artifact is empty")
        if artifact_type == "composition_table":
            persisted = json.loads(path.read_text(encoding="utf-8"))
            if persisted.get("artifact_type") != "classification_summary" or persisted.get("data") != result["data"]:
                raise ValueError("Composition metadata disagrees with the persisted table")
        for secondary in result["data"].get("secondary_outputs", []):
            secondary_path = Path(secondary["path"]).resolve()
            if not secondary_path.is_relative_to(expected_root) or not secondary_path.is_file() or secondary_path.stat().st_size == 0:
                raise ValueError("Secondary artifact is missing or outside action directory")
            secondary["sha256"] = self._file_hash(secondary_path)
        record = ArtifactRecord(
            artifact_id=f"{action_id}:{artifact_type}", artifact_type=artifact_type, uri=Path(uri),
            producer_action_id=action_id, producer_plan_node_id=plan_node_id,
            metadata={**{key: value for key, value in result["data"].items() if key != "output_path"},
                      "artifact_sha256": self._file_hash(path)},
        )
        state["artifacts"].append(record.model_dump(mode="json"))
        trace.record_artifact(
            record.artifact_id, "Executor", action_id, str(record.uri), True,
            artifact_type=artifact_type, plan_node_id=plan_node_id,
        )
        return record

    def _stop(self, state: dict[str, Any], reason: str, actor: str) -> RunResult:
        state["status"] = RunStatus.CONTROLLED_STOP
        self._append_trace(state, "run_terminal", {"status": RunStatus.CONTROLLED_STOP, "reason": reason}, actor=actor)
        return self._finish(state, report=None)

    async def _generate_manager_report(self, state: dict[str, Any]) -> RunResult:
        """Ask Manager for a report, then validate references against run facts."""
        state["phase"] = "report"
        try:
            decision = await self._decide(state, "Manager")
            if decision["kind"] != "report":
                raise ValueError("Manager did not produce a report decision")
            report, incomplete = self._render_report(state, decision)
        except (BudgetExhausted, ProviderFailure):
            raise
        except Exception as error:
            state["status"] = RunStatus.REPORT_FAILED
            self._append_trace(
                state, "report_failed", {"error_type": type(error).__name__, "message": str(error)}, actor="Runtime"
            )
            return self._finish(state, report=None)
        state["status"] = RunStatus.PARTIAL if incomplete else RunStatus.COMPLETED
        self._append_trace(state, "report_validated", {
            "artifact_refs": decision["artifact_refs"],
            "deliverable_ids": [item["deliverable_id"] for item in decision["deliverables"]],
            "incomplete_deliverable_ids": incomplete,
        }, actor="Runtime")
        return self._finish(state, report=report)

    def _finish(self, state: dict[str, Any], report: str | None) -> RunResult:
        trace = self._trace(state)
        status = RunStatus(state["status"])
        trace.record_final_status(status, [item["artifact_id"] for item in state["artifacts"]])
        self._sync_trace(state)
        result = RunResult(
            run_id=state["run_id"], status=status, report=report, questions=state.get("questions", []),
            artifacts=[ArtifactRecord.model_validate(item) for item in state["artifacts"]],
            validation=ValidationSummary(
                valid=status in {RunStatus.COMPLETED, RunStatus.PARTIAL, RunStatus.NEEDS_CLARIFICATION, RunStatus.CONTROLLED_STOP},
                messages=state["messages"], tool_calls=state["tool_calls"], model_turns=state["model_turns"], plan_versions=state["plan_count"],
            ),
            trace_path=Path(state["run_dir"]) / "trace.jsonl", checkpoint_id=state.get("checkpoint_id"),
            execution_mode=ExecutionMode(state["execution_mode"]),
            provider=(state.get("provider") or {}).get("provider"),
        )
        self._write_files(state, result)
        return result

    def _write_files(self, state: dict[str, Any], result: RunResult) -> None:
        run_dir = Path(state["run_dir"])
        trace = self._trace(state)
        trace_path = run_dir / "trace.jsonl"
        trace_path.write_text("\n".join(json.dumps(event, ensure_ascii=False) for event in trace.events) + "\n", encoding="utf-8")
        state["trace"] = trace.to_dict()
        persisted_state = self._sanitize_for_persistence(state)
        (run_dir / "state.json").write_text(json.dumps(persisted_state, indent=2, ensure_ascii=False), encoding="utf-8")
        (run_dir / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        (run_dir / "delivery_obligations.json").write_text(
            json.dumps({"view_type": "delivery_obligation_manifest", "run_id": state["run_id"],
                        "obligations": state.get("delivery_obligations", [])}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (run_dir / "manifest.json").write_text(
            json.dumps({
                "run_id": state["run_id"],
                "execution_mode": state["execution_mode"],
                "schema_version": state["schema_version"],
                "domain_profile": state.get("domain_profile", "legacy"),
                "input_resource_identities": {key: {"artifact_type": value["artifact_type"], "sha256": value["sha256"],
                                                    "components": value.get("components", {})}
                                              for key, value in state.get("input_resources", {}).items()},
                "provider": state.get("provider"),
            "budgets": state["budgets"],
            "capabilities": state["capabilities"],
            "actual_wall_time_seconds": round(max(0.0, time.time() - float(state["started_at_unix"])), 3),
            "token_usage": state.get("token_usage"),
        }, indent=2),
            encoding="utf-8",
        )
        if result.report:
            (run_dir / "report.md").write_text(result.report + "\n", encoding="utf-8")
        planned_graph = {
            "view_type": "planned_workflow_graph",
            "run_id": state["run_id"],
            "delivery_obligations": state.get("delivery_obligations", []),
            "plan_versions": state.get("plan_history", []),
        }
        (run_dir / "planned_workflow_graph.json").write_text(
            json.dumps(planned_graph, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        try:
            process_graph = {"view_type": "observed_process_graph", **build_process_graph(state["run_id"], trace.events).to_dict()}
        except ValueError as error:
            process_graph = {"view_type": "observed_process_graph", "status": "unavailable", "reason": str(error)}
        (run_dir / "observed_process_graph.json").write_text(
            json.dumps(process_graph, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        # Transitional compatibility for the frozen v1 evaluator.  New v2
        # consumers must use the unambiguous observed filename above.
        (run_dir / "process_graph.json").write_text(
            json.dumps(process_graph, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def _model_artifact_record(record: dict[str, Any]) -> dict[str, str]:
        return {"artifact_id": record["artifact_id"], "artifact_type": record["artifact_type"]}

    def _render_report(self, state: dict[str, Any], decision: dict[str, Any]) -> tuple[str, list[str]]:
        for artifact in state["artifacts"]:
            if self._file_hash(Path(artifact["uri"])) != artifact["metadata"].get("artifact_sha256"):
                raise ValueError("Artifact changed before report delivery")
            for secondary in artifact["metadata"].get("secondary_outputs", []):
                if self._file_hash(Path(secondary["path"])) != secondary["sha256"]:
                    raise ValueError("Secondary artifact changed before report delivery")
        artifacts_by_id = {item["artifact_id"]: item for item in state["artifacts"]}
        artifact_refs = decision["artifact_refs"]
        if len(set(artifact_refs)) != len(artifact_refs):
            raise ValueError("Report artifact references must be unique")
        if set(artifact_refs) != set(artifacts_by_id):
            raise ValueError("Report must reference exactly the validated artifact manifest")
        factual = {item["deliverable_id"]: item for item in self._report_deliverables(state)}
        declared = {item["deliverable_id"]: item for item in decision["deliverables"]}
        if len(declared) != len(decision["deliverables"]):
            raise ValueError("Report deliverable identifiers must be unique")
        requested = {item["obligation_id"] for item in state.get("delivery_obligations", [])}
        incomplete: list[str] = []
        for deliverable_id, candidate in declared.items():
            if deliverable_id not in requested:
                raise ValueError("Report declared a deliverable outside the runtime obligation registry")
            if set(candidate["artifact_refs"]) - set(artifacts_by_id):
                raise ValueError("Report deliverable references an unknown artifact")
        for deliverable_id in requested:
            candidate = declared.get(deliverable_id)
            fact = factual.get(deliverable_id)
            if candidate is None or candidate["status"] != "delivered" or fact is None:
                incomplete.append(deliverable_id)
                continue
            if candidate["value"] != fact["value"] or candidate["unit"] != fact["unit"]:
                raise ValueError("Report deliverable value is not supported by runtime facts")
            if candidate["scope"] != fact["scope"]:
                raise ValueError("Report deliverable scope is not supported by runtime facts")
            if set(candidate["artifact_refs"]) != set(fact["artifact_refs"]):
                raise ValueError("Report deliverable does not reference its supporting artifacts")
        lines = [decision["summary"].strip(), "", "已验证制品："]
        lines.extend(f"- {artifacts_by_id[artifact_id]['artifact_type']} ({artifact_id})" for artifact_id in artifact_refs)
        if decision["deliverables"]:
            lines.extend(["", "用户请求交付："])
            for item in decision["deliverables"]:
                value = "未提供" if item["value"] is None else str(item["value"])
                unit = f" {item['unit']}" if item["unit"] else ""
                scope = f"；口径：{item['scope']}" if item["scope"] else ""
                lines.append(f"- {item['deliverable_id']}: {item['status']}，{value}{unit}{scope}")
        if incomplete:
            lines.extend(["", f"未完全交付：{', '.join(incomplete)}。本次结果为 partial，不应解释为完整成功。"])
        return "\n".join(lines), incomplete

    @staticmethod
    def _sanitize_for_persistence(value: Any) -> Any:
        """Drop chain-of-thought-like provider state while retaining typed facts."""
        forbidden = {"thought", "thoughts", "reasoning", "reasoning_content", "inner_messages"}
        if isinstance(value, dict):
            kind = " ".join(str(value.get(key, "")) for key in ("type", "event_type", "kind", "__type__")).lower()
            if "thoughtevent" in kind or kind == "thought":
                return None
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                normalized = key.lower()
                if normalized in forbidden or "thought" in normalized or "reasoning" in normalized:
                    continue
                sanitized = ExpertsRSSystem._sanitize_for_persistence(item)
                if sanitized is not None:
                    cleaned[key] = sanitized
            return cleaned
        if isinstance(value, list):
            return [item for candidate in value if (item := ExpertsRSSystem._sanitize_for_persistence(candidate)) is not None]
        if isinstance(value, tuple):
            return [item for candidate in value if (item := ExpertsRSSystem._sanitize_for_persistence(candidate)) is not None]
        return value

    @staticmethod
    def _redact_observation(observation: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in observation.items() if key in {"tool", "success", "message", "error_code", "artifact_id", "artifact_type"}}

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
                "summarize_classification": "composition_table", "plot_classification_map": "map",
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

    @staticmethod
    def _provider_for_request(request: RunRequest) -> DecisionProvider:
        if request.execution_mode == ExecutionMode.SCRIPTED_OFFLINE:
            return ScriptedDecisionProvider()
        assert request.provider is not None  # enforced by RunRequest
        return create_autogen_live_provider(request.provider)

    @staticmethod
    def _provider_manifest(request: RunRequest) -> dict[str, Any]:
        if request.execution_mode == ExecutionMode.SCRIPTED_OFFLINE:
            return {
                "provider": "scripted", "model": "deterministic", "api_calls_permitted": False,
                **ExpertsRSSystem._provenance_manifest(),
            }
        assert request.provider is not None
        return {
            "provider": request.provider.provider,
            "model": request.provider.model,
            "timeout_seconds": request.provider.timeout_seconds,
            "temperature": request.provider.temperature,
            "top_p": request.provider.top_p,
            "max_completion_tokens": request.provider.max_completion_tokens,
            "max_retries": request.provider.max_retries,
            "cache_enabled": request.provider.cache_enabled,
            "provider_base_url_redacted": redacted_provider_base_url(request.provider),
            "api_calls_permitted": True,
            **ExpertsRSSystem._provenance_manifest(),
        }

    @staticmethod
    def _provenance_manifest() -> dict[str, str | None]:
        root = Path(__file__).resolve().parent.parent
        panel = root / "ExpertsRS" / "evaluation" / "ch1" / "d3_light_panel_v1.json"
        prompt_source = Path(__file__).resolve().parent / "provider.py"
        def digest(path: Path) -> str | None:
            return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        try:
            code_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            code_commit = None
        return {"code_commit": code_commit, "prompt_hash": digest(prompt_source), "panel_hash": digest(panel)}


def run_sync(system: ExpertsRSSystem, request: RunRequest) -> RunResult:
    """Small convenience wrapper for non-async CLI callers."""
    return asyncio.run(system.run(request))
