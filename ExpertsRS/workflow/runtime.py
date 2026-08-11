"""Small, framework-independent interfaces for an inspectable agent run.

The names in this module are implementation names, not additional thesis
concepts.  They support plan revision, a process view derived from run facts,
safe restart points, and a minimal permission boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class EventReference:
    """A typed link from one recorded fact to another recorded object."""

    target_id: str
    relation: str

    def __post_init__(self) -> None:
        if not self.target_id or not self.relation:
            raise ValueError("Event references require a target and relation")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PlanVersion:
    """One immutable version of the Scientist's adjustable plan."""

    plan_id: str
    version: int
    goal: str
    stage: str
    next_action: str
    owner: str = "Scientist"
    branch_id: str = "main"
    parent_version_id: str | None = None
    trigger_event_id: str | None = None
    restart_from_checkpoint_id: str | None = None
    status: str = "active"

    def __post_init__(self) -> None:
        if not self.plan_id or self.version < 1:
            raise ValueError("Plan versions require a plan_id and version >= 1")
        if self.version == 1 and self.parent_version_id is not None:
            raise ValueError("The first plan version cannot have a parent")
        if self.version > 1 and (not self.parent_version_id or not self.trigger_event_id):
            raise ValueError("A revised plan requires its parent and triggering event")

    @property
    def object_id(self) -> str:
        return f"{self.plan_id}:v{self.version}"

    def to_dict(self) -> dict[str, Any]:
        return {"object_id": self.object_id, **asdict(self)}


@dataclass(frozen=True)
class Checkpoint:
    """A logical restart point that references already validated artifacts."""

    checkpoint_id: str
    plan_version_id: str
    resume_after_event_id: str
    valid_artifact_ids: tuple[str, ...]
    branch_id: str = "main"
    reason: str = ""

    def __post_init__(self) -> None:
        if not self.checkpoint_id or not self.plan_version_id or not self.resume_after_event_id:
            raise ValueError("Checkpoint identifiers cannot be empty")
        if len(set(self.valid_artifact_ids)) != len(self.valid_artifact_ids):
            raise ValueError("Checkpoint artifact references must be unique")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["valid_artifact_ids"] = list(self.valid_artifact_ids)
        return data


class ToolEffect(str, Enum):
    READ = "read"
    COMPUTE = "compute"
    WRITE_LOCAL_ARTIFACT = "write_local_artifact"
    EXTERNAL = "external"
    IRREVERSIBLE = "irreversible"


class PermissionOutcome(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


@dataclass(frozen=True)
class PermissionRequest:
    request_id: str
    actor: str
    tool_name: str
    effect: ToolEffect
    resource: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["effect"] = self.effect.value
        return data


@dataclass(frozen=True)
class PermissionDecision:
    decision_id: str
    request_id: str
    outcome: PermissionOutcome
    reason: str
    policy_version: str = "ch1-local-v1"

    def to_dict(self) -> dict[str, str]:
        data = asdict(self)
        data["outcome"] = self.outcome.value
        return data


# This table is intentionally explicit and test-checked against the public tool
# registry.  It is an execution boundary, not a claim of enterprise IAM.
TOOL_EFFECTS: dict[str, ToolEffect] = {
    "list_available_data_files": ToolEffect.READ,
    "read_raster_metadata": ToolEffect.READ,
    "read_raster_band": ToolEffect.READ,
    "read_raster_bands": ToolEffect.READ,
    "calculate_area": ToolEffect.COMPUTE,
    "zonal_statistics": ToolEffect.COMPUTE,
    "save_raster": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "calculate_ndvi": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "calculate_evi": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "calculate_ndwi": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "calculate_nbr": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "calculate_lst": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "calculate_msavi": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "apply_threshold": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "apply_mask": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "plot_index_map": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "plot_thematic_map": ToolEffect.WRITE_LOCAL_ARTIFACT,
    "plot_false_color_composite": ToolEffect.WRITE_LOCAL_ARTIFACT,
}


class LocalPermissionPolicy:
    """Default-deny policy for the current local, single-executor prototype."""

    def __init__(
        self,
        read_roots: Iterable[str | Path],
        write_roots: Iterable[str | Path],
        tool_effects: Mapping[str, ToolEffect] | None = None,
        policy_version: str = "ch1-local-v1",
    ) -> None:
        self.read_roots = tuple(Path(root).resolve() for root in read_roots)
        self.write_roots = tuple(Path(root).resolve() for root in write_roots)
        self.tool_effects = dict(tool_effects or TOOL_EFFECTS)
        self.policy_version = policy_version

    @staticmethod
    def _is_within(resource: str | None, roots: tuple[Path, ...]) -> bool:
        if not resource:
            return False
        path = Path(resource).resolve()
        return any(path == root or root in path.parents for root in roots)

    def evaluate(self, request: PermissionRequest) -> PermissionDecision:
        expected_effect = self.tool_effects.get(request.tool_name)
        outcome = PermissionOutcome.DENY
        reason = "tool_not_registered"

        if expected_effect is not None and expected_effect != request.effect:
            reason = "declared_effect_does_not_match_tool"
        elif expected_effect in {ToolEffect.EXTERNAL, ToolEffect.IRREVERSIBLE}:
            reason = "external_or_irreversible_action_not_enabled"
        elif expected_effect == ToolEffect.COMPUTE:
            outcome, reason = PermissionOutcome.ALLOW, "registered_in_memory_computation"
        elif expected_effect == ToolEffect.READ:
            if self._is_within(request.resource, self.read_roots):
                outcome, reason = PermissionOutcome.ALLOW, "resource_within_allowed_read_roots"
            else:
                reason = "resource_outside_allowed_read_roots"
        elif expected_effect == ToolEffect.WRITE_LOCAL_ARTIFACT:
            if self._is_within(request.resource, self.write_roots):
                outcome, reason = PermissionOutcome.ALLOW, "resource_within_allowed_write_roots"
            else:
                reason = "resource_outside_allowed_write_roots"

        return PermissionDecision(
            decision_id=f"{request.request_id}:decision",
            request_id=request.request_id,
            outcome=outcome,
            reason=reason,
            policy_version=self.policy_version,
        )


@dataclass(frozen=True)
class ProcessNode:
    node_id: str
    event_id: str
    sequence_no: int
    kind: str
    actor: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessEdge:
    source: str
    target: str
    relation: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ProcessGraphView:
    """A deterministic, compact view derived only from recorded run facts."""

    run_id: str
    nodes: tuple[ProcessNode, ...]
    edges: tuple[ProcessEdge, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


def build_process_graph(run_id: str, events: Iterable[Mapping[str, Any]]) -> ProcessGraphView:
    """Build the same process view whenever the same ordered facts are supplied."""

    nodes: list[ProcessNode] = []
    aliases: dict[str, str] = {}
    source_events = list(events)

    for fallback_sequence, event in enumerate(source_events, start=1):
        sequence_no = int(event.get("sequence_no", fallback_sequence))
        event_id = str(event.get("event_id", f"{run_id}:legacy:{sequence_no:04d}"))
        node_id = str(event.get("object_id") or event_id)
        if node_id in {node.node_id for node in nodes}:
            raise ValueError(f"Duplicate process object: {node_id}")
        if event_id in aliases:
            raise ValueError(f"Duplicate event id: {event_id}")
        nodes.append(ProcessNode(
            node_id=node_id,
            event_id=event_id,
            sequence_no=sequence_no,
            kind=str(event["event_type"]),
            actor=str(event.get("actor", "Runtime")),
            payload=dict(event.get("payload", {})),
        ))
        aliases[event_id] = node_id
        aliases[node_id] = node_id

    edges: list[ProcessEdge] = []
    for previous, current in zip(nodes, nodes[1:]):
        edges.append(ProcessEdge(previous.node_id, current.node_id, "next_event"))

    for event, current in zip(source_events, nodes):
        for reference in event.get("references", []):
            target_id = str(reference["target_id"])
            if target_id not in aliases:
                raise ValueError(f"Unknown process reference: {target_id}")
            edges.append(ProcessEdge(
                aliases[target_id],
                current.node_id,
                str(reference["relation"]),
            ))

    return ProcessGraphView(run_id, tuple(nodes), tuple(edges))
