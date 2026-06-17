"""Explicit runtime state for ExpertsRS.

This module is intentionally framework-neutral. AutoGen, LangGraph, or any
future orchestrator should read and write this state instead of inferring the
workflow from chat history alone.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowPhase(str, Enum):
    CREATED = "created"
    CLARIFY = "clarify"
    DEFINE = "define"
    PLAN_APPROVAL = "plan_approval"
    SOLVE = "solve"
    VERIFY = "verify"
    REPORT = "report"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentRole(str, Enum):
    USER = "user"
    MANAGER = "manager"
    SCIENTIST = "scientist"
    ENGINEER = "engineer"
    VERIFIER = "verifier"
    RUNTIME = "runtime"


@dataclass
class HumanCheckpoint:
    name: str
    status: str = "pending"
    prompt: str | None = None
    response: str | None = None
    created_at: str = field(default_factory=_now_iso)
    resolved_at: str | None = None


@dataclass
class ToolCallRecord:
    call_id: str
    tool_name: str
    args: dict[str, Any]
    role: str = AgentRole.ENGINEER.value
    started_at: str = field(default_factory=_now_iso)
    finished_at: str | None = None
    success: bool | None = None
    message: str | None = None
    result_summary: dict[str, Any] | None = None


@dataclass
class ArtifactRecord:
    artifact_id: str
    kind: str
    path: str
    source_tool_call_id: str | None = None
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)


@dataclass
class RunState:
    run_id: str = field(default_factory=lambda: f"run_{uuid4().hex[:12]}")
    phase: str = WorkflowPhase.CREATED.value
    user_request: str | None = None
    structured_request: dict[str, Any] = field(default_factory=dict)
    selected_data: list[dict[str, Any]] = field(default_factory=list)
    method_plan: dict[str, Any] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    pending_questions: list[str] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    artifacts: list[ArtifactRecord] = field(default_factory=list)
    checkpoints: list[HumanCheckpoint] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def set_phase(self, phase: WorkflowPhase | str) -> None:
        self.phase = phase.value if isinstance(phase, WorkflowPhase) else str(phase)
        self.touch()

    def touch(self) -> None:
        self.updated_at = _now_iso()

    def add_decision(self, role: AgentRole | str, summary: str, details: dict[str, Any] | None = None) -> None:
        role_value = role.value if isinstance(role, AgentRole) else str(role)
        self.decisions.append({
            "role": role_value,
            "summary": summary,
            "details": details or {},
            "created_at": _now_iso(),
        })
        self.touch()

    def add_checkpoint(self, name: str, prompt: str | None = None) -> HumanCheckpoint:
        checkpoint = HumanCheckpoint(name=name, prompt=prompt)
        self.checkpoints.append(checkpoint)
        self.touch()
        return checkpoint

    def resolve_checkpoint(self, name: str, response: str, status: str = "approved") -> None:
        for checkpoint in reversed(self.checkpoints):
            if checkpoint.name == name and checkpoint.status == "pending":
                checkpoint.status = status
                checkpoint.response = response
                checkpoint.resolved_at = _now_iso()
                self.touch()
                return
        raise ValueError(f"No pending checkpoint named {name!r}")

    def start_tool_call(self, tool_name: str, args: dict[str, Any], role: AgentRole | str = AgentRole.ENGINEER) -> ToolCallRecord:
        role_value = role.value if isinstance(role, AgentRole) else str(role)
        record = ToolCallRecord(
            call_id=f"tool_{uuid4().hex[:12]}",
            tool_name=tool_name,
            args=args,
            role=role_value,
        )
        self.tool_calls.append(record)
        self.touch()
        return record

    def finish_tool_call(
        self,
        call_id: str,
        success: bool,
        message: str | None = None,
        result_summary: dict[str, Any] | None = None,
    ) -> None:
        for record in reversed(self.tool_calls):
            if record.call_id == call_id:
                record.finished_at = _now_iso()
                record.success = success
                record.message = message
                record.result_summary = result_summary
                self.touch()
                return
        raise ValueError(f"Unknown tool call id {call_id!r}")

    def add_artifact(
        self,
        kind: str,
        path: str,
        source_tool_call_id: str | None = None,
        label: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord:
        artifact = ArtifactRecord(
            artifact_id=f"artifact_{uuid4().hex[:12]}",
            kind=kind,
            path=path,
            source_tool_call_id=source_tool_call_id,
            label=label,
            metadata=metadata or {},
        )
        self.artifacts.append(artifact)
        self.touch()
        return artifact

    def add_error(self, where: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.errors.append({
            "where": where,
            "message": message,
            "details": details or {},
            "created_at": _now_iso(),
        })
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RunState":
        payload = dict(payload)
        payload["tool_calls"] = [ToolCallRecord(**item) for item in payload.get("tool_calls", [])]
        payload["artifacts"] = [ArtifactRecord(**item) for item in payload.get("artifacts", [])]
        payload["checkpoints"] = [HumanCheckpoint(**item) for item in payload.get("checkpoints", [])]
        return cls(**payload)

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "RunState":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)
