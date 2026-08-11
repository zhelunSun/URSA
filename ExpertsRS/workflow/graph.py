"""An explicit dependency graph, kept deliberately framework-independent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .specs import ArtifactSpec, ArtifactType, WorkflowNode


@dataclass
class WorkflowGraph:
    workflow_id: str
    artifacts: dict[str, ArtifactSpec] = field(default_factory=dict)
    nodes: list[WorkflowNode] = field(default_factory=list)

    def add_artifact(self, artifact: ArtifactSpec) -> None:
        if artifact.artifact_id in self.artifacts:
            raise ValueError(f"Artifact already exists: {artifact.artifact_id}")
        self.artifacts[artifact.artifact_id] = artifact

    def add_step(self, node: WorkflowNode, output_type: ArtifactType) -> None:
        if any(existing.node_id == node.node_id for existing in self.nodes):
            raise ValueError(f"Node already exists: {node.node_id}")
        if node.output_artifact_id in self.artifacts:
            raise ValueError(f"Output artifact already exists: {node.output_artifact_id}")
        self.nodes.append(node)
        self.artifacts[node.output_artifact_id] = ArtifactSpec(
            artifact_id=node.output_artifact_id,
            artifact_type=output_type,
            producer_node_id=node.node_id,
        )

    def produced_types(self) -> set[ArtifactType]:
        return {
            artifact.artifact_type
            for artifact in self.artifacts.values()
            if artifact.producer_node_id is not None
        }

    def find_artifact(self, artifact_type: ArtifactType) -> ArtifactSpec | None:
        for artifact in reversed(list(self.artifacts.values())):
            if artifact.artifact_type == artifact_type:
                return artifact
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts.values()],
            "nodes": [node.to_dict() for node in self.nodes],
        }
