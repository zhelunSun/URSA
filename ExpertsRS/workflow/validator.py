"""Deterministic pre-execution validation of a planned workflow graph."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from enum import Enum

import rasterio

from .graph import WorkflowGraph
from .specs import ArtifactType, OperatorSpec, TaskSpec


class ViolationCode(str, Enum):
    UNKNOWN_OPERATOR = "unknown_operator"
    MISSING_INPUT = "missing_input"
    UNKNOWN_ARTIFACT = "unknown_artifact"
    TYPE_MISMATCH = "type_mismatch"
    INVALID_ORDER = "invalid_order"
    PRECONDITION_FAILED = "precondition_failed"
    MISSING_REQUIRED_BAND = "missing_required_band"
    INVALID_CONFIG = "invalid_config"
    OUTPUT_TYPE_MISMATCH = "output_type_mismatch"
    MISSING_EXPECTED_OUTPUT = "missing_expected_output"
    UNKNOWN_DEPENDENCY = "unknown_dependency"
    CYCLIC_DEPENDENCY = "cyclic_dependency"


@dataclass(frozen=True)
class Violation:
    code: ViolationCode
    node_id: str | None
    message: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        value = asdict(self)
        value["code"] = self.code.value
        return value


@dataclass
class ValidationReport:
    workflow_id: str
    violations: list[Violation]

    @property
    def valid(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict:
        return {"workflow_id": self.workflow_id, "valid": self.valid,
                "violations": [violation.to_dict() for violation in self.violations]}


def validate_workflow(
    task: TaskSpec, graph: WorkflowGraph, catalog: dict[str, OperatorSpec]
) -> ValidationReport:
    """Validate types, dependencies, local-file preconditions, and task outputs."""
    violations: list[Violation] = []
    node_positions = {node.node_id: index for index, node in enumerate(graph.nodes)}

    for position, node in enumerate(graph.nodes):
        operator = catalog.get(node.operator_id)
        if operator is None:
            violations.append(Violation(ViolationCode.UNKNOWN_OPERATOR, node.node_id,
                f"No contract exists for operator '{node.operator_id}'."))
            continue

        for dependency_id in node.depends_on:
            dependency_position = node_positions.get(dependency_id)
            if dependency_position is None:
                violations.append(Violation(
                    ViolationCode.UNKNOWN_DEPENDENCY, node.node_id,
                    f"Node '{node.node_id}' depends on unknown node '{dependency_id}'.",
                    {"dependency_id": dependency_id},
                ))
            elif dependency_position >= position:
                violations.append(Violation(
                    ViolationCode.INVALID_ORDER, node.node_id,
                    f"Node '{node.node_id}' must depend only on an earlier node.",
                    {"dependency_id": dependency_id},
                ))

        output_artifact = graph.artifacts.get(node.output_artifact_id)
        if output_artifact is None or output_artifact.artifact_type != operator.output_type:
            actual = output_artifact.artifact_type.value if output_artifact else None
            violations.append(Violation(
                ViolationCode.OUTPUT_TYPE_MISMATCH,
                node.node_id,
                f"Operator '{operator.tool_name}' produces '{operator.output_type.value}', "
                f"but the graph declares '{actual}'.",
                {"expected": operator.output_type.value, "actual": actual},
            ))

        effective_config = {**operator.default_config, **node.config}
        for config_name, accepted_values in operator.required_config.items():
            if config_name not in effective_config:
                violations.append(Violation(
                    ViolationCode.INVALID_CONFIG,
                    node.node_id,
                    f"Required configuration '{config_name}' is missing for '{operator.tool_name}'.",
                    {"parameter": config_name, "accepted_values": list(accepted_values)},
                ))
            elif accepted_values and effective_config[config_name] not in accepted_values:
                violations.append(Violation(
                    ViolationCode.INVALID_CONFIG,
                    node.node_id,
                    f"Configuration '{config_name}'={effective_config[config_name]!r} is not "
                    f"scientifically admitted for '{operator.tool_name}'.",
                    {"parameter": config_name, "accepted_values": list(accepted_values)},
                ))

        for parameter, accepted_types in operator.input_types.items():
            artifact_id = node.inputs.get(parameter)
            if artifact_id is None:
                violations.append(Violation(ViolationCode.MISSING_INPUT, node.node_id,
                    f"Required input '{parameter}' is not connected.", {"parameter": parameter}))
                continue
            artifact = graph.artifacts.get(artifact_id)
            if artifact is None:
                violations.append(Violation(ViolationCode.UNKNOWN_ARTIFACT, node.node_id,
                    f"Input '{parameter}' references missing artifact '{artifact_id}'.", {"artifact_id": artifact_id}))
                continue
            if artifact.artifact_type not in accepted_types:
                violations.append(Violation(ViolationCode.TYPE_MISMATCH, node.node_id,
                    f"Input '{parameter}' expects {[item.value for item in accepted_types]}, got '{artifact.artifact_type.value}'.",
                    {"artifact_id": artifact_id, "parameter": parameter}))
            if artifact.producer_node_id and node_positions.get(artifact.producer_node_id, -1) >= position:
                violations.append(Violation(ViolationCode.INVALID_ORDER, node.node_id,
                    f"Input artifact '{artifact_id}' is produced after its consumer.", {"artifact_id": artifact_id}))
            if "file_exists" in operator.preconditions:
                if artifact.uri is None and artifact.producer_node_id is None:
                    violations.append(Violation(
                        ViolationCode.PRECONDITION_FAILED, node.node_id,
                        f"Raw input artifact '{artifact_id}' has no file URI.",
                        {"artifact_id": artifact_id, "uri": None},
                    ))
                elif artifact.uri and not os.path.exists(artifact.uri):
                    violations.append(Violation(ViolationCode.PRECONDITION_FAILED, node.node_id,
                        f"Input file does not exist: {artifact.uri}", {"artifact_id": artifact_id, "uri": artifact.uri}))

        if operator.required_bands:
            source_id = node.inputs.get("file_path")
            source = graph.artifacts.get(source_id) if source_id else None
            if source is None or not source.uri:
                violations.append(Violation(
                    ViolationCode.MISSING_REQUIRED_BAND,
                    node.node_id,
                    f"Cannot verify required bands {list(operator.required_bands)} without a source raster URI.",
                    {"required_bands": list(operator.required_bands), "artifact_id": source_id},
                ))
            elif os.path.exists(source.uri):
                try:
                    with rasterio.open(source.uri) as dataset:
                        available = {
                            description.strip().upper()
                            for description in dataset.descriptions
                            if description and description.strip()
                        }
                    missing = [band for band in operator.required_bands if band.upper() not in available]
                    if missing:
                        violations.append(Violation(
                            ViolationCode.MISSING_REQUIRED_BAND,
                            node.node_id,
                            f"Required semantic bands {missing} are absent from '{source.artifact_id}'.",
                            {
                                "artifact_id": source.artifact_id,
                                "required_bands": list(operator.required_bands),
                                "missing_bands": missing,
                                "available_bands": sorted(available),
                            },
                        ))
                except Exception as error:
                    violations.append(Violation(
                        ViolationCode.PRECONDITION_FAILED,
                        node.node_id,
                        f"Could not inspect raster band semantics: {error}",
                        {"artifact_id": source.artifact_id, "uri": source.uri},
                    ))

    produced = graph.produced_types()
    for expected in task.expected_outputs:
        if expected not in produced:
            violations.append(Violation(ViolationCode.MISSING_EXPECTED_OUTPUT, None,
                f"Task requires '{expected.value}', but no workflow artifact produces it.",
                {"expected_output": expected.value}))

    dependencies = {node.node_id: graph.predecessor_ids(node) for node in graph.nodes}
    visited: set[str] = set()
    active: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in active:
            violations.append(Violation(
                ViolationCode.CYCLIC_DEPENDENCY, node_id,
                f"Workflow contains a dependency cycle at '{node_id}'.",
            ))
            return
        if node_id in visited:
            return
        visited.add(node_id)
        active.add(node_id)
        for parent in dependencies.get(node_id, set()):
            if parent in dependencies:
                visit(parent)
        active.remove(node_id)

    for node_id in dependencies:
        visit(node_id)
    return ValidationReport(graph.workflow_id, violations)
