"""Backend provenance interfaces for future multi-agent execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .state import AgentRole, RunState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AgentBackendConfig:
    role: str
    backend_type: str
    provider: str
    model: str | None = None
    enabled: bool = True
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BackendCallRecord:
    call_id: str
    role: str
    backend_type: str
    provider: str
    model: str | None = None
    purpose: str | None = None
    started_at: str = field(default_factory=_now_iso)
    finished_at: str | None = None
    status: str = "started"
    token_input: int | None = None
    token_output: int | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(
        self,
        status: str = "ok",
        token_input: int | None = None,
        token_output: int | None = None,
        cost_usd: float | None = None,
        latency_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.finished_at = _now_iso()
        self.status = status
        self.token_input = token_input
        self.token_output = token_output
        self.cost_usd = cost_usd
        self.latency_ms = latency_ms
        if metadata:
            self.metadata.update(metadata)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_BACKEND_PLAN: dict[str, AgentBackendConfig] = {
    AgentRole.MANAGER.value: AgentBackendConfig(
        role=AgentRole.MANAGER.value,
        backend_type="llm",
        provider="configurable",
        model=None,
        notes="Fast conversational model for user clarification and report phrasing.",
    ),
    AgentRole.SCIENTIST.value: AgentBackendConfig(
        role=AgentRole.SCIENTIST.value,
        backend_type="llm_with_retrieval",
        provider="configurable",
        model=None,
        notes="Reasoning model plus curated RS knowledge and literature retrieval.",
    ),
    AgentRole.ENGINEER.value: AgentBackendConfig(
        role=AgentRole.ENGINEER.value,
        backend_type="tool_runtime_or_code_cli",
        provider="expertsrs_runtime",
        model=None,
        notes="Default path uses ToolRuntime; Claude Code CLI may be attached later for complex code edits.",
    ),
    AgentRole.VERIFIER.value: AgentBackendConfig(
        role=AgentRole.VERIFIER.value,
        backend_type="deterministic_or_llm_judge",
        provider="expertsrs_runtime",
        model=None,
        notes="Deterministic evaluator first; independent model verifier can be added later.",
    ),
}


def start_backend_call(
    state: RunState,
    role: AgentRole | str,
    backend_type: str,
    provider: str,
    model: str | None = None,
    purpose: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BackendCallRecord:
    role_value = role.value if isinstance(role, AgentRole) else str(role)
    record = BackendCallRecord(
        call_id=f"backend_{uuid4().hex[:12]}",
        role=role_value,
        backend_type=backend_type,
        provider=provider,
        model=model,
        purpose=purpose,
        metadata=metadata or {},
    )
    state.backend_calls.append(record)
    state.touch()
    return record


def finish_backend_call(state: RunState, call_id: str, **kwargs: Any) -> BackendCallRecord:
    for record in reversed(state.backend_calls):
        if record.call_id == call_id:
            record.finish(**kwargs)
            state.touch()
            return record
    raise ValueError(f"Unknown backend call id {call_id!r}")


def add_evidence(
    state: RunState,
    role: AgentRole | str,
    source: str,
    summary: str,
    citation: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role_value = role.value if isinstance(role, AgentRole) else str(role)
    record = {
        "role": role_value,
        "source": source,
        "summary": summary,
        "citation": citation,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }
    state.evidence.append(record)
    state.touch()
    return record


def backend_plan_to_dict(plan: dict[str, AgentBackendConfig] | None = None) -> dict[str, dict[str, Any]]:
    plan = plan or DEFAULT_BACKEND_PLAN
    return {role: config.to_dict() for role, config in plan.items()}
