"""Bounded decision boundary for the three-role ExpertsRS system.

The production adapter can be backed by AutoGen AgentChat.  Tests use
``ScriptedDecisionProvider`` so the very same runtime and tool executor can be
verified without a network call or an installed model provider.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol

from pydantic import ValidationError

from .models import (
    EngineerActionDecision,
    EngineerHandoffDecision,
    EngineerStopDecision,
    ManagerClarifyDecision,
    ManagerHandoffDecision,
    ReportDecision,
    ScientistPlanDecision,
    ScientistReviseDecision,
    ScientistStopDecision,
)


ROLE_DECISION_MODELS: dict[str, tuple[type[Any], ...]] = {
    "Manager": (ManagerClarifyDecision, ManagerHandoffDecision, ReportDecision),
    "Scientist": (ScientistPlanDecision, ScientistReviseDecision, ScientistStopDecision),
    "Engineer": (EngineerActionDecision, EngineerHandoffDecision, EngineerStopDecision),
}


def _decode_single_json_object(content: str) -> dict[str, Any]:
    """Decode one decision, allowing only a conventional JSON code fence.

    Some OpenAI-compatible endpoints wrap a JSON-mode response in a Markdown
    fence despite being asked not to. The fence is transport decoration, not
    part of the decision. A few compatible endpoints duplicate the *identical*
    JSON-mode payload; that exact transport duplication is canonicalised to one
    object. Prose, a different second decision, or any other trailing content
    remains rejected.
    """
    normalized = content.strip()
    if normalized.startswith("```"):
        opening, separator, body = normalized.partition("\n")
        if opening.lower() not in {"```", "```json"} or not separator or not body.endswith("```"):
            raise ValueError("decision must be one JSON object, optionally in a JSON code fence")
        normalized = body[:-3].rstrip()
    elif normalized.endswith("```"):
        # A few compatible endpoints emit only the closing fence after a
        # correctly JSON-formatted body. Permit that exact decoration only.
        normalized = normalized[:-3].rstrip()
    decoder = json.JSONDecoder()
    decision, end = decoder.raw_decode(normalized)
    trailing = normalized[end:].strip()
    if trailing:
        duplicate, duplicate_end = decoder.raw_decode(trailing)
        if duplicate != decision or trailing[duplicate_end:].strip():
            raise ValueError("decision must contain one JSON object")
    if not isinstance(decision, dict):
        raise ValueError("decision must be a JSON object")
    return decision


def parse_role_decision(role: str, payload: Any) -> dict[str, Any]:
    """Validate a model response against the narrow decision contract for its role."""
    if not isinstance(payload, dict):
        raise ValueError("decision must be a JSON object")
    models = ROLE_DECISION_MODELS.get(role)
    if models is None:
        raise ValueError(f"Unknown role: {role}")
    failures: list[str] = []
    for model in models:
        try:
            return model.model_validate(payload).model_dump(mode="json")
        except ValidationError as error:
            failures.append(str(error))
    raise ValueError(f"invalid {role} decision: {'; '.join(failures)}")


class DecisionProvider(Protocol):
    """Return one structured, auditable decision for a named runtime role."""

    async def decide(self, role: str, state: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class ScriptedDecisionProvider:
    """Deterministic policy used by system tests and offline D3 pre-flight.

    This is deliberately not a hidden scheduler: it reads the same compact
    state supplied to any model and returns a single role decision.  The system
    runtime remains responsible for all validation, permission checks,
    execution, recovery and terminal transitions.
    """

    def _operation(self, request: str) -> str:
        normalized = request.lower()
        if "ndsi" in normalized:
            return "unsupported_ndsi"
        if "land surface temperature" in normalized or "lst" in normalized:
            return "lst"
        if any(word in normalized for word in ("green cover", "greenspace", "green space", "vegetation coverage")):
            return "greenspace"
        if "ndvi" in normalized:
            return "ndvi"
        if any(word in normalized for word in ("vegetation health", "health condition", "健康")):
            return "clarify_health"
        if "vegetation" in normalized:
            return "ndvi"
        return "clarify_scope"

    @staticmethod
    def _workflow(operation: str, request: str, *, recovery: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
        """Deterministic v2 plans used by the offline harness.

        They exercise the same serialized contract required from a live
        Scientist without giving the Engineer an implicit action sequence.
        """
        base_artifact = {"artifact_id": "input_raster", "artifact_type": "raster"}
        metadata = {
            "node_id": "metadata", "operator_id": "expertsrs.read_raster_metadata.v1",
            "inputs": {"file_path": "input_raster"}, "output_artifact_id": "metadata",
            "config": {}, "depends_on": [],
        }
        ndvi = {
            "node_id": "ndvi", "operator_id": "expertsrs.calculate_ndvi.v1",
            "inputs": {"file_path": "input_raster"}, "output_artifact_id": "ndvi_raster",
            "config": {}, "depends_on": ["metadata"],
        }
        if operation == "lst":
            task = {
                "task_id": "lst_task", "goal": request, "expected_outputs": ["metadata"],
                "requested_outputs": ["thermal_precondition"], "required_metrics": [],
                "constraints": {"operation": "lst"},
            }
            return task, {"workflow_id": "lst_workflow", "input_artifacts": [base_artifact], "nodes": [metadata]}

        map_node = {
            "node_id": "index_map", "operator_id": "expertsrs.plot_index_map.v1",
            "inputs": {"file_path": "ndvi_raster"}, "output_artifact_id": "ndvi_map",
            "config": {}, "depends_on": ["ndvi"],
        }
        if operation != "greenspace":
            task = {
                "task_id": "ndvi_task", "goal": request,
                "expected_outputs": ["metadata", "index_raster", "map"],
                "requested_outputs": ["ndvi_map"], "required_metrics": [],
                "constraints": {"operation": "ndvi"},
            }
            return task, {"workflow_id": "ndvi_workflow", "input_artifacts": [base_artifact], "nodes": [metadata, ndvi, map_node]}

        threshold = {
            "node_id": "threshold", "operator_id": "expertsrs.apply_threshold.v1",
            "inputs": {"file_path": "ndvi_raster"}, "output_artifact_id": "greenspace_mask",
            "config": {"threshold_low": 0.3}, "depends_on": ["ndvi"],
        }
        thematic = {
            "node_id": "thematic_map", "operator_id": "expertsrs.plot_thematic_map.v1",
            "inputs": {"file_path": "greenspace_mask"}, "output_artifact_id": "greenspace_map",
            "config": {}, "depends_on": ["threshold"],
        }
        area = {
            "node_id": "area_statistics", "operator_id": "expertsrs.calculate_area.v1",
            "inputs": {"file_path": "greenspace_mask"}, "output_artifact_id": "greenspace_area",
            "config": {}, "depends_on": ["threshold"],
        }
        task = {
            "task_id": "greenspace_task", "goal": request,
            "expected_outputs": ["metadata", "index_raster", "mask_raster", "map", "area_statistics"],
            "requested_outputs": ["vegetation_coverage_map", "green_cover_rate"],
            "required_metrics": ["green_cover_rate"],
            "constraints": {"operation": "greenspace"},
        }
        return task, {
            "workflow_id": "greenspace_workflow",
            "input_artifacts": [base_artifact],
            "nodes": [metadata, ndvi, threshold, thematic, area],
        }

    async def decide(self, role: str, state: dict[str, Any]) -> dict[str, Any]:
        operation = self._operation(" ".join([state["request"], *state.get("user_answers", [])]))
        phase = state.get("phase", "initial")

        if role == "Manager":
            if phase == "report":
                artifacts = state.get("artifact_manifest", [])
                deliverables = state.get("report_deliverables", [])
                return {
                    "kind": "report",
                    "summary": f"已完成对“{state['request']}”的受控本地分析。结果仅包含下列已验证制品。",
                    "artifact_refs": [item["artifact_id"] for item in artifacts],
                    "deliverables": deliverables,
                }
            if operation in {"clarify_health", "clarify_scope"} and not state.get("user_answers"):
                return {
                    "kind": "clarify",
                    "question": "请说明希望评估的植被健康指标（例如 NDVI、绿地覆盖率）以及期望的输出地图或统计结果。",
                }
            return {"kind": "handoff", "target": "Scientist"}

        if role == "Scientist":
            if operation == "unsupported_ndsi":
                return {"kind": "stop", "reason": "NDSI is not supported by the registered ExpertsRS tool catalog."}
            if operation == "lst":
                task, workflow = self._workflow("lst", state["request"])
                return {"kind": "plan", "task": task, "workflow": workflow}
            if phase in {"initial", "planning"}:
                task, workflow = self._workflow("greenspace" if operation == "greenspace" else "ndvi", state["request"])
                return {
                    "kind": "plan",
                    "task": task,
                    "workflow": workflow,
                }
            if phase == "revision_required":
                task, workflow = self._workflow("greenspace", state["request"], recovery=True)
                return {
                    "kind": "revise", "reason": "Retry only the failed threshold branch after the observed transient failure.",
                    "base_plan_id": state["active_plan_id"],
                    "affected_node_ids": ["threshold", "thematic_map", "area_statistics"],
                    "task": task, "workflow": workflow,
                }
            return {"kind": "stop", "reason": "No safe Scientist decision is available."}

        if role == "Engineer":
            if operation == "lst":
                eligible = state.get("eligible_node_ids", [])
                if eligible:
                    return {"kind": "action", "node_id": eligible[0]}
                return {
                    "kind": "stop",
                    "reason": "Thermal precondition failed: LST requires Landsat-8 Band 10 TOA radiance; the supplied Sentinel-2 raster is not admissible.",
                }
            eligible = state.get("eligible_node_ids", [])
            if eligible:
                return {"kind": "action", "node_id": eligible[0]}
            return {"kind": "handoff", "target": "Manager"}

        raise ValueError(f"Unknown role: {role}")


class AutoGenSelectorDecisionProvider:
    """Optional adapter for the supported modern AutoGen AgentChat stack.

    The adapter intentionally imports AutoGen lazily.  It keeps framework state
    out of the domain runtime and requires the model response to be supplied as
    a structured JSON decision before the runtime will act on it.
    """

    def __init__(self, model_client: Any, agents: dict[str, Any], team: Any) -> None:
        self.model_client = model_client
        self.agents = agents
        self.team = team

    @classmethod
    def create(cls, model_client: Any, role_instructions: dict[str, str]) -> "AutoGenSelectorDecisionProvider":
        try:
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import SelectorGroupChat
        except ImportError as error:  # pragma: no cover - depends on optional package
            raise RuntimeError(
                "Modern AutoGen is not installed. Install the locked project dependencies first."
            ) from error
        agents = {
            role: AssistantAgent(
                role.lower(), model_client=model_client, system_message=instruction,
                description=f"{role} role for the ExpertsRS runtime.",
            )
            for role, instruction in role_instructions.items()
        }
        active_role: dict[str, str | None] = {"value": None}

        def candidate_func(_: Any) -> list[str]:
            """Expose exactly the role selected by the domain runtime."""
            if active_role["value"] is None:
                raise ValueError("Runtime must select a role before the AutoGen Team runs")
            return [active_role["value"].lower()]

        def selector_func(_: Any) -> str:
            if active_role["value"] is None:
                raise ValueError("Runtime must select a role before the AutoGen Team runs")
            return active_role["value"].lower()

        # The domain runtime owns admissible transitions, budgets, permissions
        # and terminal states.  The Team owns the model-facing conversation and
        # state.  Candidate/selector callbacks make that boundary explicit:
        # AutoGen never invents a role lifecycle, but it does execute the named
        # role through SelectorGroupChat for every decision.
        team = SelectorGroupChat(
            list(agents.values()), model_client=model_client,
            selector_func=selector_func, candidate_func=candidate_func,
            max_turns=1,
        )
        provider = cls(model_client, agents, team)
        provider._active_role = active_role
        return provider

    async def decide(self, role: str, state: dict[str, Any]) -> dict[str, Any]:
        from .provider import classify_provider_exception

        if role not in self.agents:
            raise ValueError(f"Unknown role: {role}")
        self._active_role["value"] = role
        try:
            response = await self.team.run(task=json.dumps(state, ensure_ascii=False))
        except Exception as error:
            raise classify_provider_exception(error) from error
        messages = getattr(response, "messages", [])
        role_messages = [message for message in messages if getattr(message, "source", None) == role.lower()]
        message = role_messages[-1] if role_messages else None
        content = getattr(message, "content", None)
        if not isinstance(content, str):
            raise ValueError(f"{role} produced no textual structured decision")
        decision = _decode_single_json_object(content)
        if not isinstance(decision.get("kind"), str):
            raise ValueError(f"{role} produced an invalid structured decision")
        usage = getattr(message, "models_usage", None)
        if usage is None:
            raise ValueError(f"{role} response omitted provider usage metadata")
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        if not isinstance(prompt_tokens, int) or not isinstance(completion_tokens, int):
            raise ValueError(f"{role} response has invalid provider usage metadata")
        decision["_provider_usage"] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        return decision

    async def save_state(self) -> dict[str, Any]:
        """Expose modern AutoGen Team state for a resumable live-session bridge."""
        return dict(await self.team.save_state())

    async def load_state(self, state: dict[str, Any]) -> None:
        await self.team.load_state(state)
