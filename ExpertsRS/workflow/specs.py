"""Serializable contracts for remote-sensing tasks, tools, and artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ArtifactType(str, Enum):
    RASTER = "raster"
    INDEX_RASTER = "index_raster"
    MASK_RASTER = "mask_raster"
    METADATA = "metadata"
    MAP = "map"
    REPORT = "report"
    AREA_STATISTICS = "area_statistics"
    AOI = "aoi"
    COMPOSITION_TABLE = "composition_table"


@dataclass(frozen=True)
class ArtifactSpec:
    artifact_id: str
    artifact_type: ArtifactType
    uri: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    producer_node_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["artifact_type"] = self.artifact_type.value
        return data


@dataclass(frozen=True)
class TaskSpec:
    """User intent represented independently of a chat transcript."""

    task_id: str
    goal: str
    expected_outputs: tuple[ArtifactType, ...]
    aoi: str | None = None
    time_range: str | None = None
    constraints: dict[str, Any] = field(default_factory=dict)
    validation_needs: tuple[str, ...] = ()
    unresolved_questions: tuple[str, ...] = ()
    requested_outputs: tuple[str, ...] = ()
    required_metrics: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["expected_outputs"] = [item.value for item in self.expected_outputs]
        return data


@dataclass(frozen=True)
class OperatorSpec:
    """Stable contract for one tool available to the planning runtime."""

    operator_id: str
    tool_name: str
    input_types: dict[str, tuple[ArtifactType, ...]]
    output_type: ArtifactType
    preconditions: tuple[str, ...] = ()
    required_bands: tuple[str, ...] = ()
    required_config: dict[str, tuple[Any, ...]] = field(default_factory=dict)
    failure_modes: tuple[str, ...] = ()
    default_config: dict[str, Any] = field(default_factory=dict)
    cost_hint: str = "local"


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    operator_id: str
    inputs: dict[str, str]
    output_artifact_id: str
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
