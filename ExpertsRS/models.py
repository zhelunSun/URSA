"""Stable JSON contracts for the authoritative ExpertsRS runtime."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RunStatus(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
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
    max_wall_time_seconds: int = Field(default=300, ge=1, le=3_600)
    max_total_tokens_recorded: int = Field(default=18_000, ge=1, le=1_000_000)


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
    max_completion_tokens: int = Field(default=6_000, ge=1, le=100_000)
    max_retries: Literal[0] = 0
    cache_enabled: Literal[False] = False
    enable_thinking: bool | None = None


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


class PlannedArtifactDecision(BaseModel):
    """A model-visible logical artifact.  URIs are runtime-only facts."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(pattern=r"^[a-z][a-z0-9_:-]*$")
    artifact_type: Literal[
        "raster", "index_raster", "mask_raster", "metadata", "map", "report", "area_statistics", "aoi", "composition_table",
    ]


class PlannedNodeDecision(BaseModel):
    """One symbolic node in the Scientist's workflow proposal."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(pattern=r"^[a-z][a-z0-9_:-]*$")
    operator_id: str = Field(pattern=r"^expertsrs\.[a-z][a-z0-9_]*\.v1$")
    inputs: dict[str, str] = Field(default_factory=dict)
    output_artifact_id: str = Field(pattern=r"^[a-z][a-z0-9_:-]*$")
    config: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class TaskSpecDecision(BaseModel):
    """Serializable, path-free TaskSpec accepted at the model boundary."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(pattern=r"^[a-z][a-z0-9_:-]*$")
    goal: str = Field(min_length=1, max_length=2_000)
    expected_outputs: list[Literal[
        "raster", "index_raster", "mask_raster", "metadata", "map", "report", "area_statistics", "aoi", "composition_table",
    ]] = Field(min_length=1)
    requested_outputs: list[str] = Field(default_factory=list)
    required_metrics: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class WorkflowGraphDecision(BaseModel):
    """Path-free graph payload; runtime hydrates only its declared input IDs."""

    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(pattern=r"^[a-z][a-z0-9_:-]*$")
    input_artifacts: list[PlannedArtifactDecision] = Field(min_length=1)
    nodes: list[PlannedNodeDecision] = Field(min_length=1)


class ScientistPlanDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["plan"]
    task: TaskSpecDecision
    workflow: WorkflowGraphDecision


class ScientistReviseDecision(BaseModel):
    """A full replacement graph constrained to a local, observed-failure patch."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["revise"]
    reason: str = Field(min_length=1, max_length=1_000)
    base_plan_id: str = Field(min_length=1)
    affected_node_ids: list[str] = Field(min_length=1)
    task: TaskSpecDecision
    workflow: WorkflowGraphDecision


class ScientistStopDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["stop"]
    reason: str = Field(min_length=1, max_length=1_000)


class EngineerActionDecision(BaseModel):
    """A symbolic request; no local location is accepted from a model."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["action"]
    node_id: str = Field(pattern=r"^[a-z][a-z0-9_:-]*$")


class EngineerHandoffDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["handoff"]
    target: Literal["Manager"]


class EngineerStopDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["stop"]
    reason: str = Field(min_length=1, max_length=1_000)


class ReportDeliverableDecision(BaseModel):
    """A user-facing output backed by a validated artifact or observation."""

    model_config = ConfigDict(extra="forbid")

    deliverable_id: str = Field(pattern=r"^[a-z][a-z0-9_:-]*$")
    status: Literal["delivered", "partial", "unavailable"]
    value: float | int | str | None = None
    unit: str | None = Field(default=None, max_length=100)
    scope: str | None = Field(default=None, max_length=1_000)
    artifact_refs: list[str] = Field(default_factory=list)


class ReportDecision(BaseModel):
    """Reserved report contract.  Rendering and report control remain WP3 work."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["report"]
    summary: str = Field(min_length=1, max_length=10_000)
    artifact_refs: list[str] = Field(default_factory=list)
    deliverables: list[ReportDeliverableDecision] = Field(default_factory=list)


class InputResource(BaseModel):
    """Caller-owned resource binding; paths and byte identities stay runtime-side."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    path: Path
    artifact_type: Literal["raster", "aoi"]
    sha256: str | None = Field(default=None, pattern=r"^[A-Fa-f0-9]{64}$")


class RunRequest(BaseModel):
    """One natural-language remote-sensing request and its local raster inputs."""

    request: str = Field(min_length=1)
    data_paths: list[Path] = Field(default_factory=list)
    input_resources: dict[str, InputResource] = Field(default_factory=dict)
    domain_profile: Literal["legacy", "classification-v1"] = "legacy"
    classification_admission: Literal["ch3-k0-dev-v1"] | None = None
    product_year: int = Field(default=2025, ge=1900, le=2100)
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
        if self.domain_profile == "classification-v1":
            if self.execution_mode != ExecutionMode.SCRIPTED_OFFLINE and self.classification_admission != "ch3-k0-dev-v1":
                raise ValueError("classification-v1 is an offline engineering profile unless the explicit K0 development contract is selected")
            valid_resources = ("classification" in self.input_resources and set(self.input_resources) <= {"classification", "study_area"}) if self.classification_admission else set(self.input_resources) == {"classification", "study_area"}
            if self.data_paths or not valid_resources:
                raise ValueError("classification-v1 requires exactly classification and study_area resources, without data_paths")
            if self.input_resources["classification"].artifact_type != "raster" or ("study_area" in self.input_resources and self.input_resources["study_area"].artifact_type != "aoi"):
                raise ValueError("Classification must be raster and study_area must be aoi")
        elif self.input_resources:
            raise ValueError("Explicit input_resources require classification-v1; legacy data_paths remain unchanged")
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
    producer_plan_node_id: str | None = None
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
