"""Conservative, deterministic repair that never rewrites unaffected nodes."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .graph import WorkflowGraph
from .specs import ArtifactType, OperatorSpec, WorkflowNode
from .validator import ValidationReport, ViolationCode


@dataclass(frozen=True)
class RepairDecision:
    status: str  # repaired | stopped | no_action
    reason: str
    added_node_ids: tuple[str, ...] = ()
    unresolved_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def apply_targeted_repair(
    graph: WorkflowGraph, report: ValidationReport, catalog: dict[str, OperatorSpec]
) -> RepairDecision:
    """Add one missing-output step when its inputs are unambiguous; otherwise stop.

    The method is intentionally narrow: it demonstrates repair provenance and
    unaffected-subgraph preservation without allowing hidden LLM rewrites.
    """
    missing = [item for item in report.violations if item.code == ViolationCode.MISSING_EXPECTED_OUTPUT]
    blocking = [item for item in report.violations if item.code != ViolationCode.MISSING_EXPECTED_OUTPUT]
    if blocking:
        return RepairDecision("stopped", "Existing contract violations require planner or user input.",
                              unresolved_codes=tuple(sorted({item.code.value for item in blocking})))
    if len(missing) != 1:
        return RepairDecision("stopped", "Repair supports exactly one missing expected output at a time.",
                              unresolved_codes=tuple(item.code.value for item in missing))

    target = ArtifactType(missing[0].details["expected_output"])
    candidates: list[tuple[OperatorSpec, dict[str, str]]] = []
    for operator in catalog.values():
        if operator.output_type != target:
            continue
        inputs: dict[str, str] = {}
        for parameter, types in operator.input_types.items():
            artifact = next((item for item in reversed(list(graph.artifacts.values())) if item.artifact_type in types), None)
            if artifact is None:
                break
            inputs[parameter] = artifact.artifact_id
        else:
            candidates.append((operator, inputs))

    if len(candidates) != 1:
        return RepairDecision("stopped", "No unique safe repair exists for the missing output.",
                              unresolved_codes=(ViolationCode.MISSING_EXPECTED_OUTPUT.value,))

    operator, inputs = candidates[0]
    node_id = f"repair_{len(graph.nodes) + 1:03d}_{operator.tool_name}"
    output_id = f"{node_id}_output"
    graph.add_step(WorkflowNode(node_id, operator.operator_id, inputs, output_id, operator.default_config), target)
    return RepairDecision("repaired", f"Added '{operator.tool_name}' only for the missing '{target.value}' output.", (node_id,))
