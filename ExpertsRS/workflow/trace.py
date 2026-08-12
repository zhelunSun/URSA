"""Portable JSON traces for inspection, evaluation, and future trajectory data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .graph import WorkflowGraph
from .repair import RepairDecision
from .runtime import (
    Checkpoint,
    EventReference,
    PermissionDecision,
    PermissionRequest,
    PlanVersion,
)
from .specs import TaskSpec
from .validator import ValidationReport


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowTrace:
    run_id: str
    events: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        actor: str = "Runtime",
        object_id: str | None = None,
        references: Iterable[EventReference] = (),
    ) -> str:
        """Append one immutable run fact while preserving the legacy payload shape."""
        sequence_no = len(self.events) + 1
        event_id = f"{self.run_id}:e{sequence_no:04d}"
        self.events.append({
            "event_id": event_id,
            "sequence_no": sequence_no,
            "timestamp": _now(),
            "event_type": event_type,
            "actor": actor,
            "object_id": object_id or event_id,
            "references": [reference.to_dict() for reference in references],
            "payload": payload,
        })
        return event_id

    def record_plan_version(self, plan: PlanVersion) -> str:
        references = []
        if plan.parent_version_id:
            references.append(EventReference(plan.parent_version_id, "revises"))
        if plan.trigger_event_id:
            references.append(EventReference(plan.trigger_event_id, "triggered_by"))
        if plan.restart_from_checkpoint_id:
            references.append(EventReference(plan.restart_from_checkpoint_id, "restarts_from"))
        return self.record(
            "plan_version_recorded",
            plan.to_dict(),
            actor=plan.owner,
            object_id=plan.object_id,
            references=references,
        )

    def record_permission(
        self,
        request: PermissionRequest,
        decision: PermissionDecision,
    ) -> str:
        if decision.request_id != request.request_id:
            raise ValueError("Permission decision does not match its request")
        return self.record(
            "permission_decided",
            {"request": request.to_dict(), "decision": decision.to_dict()},
            actor="Runtime",
            object_id=decision.decision_id,
        )

    def record_action(
        self,
        action_id: str,
        actor: str,
        tool_name: str,
        arguments: dict[str, Any],
        plan_version_id: str,
        permission_decision_id: str,
        branch_id: str = "main",
    ) -> str:
        return self.record(
            "action_started",
            {"tool_name": tool_name, "arguments": arguments, "branch_id": branch_id},
            actor=actor,
            object_id=action_id,
            references=(
                EventReference(plan_version_id, "implements"),
                EventReference(permission_decision_id, "authorized_by"),
            ),
        )

    def record_observation(
        self,
        observation_id: str,
        actor: str,
        action_id: str,
        success: bool,
        payload: dict[str, Any],
    ) -> str:
        return self.record(
            "tool_observation_recorded",
            {"success": success, **payload},
            actor=actor,
            object_id=observation_id,
            references=(EventReference(action_id, "observes"),),
        )

    def record_artifact(
        self,
        artifact_id: str,
        actor: str,
        action_id: str,
        uri: str,
        validated: bool,
        artifact_type: str | None = None,
    ) -> str:
        payload = {"uri": uri, "validated": validated}
        if artifact_type is not None:
            payload["artifact_type"] = artifact_type
        return self.record(
            "artifact_recorded",
            payload,
            actor=actor,
            object_id=artifact_id,
            references=(EventReference(action_id, "produced_by"),),
        )

    def record_checkpoint(self, checkpoint: Checkpoint) -> str:
        references = [
            EventReference(checkpoint.plan_version_id, "uses_plan"),
            EventReference(checkpoint.resume_after_event_id, "resumes_after"),
        ]
        references.extend(
            EventReference(artifact_id, "reuses_valid_artifact")
            for artifact_id in checkpoint.valid_artifact_ids
        )
        return self.record(
            "checkpoint_recorded",
            checkpoint.to_dict(),
            actor="Runtime",
            object_id=checkpoint.checkpoint_id,
            references=references,
        )

    def record_plan(self, task: TaskSpec, graph: WorkflowGraph) -> None:
        self.record("plan_created", {"task": task.to_dict(), "workflow": graph.to_dict()})

    def record_validation(self, report: ValidationReport) -> None:
        self.record("validation_completed", report.to_dict())

    def record_repair(self, decision: RepairDecision, graph: WorkflowGraph) -> None:
        self.record("repair_completed", {"decision": decision.to_dict(), "workflow": graph.to_dict()})

    def record_final_status(self, status: str, artifacts: list[str]) -> None:
        self.record("run_completed", {"status": status, "artifacts": artifacts})

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "events": self.events}

    def write(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return destination
