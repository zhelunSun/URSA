"""Minimal runtime workflow over explicit state.

This is not the final orchestrator. It is a small framework-neutral smoke path
that proves state, tools, and artifacts can work without the notebook.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import RunArtifactStore
from .evaluator import EvaluationResult, RuntimeEvaluator
from .state import AgentRole, RunState, WorkflowPhase
from .tool_runtime import ToolRuntime


class RuntimeWorkflow:
    def __init__(
        self,
        state: RunState | None = None,
        tool_runtime: ToolRuntime | None = None,
        artifact_store: RunArtifactStore | None = None,
        evaluator: RuntimeEvaluator | None = None,
    ):
        self.state = state or RunState()
        self.tools = tool_runtime or ToolRuntime()
        self.artifacts = artifact_store or RunArtifactStore()
        self.evaluator = evaluator or RuntimeEvaluator()
        self.artifacts.bind(self.state)
        self.tools.set_output_dir(str(self.artifacts.path("tool_outputs")))

    def initialize_request(self, user_request: str) -> RunState:
        self.state.user_request = user_request
        self.state.set_phase(WorkflowPhase.CLARIFY)
        self.state.add_decision(AgentRole.MANAGER, "Captured initial user request")
        self.artifacts.write_manifest(self.state)
        return self.state

    def set_structured_request(self, **fields: Any) -> RunState:
        self.state.structured_request.update(fields)
        self.state.set_phase(WorkflowPhase.DEFINE)
        self.state.add_decision(AgentRole.MANAGER, "Updated structured request", fields)
        self.artifacts.write_manifest(self.state)
        return self.state

    def set_method_plan(self, plan: dict[str, Any], assumptions: list[str] | None = None) -> RunState:
        self.state.method_plan = plan
        if assumptions:
            self.state.assumptions.extend(assumptions)
        self.state.set_phase(WorkflowPhase.PLAN_APPROVAL)
        self.state.add_checkpoint("plan_approval", prompt="Approve the proposed remote-sensing analysis plan.")
        self.state.add_decision(AgentRole.SCIENTIST, "Prepared method plan", plan)
        self.artifacts.write_manifest(self.state)
        return self.state

    def approve_plan(self, response: str = "approved") -> RunState:
        self.state.resolve_checkpoint("plan_approval", response=response, status="approved")
        self.state.set_phase(WorkflowPhase.SOLVE)
        self.artifacts.write_manifest(self.state)
        return self.state

    def discover_data(self) -> dict[str, Any]:
        result = self.tools.call(self.state, "list_available_data_files", role=AgentRole.ENGINEER)
        if result.get("success") and result.get("data"):
            files = result["data"].get("files", [])
            abs_paths = result["data"].get("abs_paths", [])
            self.state.selected_data = [
                {"file": file_name, "path": path}
                for file_name, path in zip(files, abs_paths)
            ]
        self.artifacts.write_manifest(self.state)
        return result

    def write_report_stub(self, summary: str) -> Path:
        self.state.set_phase(WorkflowPhase.REPORT)
        path = self.artifacts.write_text_artifact(
            self.state,
            "report_stub.md",
            summary,
            kind="report",
            label="runtime_report_stub",
        )
        self.state.set_phase(WorkflowPhase.COMPLETE)
        self.artifacts.write_manifest(self.state)
        return path

    def evaluate(self) -> EvaluationResult:
        self.state.set_phase(WorkflowPhase.VERIFY)
        result = self.evaluator.evaluate(self.state)
        self.artifacts.write_manifest(self.state)
        return result
