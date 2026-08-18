"""Runtime-side hydration of path-free Scientist planning payloads.

The decision contract deliberately carries only logical input artifact IDs.  This
module is the narrow point where the authoritative runtime supplies local input
URIs before applying the existing workflow validator.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .graph import WorkflowGraph
from .specs import ArtifactSpec, ArtifactType, TaskSpec, WorkflowNode


def hydrate_task(payload: dict[str, Any]) -> TaskSpec:
    return TaskSpec(
        task_id=payload["task_id"],
        goal=payload["goal"],
        expected_outputs=tuple(ArtifactType(item) for item in payload["expected_outputs"]),
        constraints=dict(payload.get("constraints", {})),
        requested_outputs=tuple(payload.get("requested_outputs", [])),
        required_metrics=tuple(payload.get("required_metrics", [])),
    )


def hydrate_workflow(
    payload: dict[str, Any],
    catalog: dict[str, Any],
    input_paths: dict[str, str | Path],
) -> WorkflowGraph:
    """Build a domain graph after binding only declared logical input artifacts."""
    graph = WorkflowGraph(payload["workflow_id"])
    for artifact in payload["input_artifacts"]:
        artifact_id = artifact["artifact_id"]
        if artifact_id not in input_paths:
            raise ValueError(f"Plan references undeclared runtime input artifact '{artifact_id}'.")
        graph.add_artifact(ArtifactSpec(
            artifact_id=artifact_id,
            artifact_type=ArtifactType(artifact["artifact_type"]),
            uri=str(Path(input_paths[artifact_id]).resolve()),
        ))
    for node in payload["nodes"]:
        operator = catalog.get(node["operator_id"])
        if operator is None:
            # The validator will report the unknown operator.  A placeholder
            # output type keeps graph construction deterministic.
            output_type = ArtifactType.METADATA
        else:
            output_type = operator.output_type
        graph.add_step(
            WorkflowNode(
                node_id=node["node_id"],
                operator_id=node["operator_id"],
                inputs=dict(node.get("inputs", {})),
                output_artifact_id=node["output_artifact_id"],
                config=dict(node.get("config", {})),
                depends_on=tuple(node.get("depends_on", [])),
            ),
            output_type,
        )
    return graph
