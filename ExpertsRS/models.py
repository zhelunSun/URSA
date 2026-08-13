"""Stable JSON contracts for the authoritative ExpertsRS runtime."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunStatus(StrEnum):
    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    CONTROLLED_STOP = "controlled_stop"
    FAILED = "failed"


class RunBudgets(BaseModel):
    """Bounded research-run budget, enforced by the runtime rather than prompts."""

    model_config = ConfigDict(frozen=True)

    max_model_turns: int = Field(default=12, ge=1, le=100)
    max_tool_calls: int = Field(default=10, ge=1, le=100)
    max_tool_calls_scientist: int = Field(default=4, ge=0, le=100)
    max_tool_calls_engineer: int = Field(default=6, ge=0, le=100)


DEFAULT_RESEARCH_BUDGETS = RunBudgets()


class RuntimeCapabilities(BaseModel):
    """The only switchable mechanism policy used by evaluation conditions."""

    model_config = ConfigDict(frozen=True)

    allow_plan_revision: bool = True
    allow_checkpoint_recovery: bool = True


class RunRequest(BaseModel):
    """One natural-language remote-sensing request and its local raster inputs."""

    request: str = Field(min_length=1)
    data_paths: list[Path] = Field(default_factory=list)
    output_dir: Path
    run_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
    budgets: RunBudgets = DEFAULT_RESEARCH_BUDGETS
    capabilities: RuntimeCapabilities = RuntimeCapabilities()

    @field_validator("request")
    @classmethod
    def _request_must_have_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request must not be blank")
        return value.strip()


class ArtifactRecord(BaseModel):
    artifact_id: str
    artifact_type: str
    uri: Path
    validated: bool = True
    producer_action_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationSummary(BaseModel):
    valid: bool
    messages: list[str] = Field(default_factory=list)
    tool_calls: int = 0
    model_turns: int = 0
    plan_versions: int = 0


class RunResult(BaseModel):
    """Stable result returned by both the Python API and CLI."""

    run_id: str
    status: RunStatus
    report: str | None = None
    questions: list[str] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    validation: ValidationSummary
    trace_path: Path
    checkpoint_id: str | None = None
