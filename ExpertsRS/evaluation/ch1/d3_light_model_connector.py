"""Leakage-safe direct model-call adapter for D3-light.

This module is deliberately an engineering adapter, not a thesis method object
or a multi-agent scheduler: it asks one named role for one structured next
decision. It performs no network I/O unless a caller supplies a network client
*and* the separately frozen API gate has been opened. The D3 live experiment is
blocked until the existing AG2/AutoGen routing is bridged to the runtime.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

import requests

from .d3_light_protocol import API_GATE_ENV, api_calls_permitted


class ChatCompletionClient(Protocol):
    """Small provider boundary; an SDK-specific adapter can implement this later."""

    def complete(self, *, model: str, messages: list[dict[str, str]], settings: dict[str, Any]) -> dict[str, Any]: ...


class APIAuthorizationError(RuntimeError):
    """Raised before an adapter is allowed to send any provider request."""


@dataclass(frozen=True)
class OpenAICompatibleClient:
    """Minimal HTTP client for a future approved DeepSeek-compatible run.

    The API key is supplied at construction and is never written to a manifest,
    trace, exception, or console message.
    """

    api_key: str
    base_url: str
    session: Any = requests

    def complete(self, *, model: str, messages: list[dict[str, str]], settings: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key or self.api_key == "your-api-key":
            raise APIAuthorizationError("No usable model API key is configured")
        endpoint = self.base_url.rstrip("/") + "/chat/completions"
        response = self.session.post(
            endpoint,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": messages,
                "temperature": settings["temperature"],
                "top_p": settings["top_p"],
                "max_tokens": settings["max_tokens"],
            },
            timeout=settings["timeout_seconds"],
        )
        response.raise_for_status()
        payload = response.json()
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError("Provider response lacks choices[0].message.content") from error
        return {"content": content, "usage": payload.get("usage"), "provider_model": payload.get("model", model)}


def configured_deepseek_client(panel: dict[str, Any]) -> OpenAICompatibleClient:
    """Build the approved provider client only when its model ID matches protocol."""
    protocol = panel["proposed_run_protocol"]["model_selection"]
    configured_model = os.getenv(protocol["model_env"], protocol["default_model"])
    if configured_model != protocol["default_model"]:
        raise APIAuthorizationError(
            "Configured model differs from frozen D3-light model; amend and review the protocol first."
        )
    return OpenAICompatibleClient(
        api_key=os.getenv(protocol["provider_env"], ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
    )


@dataclass(frozen=True)
class ModelDecisionAdapter:
    """Turn a redacted D3-light state into one direct role decision; not a scheduler."""

    panel: dict[str, Any]
    client: ChatCompletionClient

    def next_step(self, agent_case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        if not api_calls_permitted(self.panel):
            raise APIAuthorizationError(
                f"Live model calls are disabled. Set panel run_gate and {API_GATE_ENV}=YES only after approval."
            )
        request = self.build_request(agent_case, state)
        response = self.client.complete(
            model=request["model"], messages=request["messages"], settings=request["settings"]
        )
        decision = self.parse_decision(response)
        return {**decision, "usage": response.get("usage"), "provider_model": response.get("provider_model")}

    def build_request(self, agent_case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        """Build the only payload permitted to leave the local machine."""
        protocol = self.panel["proposed_run_protocol"]
        role = _role_for_phase(agent_case["source_task_id"], state.get("phase", "initial"))
        messages = [
            {"role": "system", "content": _role_instruction(role, protocol)},
            {"role": "user", "content": json.dumps(_redacted_case(agent_case, state), ensure_ascii=False)},
        ]
        return {
            "model": protocol["model_selection"]["default_model"],
            "settings": {
                "temperature": protocol["sampling"]["temperature"],
                "top_p": protocol["sampling"]["top_p"],
                "max_tokens": protocol["per_run_budget"]["max_completion_tokens"],
                "timeout_seconds": protocol["per_run_budget"]["max_wall_time_seconds"],
            },
            "messages": messages,
        }

    @staticmethod
    def parse_decision(response: dict[str, Any]) -> dict[str, Any]:
        """Accept only small, explicit next-step JSON; no hidden natural-language parser."""
        content = response.get("content")
        if not isinstance(content, str):
            raise ValueError("Model response lacks string content")
        try:
            decision = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError("Model response is not valid decision JSON") from error
        kind = decision.get("kind")
        if kind == "action":
            if not isinstance(decision.get("tool"), str):
                raise ValueError("Action decision requires a tool name")
            if "plan_update" in decision and not isinstance(decision["plan_update"], str):
                raise ValueError("plan_update must be a short string when supplied")
        elif kind == "stop":
            if not isinstance(decision.get("status"), str) or not isinstance(decision.get("reason"), str):
                raise ValueError("Stop decision requires status and reason")
        elif kind == "clarify":
            if not isinstance(decision.get("question"), str):
                raise ValueError("Clarify decision requires a question")
        else:
            raise ValueError(f"Unsupported decision kind: {kind!r}")
        return decision


def _role_for_phase(task_id: int, phase: str) -> str:
    if task_id == 13:
        return "Manager"
    if phase in {"metadata", "thermal_check"}:
        return "Scientist"
    return "Engineer"


def _role_instruction(role: str, protocol: dict[str, Any]) -> str:
    # Import only public role prompts; evaluator contracts and fixture data never
    # enter this module's model payload.
    from prompts import engineer_prompt, manager_prompt, scientist_prompt

    base_prompt = {"Manager": manager_prompt, "Scientist": scientist_prompt, "Engineer": engineer_prompt}[role]
    contracts = {
        "Manager": (
            "You are the Manager. Decide whether to ask the user one concise clarification. "
            "Return only JSON: {\"kind\":\"clarify\",\"question\":\"...\"}."
        ),
        "Scientist": (
            "You are the Scientist. Decide the next information-gathering action or an explicit stop. "
            "Return only one JSON object: {\"kind\":\"action\",\"tool\":\"registered_tool_name\"} "
            "or {\"kind\":\"stop\",\"status\":\"controlled_stop\",\"reason\":\"...\"}."
        ),
        "Engineer": (
            "You are the Engineer. Decide the next registered tool action after the observed result, "
            "or explicitly stop. Return only one JSON object using the same action/stop schema."
        ),
    }
    budget = protocol["per_run_budget"]
    return (
        base_prompt
        + "\n\nD3-light decision format:\n"
        + contracts[role]
        + f" The experiment allows at most {budget['max_tool_calls']} tool calls and {budget['max_model_turns']} model turns. "
        + "When the input phase is recovery, an action decision must also include a one-sentence plan_update. "
        + "Do not invent tools, file paths, data values, or success. Do not expose chain-of-thought."
    )


def _redacted_case(agent_case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Remove filesystem paths, hashes, hidden fixtures, scores, and arbitrary state fields."""
    allowed_observation_keys = {"success", "message", "error_code", "tool_name", "artifact_type"}
    observation = state.get("last_observation", {})
    safe_observation = {
        key: value for key, value in observation.items()
        if key in allowed_observation_keys and isinstance(value, (str, int, float, bool, type(None)))
    }
    # The tested agent may observe a recoverable tool failure, but must never
    # learn that an evaluator deliberately seeded it.
    if isinstance(safe_observation.get("error_code"), str) and safe_observation["error_code"].startswith("fixture_"):
        safe_observation["error_code"] = "transient_tool_failure"
    if isinstance(safe_observation.get("message"), str) and safe_observation["message"].startswith("Seeded D3-light fixture:"):
        safe_observation["message"] = "The tool failed before producing its requested output."
    return {
        "task_id": agent_case["source_task_id"],
        "request": agent_case["request"],
        "context": agent_case["context"],
        "phase": state.get("phase"),
        "available_tools": state.get("available_tools", []),
        "last_observation": safe_observation,
        "remaining_tool_budget": state.get("remaining_tool_budget"),
    }
