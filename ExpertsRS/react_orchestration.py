"""Minimal ReAct orchestration for the ExpertsRS multi-agent prototype.

The global workflow remains Manager -> Scientist -> Engineer -> Manager.  This
module adds local Reason -> Action -> Observation loops for Scientist and
Engineer: a tool result is always routed back to the agent that requested it.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Iterable

from workflow import WorkflowTrace


SCIENTIST_TOOL_NAMES = {"list_available_data_files", "read_raster_metadata"}
SCIENTIST_TOOL_LIMIT = 4
ENGINEER_TOOL_LIMIT = 10


def _tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Return OpenAI-style and legacy function calls in one compact format."""
    calls = list(message.get("tool_calls") or [])
    if message.get("function_call"):
        calls.append({"function": message["function_call"]})
    return calls


def _call_names(message: dict[str, Any]) -> list[str]:
    return [call.get("function", {}).get("name", "unknown") for call in _tool_calls(message)]


def _compact(value: Any, limit: int = 1_000) -> str:
    text = str(value if value is not None else "")
    return text if len(text) <= limit else text[:limit] + "…"


def _ag2_compatible_tool(tool: Callable[..., Any]) -> Callable[..., Any]:
    """Return a typed facade for AG2 without changing the underlying tool.

    The historical tool layer predates AG2's strict function-schema validator,
    which requires annotations for every mandatory parameter.  The facade fills
    only missing annotations with ``Any`` and forwards calls unchanged.
    """
    signature = inspect.signature(tool)
    parameters = [
        parameter.replace(annotation=Any)
        if parameter.annotation is inspect.Parameter.empty else parameter
        for parameter in signature.parameters.values()
    ]
    return_annotation = dict if signature.return_annotation is inspect.Signature.empty else signature.return_annotation

    @wraps(tool)
    def typed_facade(*args, **kwargs):
        return tool(*args, **kwargs)

    typed_facade.__signature__ = signature.replace(parameters=parameters, return_annotation=return_annotation)
    typed_facade.__annotations__ = {parameter.name: parameter.annotation for parameter in parameters}
    typed_facade.__annotations__["return"] = return_annotation
    return typed_facade


@dataclass
class ReActRoutingState:
    """Mutable state intentionally limited to routing budgets and trace data."""

    run_id: str
    trace_path: Path | None = None
    trace: WorkflowTrace = field(init=False)
    pending_tool_owner: str | None = None
    tool_calls_by_agent: dict[str, int] = field(default_factory=lambda: {"Scientist": 0, "Engineer": 0})
    finalised: bool = False

    def __post_init__(self) -> None:
        self.trace = WorkflowTrace(self.run_id)

    def record_decision(self, agent_name: str, message: dict[str, Any]) -> None:
        self.trace.record("decision", {
            "agent": agent_name,
            "summary": _compact(message.get("content")),
        }, actor=agent_name)

    def record_tool_call(self, agent_name: str, message: dict[str, Any]) -> None:
        calls = _tool_calls(message)
        self.tool_calls_by_agent[agent_name] = self.tool_calls_by_agent.get(agent_name, 0) + len(calls)
        self.trace.record("tool_call", {
            "agent": agent_name,
            "tools": _call_names(message),
            "calls": calls,
            "call_count": len(calls),
            "cumulative_tool_calls": self.tool_calls_by_agent[agent_name],
        }, actor=agent_name)

    def record_observation(self, executor_message: dict[str, Any]) -> None:
        content = executor_message.get("content")
        self.trace.record("tool_observation", {
            "agent": self.pending_tool_owner,
            "content": content if isinstance(content, (dict, list, int, float, bool)) else _compact(content),
        }, actor="Executor")

    def record_handoff(self, source: str, target: str, message: dict[str, Any]) -> None:
        self.trace.record("agent_handoff", {
            "source": source,
            "target": target,
            "summary": _compact(message.get("content")),
        }, actor=source)

    def finalise(self, status: str) -> None:
        if self.finalised:
            return
        self.trace.record("final_status", {"status": status, "tool_calls": self.tool_calls_by_agent.copy()})
        if self.trace_path is not None:
            self.trace.write(self.trace_path)
        self.finalised = True

    def can_call_tool(self, agent_name: str) -> bool:
        limit = SCIENTIST_TOOL_LIMIT if agent_name == "Scientist" else ENGINEER_TOOL_LIMIT
        return self.tool_calls_by_agent.get(agent_name, 0) < limit

def register_selector_executor_tools(
    scientist: Any,
    engineer: Any,
    executor: Any,
    tools: Iterable[Callable[..., Any]],
) -> None:
    """Register selection with assistants and execution only with Executor.

    This uses AG2/legacy AutoGen's documented selector/executor split.  The
    assistants therefore cannot directly execute a callable through a local
    ``function_map``.
    """
    for tool in tools:
        registered_tool = _ag2_compatible_tool(tool)
        description = (registered_tool.__doc__ or registered_tool.__name__).strip().split("\n")[0]
        if registered_tool.__name__ in SCIENTIST_TOOL_NAMES:
            scientist.register_for_llm(name=registered_tool.__name__, description=description)(registered_tool)
        engineer.register_for_llm(name=registered_tool.__name__, description=description)(registered_tool)
        executor.register_for_execution(name=registered_tool.__name__, description=description)(registered_tool)


def make_react_speaker_selection(
    manager: Any,
    user_proxy: Any,
    scientist: Any,
    engineer: Any,
    executor: Any,
    state: ReActRoutingState,
):
    """Create a GroupChat selector with per-agent ReAct loops.

    A successful tool call intentionally does *not* advance the global stage:
    the result is an observation for the requesting Scientist or Engineer.
    """
    agent_by_name = {agent.name: agent for agent in (manager, user_proxy, scientist, engineer, executor)}

    def speaker_selection(last_speaker: Any, groupchat: Any):
        messages = groupchat.messages
        if len(messages) <= 1:
            return manager

        last_message = messages[-1]
        last_name = last_speaker.name

        if last_speaker == manager:
            return user_proxy

        if last_speaker == user_proxy:
            content = _compact(last_message.get("content"), limit=10_000)
            if "Approve" in content:
                return scientist
            if "End" in content or "exit" in content.lower():
                state.finalise("user_ended")
                return None
            return manager

        if last_speaker in (scientist, engineer):
            if _tool_calls(last_message):
                if len(_tool_calls(last_message)) != 1:
                    state.trace.record("tool_observation", {
                        "agent": last_name,
                        "content": "Protocol error: ReAct permits one tool call per decision.",
                    })
                    return last_speaker
                if not state.can_call_tool(last_name):
                    state.finalise(f"{last_name.lower()}_tool_budget_exhausted")
                    return None
                state.record_decision(last_name, last_message)
                state.record_tool_call(last_name, last_message)
                state.pending_tool_owner = last_name
                return executor

            if last_speaker == scientist:
                state.record_handoff("Scientist", "Engineer", last_message)
                return engineer
            state.record_handoff("Engineer", "Manager", last_message)
            return manager

        if last_speaker == executor:
            state.record_observation(last_message)
            owner = agent_by_name.get(state.pending_tool_owner or "")
            if owner is None:
                state.finalise("orphaned_tool_observation")
                return None
            state.pending_tool_owner = None
            return owner

        state.finalise("unknown_routing_state")
        return None

    return speaker_selection


SCIENTIST_REACT_PROTOCOL = """
### ReAct interaction protocol
When data context is needed, follow this loop: give one short `Decision` based
on the current request, call exactly one available read-only tool, inspect the
Executor's real observation, then decide whether another observation is needed.
Do not invent metadata or claim a tool result before receiving it. When the plan
is sufficiently grounded, provide a structured handoff to Engineer instead of a
tool call. Do not provide long chain-of-thought; one decision sentence is enough.
"""


ENGINEER_REACT_PROTOCOL = """
### ReAct interaction protocol
For each analytical step, give one short `Decision` grounded in the latest task
context or Executor observation, then call exactly one registered tool. Inspect
the returned `success`, statistics and artifact paths before deciding the next
tool. Never predict a tool result. On an unsuccessful observation, choose a
safe retry, an alternative tool, or explicitly stop that subtask. When expected
artifacts are available, provide a structured handoff to Manager. Do not provide
long chain-of-thought; one decision sentence is enough.
"""
