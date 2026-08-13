"""Bounded decision boundary for the three-role ExpertsRS system.

The production adapter can be backed by AutoGen AgentChat.  Tests use
``ScriptedDecisionProvider`` so the very same runtime and tool executor can be
verified without a network call or an installed model provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import ValidationError

from .models import (
    EngineerActionDecision,
    EngineerHandoffDecision,
    EngineerReviseDecision,
    EngineerStopDecision,
    ManagerClarifyDecision,
    ManagerHandoffDecision,
    ReportDecision,
    ScientistPlanDecision,
    ScientistStopDecision,
)


ROLE_DECISION_MODELS: dict[str, tuple[type[Any], ...]] = {
    "Manager": (ManagerClarifyDecision, ManagerHandoffDecision, ReportDecision),
    "Scientist": (ScientistPlanDecision, ScientistStopDecision),
    "Engineer": (EngineerActionDecision, EngineerHandoffDecision, EngineerStopDecision, EngineerReviseDecision),
}


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
        if any(word in normalized for word in ("vegetation health", "health condition", "健康")):
            return "clarify_health"
        if "ndvi" in normalized or "vegetation" in normalized:
            return "ndvi"
        return "clarify_scope"

    async def decide(self, role: str, state: dict[str, Any]) -> dict[str, Any]:
        operation = self._operation(" ".join([state["request"], *state.get("user_answers", [])]))
        observations = state.get("observations", [])
        phase = state.get("phase", "initial")

        def artifact_ref(artifact_type: str) -> list[str]:
            for observation in reversed(observations):
                if observation.get("artifact_type") == artifact_type and isinstance(observation.get("artifact_id"), str):
                    return [observation["artifact_id"]]
            return []

        if role == "Manager":
            if phase == "report":
                artifacts = state.get("artifact_manifest", [])
                return {
                    "kind": "report",
                    "summary": f"已完成对“{state['request']}”的受控本地分析。结果仅包含下列已验证制品。",
                    "artifact_refs": [item["artifact_id"] for item in artifacts],
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
                return {"kind": "plan", "operation": "lst", "next_action": "read_raster_metadata"}
            if phase in {"initial", "planning"}:
                return {
                    "kind": "plan",
                    "operation": "greenspace" if operation == "greenspace" else "ndvi",
                    "next_action": "read_raster_metadata",
                }
            return {"kind": "handoff", "target": "Engineer"}

        if role == "Engineer":
            successes = [item.get("tool") for item in observations if item.get("success")]
            last = observations[-1] if observations else {}
            if operation == "lst":
                if not successes:
                    return {"kind": "action", "tool_name": "read_raster_metadata"}
                return {
                    "kind": "stop",
                    "reason": "Thermal precondition failed: LST requires Landsat-8 Band 10 TOA radiance; the supplied Sentinel-2 raster is not admissible.",
                }
            if not successes:
                return {"kind": "action", "tool_name": "read_raster_metadata"}
            if "calculate_ndvi" not in successes:
                return {"kind": "action", "tool_name": "calculate_ndvi"}
            if operation in {"ndvi", "clarify_health", "clarify_scope"}:
                if "plot_index_map" not in successes:
                    return {"kind": "action", "tool_name": "plot_index_map", "artifact_refs": artifact_ref("index_raster")}
                return {"kind": "handoff", "target": "Manager"}
            if operation == "greenspace":
                if last.get("tool") == "apply_threshold" and not last.get("success") and phase != "recovery":
                    return {"kind": "revise", "next_action": "apply_threshold"}
                if "apply_threshold" not in successes:
                    return {"kind": "action", "tool_name": "apply_threshold", "artifact_refs": artifact_ref("index_raster"), "parameters": {"threshold_low": 0.3}}
                if "plot_thematic_map" not in successes:
                    return {"kind": "action", "tool_name": "plot_thematic_map", "artifact_refs": artifact_ref("mask_raster")}
                if "calculate_area" not in successes:
                    return {"kind": "action", "tool_name": "calculate_area", "artifact_refs": artifact_ref("mask_raster")}
                return {"kind": "handoff", "target": "Manager"}
            return {"kind": "stop", "reason": "No safe action is available for this request."}

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
        import json

        if role not in self.agents:
            raise ValueError(f"Unknown role: {role}")
        self._active_role["value"] = role
        response = await self.team.run(task=json.dumps(state, ensure_ascii=False))
        messages = getattr(response, "messages", [])
        role_messages = [message for message in messages if getattr(message, "source", None) == role.lower()]
        content = getattr(role_messages[-1], "content", None) if role_messages else None
        if not isinstance(content, str):
            raise ValueError(f"{role} produced no textual structured decision")
        decision = json.loads(content)
        if not isinstance(decision, dict) or not isinstance(decision.get("kind"), str):
            raise ValueError(f"{role} produced an invalid structured decision")
        return decision

    async def save_state(self) -> dict[str, Any]:
        """Expose modern AutoGen Team state for a resumable live-session bridge."""
        return dict(await self.team.save_state())

    async def load_state(self, state: dict[str, Any]) -> None:
        await self.team.load_state(state)
