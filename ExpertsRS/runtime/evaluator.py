"""Deterministic evaluator for ExpertsRS runtime runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .contracts import ValidationIssue, get_tool_contract
from .state import AgentRole, RunState, WorkflowPhase


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvaluationResult:
    status: str
    issues: list[ValidationIssue] = field(default_factory=list)
    checked_at: str = field(default_factory=_now_iso)
    summary: str = ""
    evaluator: str = AgentRole.VERIFIER.value

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["issues"] = [issue.to_dict() for issue in self.issues]
        return payload


class RuntimeEvaluator:
    """Check that a run has enough state, trace, and artifacts to be auditable."""

    def evaluate(self, state: RunState) -> EvaluationResult:
        issues: list[ValidationIssue] = []

        if not state.structured_request:
            issues.append(ValidationIssue("missing_structured_request", "RunState has no structured request."))
        if not state.method_plan:
            issues.append(ValidationIssue("missing_method_plan", "RunState has no method plan."))
        if not state.tool_calls:
            issues.append(ValidationIssue("missing_tool_trace", "RunState has no recorded tool calls."))

        for call in state.tool_calls:
            if call.finished_at is None:
                issues.append(ValidationIssue("unfinished_tool_call", f"Tool call {call.call_id} did not finish.", tool_name=call.tool_name))
            if call.success is False:
                issues.append(ValidationIssue("failed_tool_call", call.message or f"Tool call {call.call_id} failed.", tool_name=call.tool_name))

        if not state.artifacts:
            issues.append(ValidationIssue("missing_artifacts", "RunState has no output artifacts."))

        calls_by_id = {call.call_id: call for call in state.tool_calls}
        for artifact in state.artifacts:
            if not Path(artifact.path).exists():
                issues.append(ValidationIssue("missing_artifact_path", f"Artifact path does not exist: {artifact.path}"))
                continue
            if artifact.source_tool_call_id is None:
                continue
            call = calls_by_id.get(artifact.source_tool_call_id)
            if call is None:
                issues.append(ValidationIssue("unknown_artifact_source", f"Artifact source call is missing: {artifact.source_tool_call_id}"))
                continue
            contract = get_tool_contract(call.tool_name)
            if contract is None:
                issues.append(ValidationIssue("missing_contract", f"No contract for source tool {call.tool_name}.", tool_name=call.tool_name))
                continue
            allowed_kinds = {item.kind for item in contract.output_artifacts}
            if artifact.kind not in allowed_kinds:
                issues.append(ValidationIssue(
                    "artifact_contract_mismatch",
                    f"Artifact kind {artifact.kind!r} is not allowed for {call.tool_name}; expected one of {sorted(allowed_kinds)}.",
                    tool_name=call.tool_name,
                ))

        status = "pass" if not issues else "fail"
        summary = "Runtime evaluation passed." if status == "pass" else f"Runtime evaluation failed with {len(issues)} issue(s)."
        result = EvaluationResult(status=status, issues=issues, summary=summary)
        state.metrics["evaluation_status"] = result.status
        state.metrics["evaluation"] = result.to_dict()
        state.add_decision(AgentRole.VERIFIER, summary, {"issue_count": len(issues)})
        state.set_phase(WorkflowPhase.VERIFY if issues else WorkflowPhase.REPORT)
        return result
