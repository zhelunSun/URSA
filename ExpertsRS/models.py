"""Stable JSON contracts for the authoritative ExpertsRS runtime."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RunStatus(StrEnum):
    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    CONTROLLED_STOP = "controlled_stop"
    FAILED = "failed"
    REPORT_FAILED = "report_failed"


class ExecutionMode(StrEnum):
    """Explicit execution identity; offline output is never live evidence."""

    SCRIPTED_OFFLINE = "scripted-offline"
    AUTOGEN_LIVE = "autogen-live"


class RunBudgets(BaseModel):
    """Bounded research-run budget, enforced by the runtime rather than prompts."""

    model_config = ConfigDict(frozen=True)

    max_model_turns: int = Field(default=12, ge=1, le=100)
    max_tool_calls: int = Field(default=10, ge=1, le=100)
    max_tool_calls_scientist: int = Field(default=4, ge=0, le=100)
    max_tool_calls_engineer: int = Field(default=6, ge=0, le=100)


class ProviderConfig(BaseModel):
    """Non-secret configuration required to construct one approved live provider."""

    model_config = ConfigDict(frozen=True)

    provider: Literal["openai-compatible"] = "openai-compatible"
    model: str = Field(min_length=1, max_length=200)
    api_key_env: str = Field(default="EXPERTSRS_API_KEY", pattern=r"^[A-Z][A-Z0-9_]*$")
    base_url_env: str = Field(default="EXPERTSRS_BASE_URL", pattern=r"^[A-Z][A-Z0-9_]*$")
    timeout_seconds: int = Field(default=120, ge=1, le=3_600)
    temperature: float = Field(default=0, ge=0, le=2)
    top_p: float = Field(default=1, gt=0, le=1)


DEFAULT_RESEARCH_BUDGETS = RunBudgets()


class RuntimeCapabilities(BaseModel):
    """The only switchable mechanism policy used by evaluation conditions."""

    model_config = ConfigDict(frozen=True)

    allow_plan_revision: bool = True
    allow_checkpoint_recovery: bool = True


class ToolBinding(BaseModel):
    """One model-visible tool contract backed by the local runtime.

    ``safe_parameters`` are symbolic, allow-listed values.  The runtime alone
    resolves data paths, output locations and artifact URIs.
    """

    model_config = ConfigDict(frozen=True)

    tool_name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    required_artifact_types: tuple[str, ...] = ()
    safe_parameters: dict[str, Any] = Field(default_factory=dict)


class ManagerClarifyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["clarify"]
    question: str = Field(min_length=1, max_length=1_000)


class ManagerHandoffDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["handoff"]
    target: Literal["Scientist"]


class ScientistPlanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["plan"]
    operation: Literal["ndvi", "greenspace", "lst"]
    next_action: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class ScientistStopDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["stop"]
    reason: str = Field(min_length=1, max_length=1_000)


class EngineerActionDecision(BaseModel):
    """A symbolic request; no local location is accepted from a model."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["action"]
    tool_name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    artifact_refs: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("parameters")
    @classmethod
    def _parameters_must_not_contain_paths(cls, value: dict[str, Any]) -> dict[str, Any]:
        def contains_path(candidate: Any) -> bool:
            if isinstance(candidate, str):
                return candidate.startswith(("/", "\\\\")) or ":\\" in candidate or ":/" in candidate
            if isinstance(candidate, dict):
                return any(contains_path(item) for item in candidate.values())
            if isinstance(candidate, list):
                return any(contains_path(item) for item in candidate)
            return False

        if contains_path(value):
            raise ValueError("action parameters must be symbolic and must not contain paths")
        return value


class EngineerHandoffDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["handoff"]
    target: Literal["Manager"]


class EngineerStopDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["stop"]
    reason: str = Field(min_length=1, max_length=1_000)


class EngineerReviseDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["revise"]
    next_action: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class ReportDecision(BaseModel):
    """Reserved report contract.  Rendering and report control remain WP3 work."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["report"]
    summary: str = Field(min_length=1, max_length=10_000)
    artifact_refs: list[str] = Field(default_factory=list)


class RunRequest(BaseModel):
    """One natural-language remote-sensing request and its local raster inputs."""

    request: str = Field(min_length=1)
    data_paths: list[Path] = Field(default_factory=list)
    output_dir: Path
    run_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
    budgets: RunBudgets = DEFAULT_RESEARCH_BUDGETS
    capabilities: RuntimeCapabilities = RuntimeCapabilities()
    execution_mode: ExecutionMode = ExecutionMode.SCRIPTED_OFFLINE
    provider: ProviderConfig | None = None

    @field_validator("request")
    @classmethod
    def _request_must_have_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def _provider_matches_execution_mode(self) -> "RunRequest":
        if self.execution_mode == ExecutionMode.AUTOGEN_LIVE and self.provider is None:
            raise ValueError("autogen-live requires explicit provider configuration")
        if self.execution_mode == ExecutionMode.SCRIPTED_OFFLINE and self.provider is not None:
            raise ValueError("scripted-offline must not carry live provider configuration")
        return self


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
    execution_mode: ExecutionMode = ExecutionMode.SCRIPTED_OFFLINE
    provider: str | None = None
