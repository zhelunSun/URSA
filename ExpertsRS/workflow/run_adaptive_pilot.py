"""No-API D2 pilot: real feedback, one local recovery, and one denied action.

This is a mechanism fixture.  The deliberately invalid band label is fault
injection, not an example of scientific planning and not an accuracy test.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.index_kit import calculate_ndvi
from tools.io_kit import read_raster_metadata

from .runtime import (
    Checkpoint,
    LocalPermissionPolicy,
    PermissionOutcome,
    PermissionRequest,
    PlanVersion,
    ToolEffect,
    build_process_graph,
)
from .trace import WorkflowTrace


def _require_allowed(trace: WorkflowTrace, policy: LocalPermissionPolicy, request: PermissionRequest):
    decision = policy.evaluate(request)
    trace.record_permission(request, decision)
    if decision.outcome != PermissionOutcome.ALLOW:
        raise RuntimeError(f"Fixture action was unexpectedly denied: {decision.reason}")
    return decision


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data")
    compact_data = data
    if isinstance(data, dict):
        compact_data = {
            key: value for key, value in data.items()
            if key in {"output_path", "shape", "min", "max", "mean", "std", "band_descriptions"}
        }
    return {
        "message": result.get("message"),
        "error_code": result.get("error_code"),
        "data": compact_data,
    }


def generate_adaptive_evidence(output_dir: str | Path) -> dict[str, Path]:
    root = Path(__file__).resolve().parents[1]
    source = root / "data" / "Sentinel2_Dongcheng_20230718.tif"
    results = root / "results"
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("ch1_d2_adaptive_%Y%m%d%H%M%S")

    trace = WorkflowTrace(run_id)
    policy = LocalPermissionPolicy([root / "data"], [results])
    plan_v1 = PlanVersion(
        "greenspace-plan", 1, "produce an NDVI artifact from the supplied scene",
        "inspect", "read metadata, then execute the proposed band selection",
    )
    trace.record_plan_version(plan_v1)

    read_request = PermissionRequest(
        "permission-read-metadata", "Scientist", "read_raster_metadata",
        ToolEffect.READ, str(source),
    )
    read_decision = _require_allowed(trace, policy, read_request)
    trace.record_action(
        "action-read-metadata", "Scientist", read_request.tool_name,
        {"file_path": str(source)}, plan_v1.object_id, read_decision.decision_id,
    )
    metadata = read_raster_metadata(str(source))
    metadata_observation = trace.record_observation(
        "observation-metadata", "Executor", "action-read-metadata",
        bool(metadata.get("success")), _compact_result(metadata),
    )
    if not metadata.get("success"):
        raise RuntimeError(metadata.get("message", "metadata inspection failed"))
    trace.record_artifact(
        "artifact-metadata", "Executor", "action-read-metadata",
        "memory://verified-scene-metadata", True,
    )
    trace.record_checkpoint(Checkpoint(
        "checkpoint-after-metadata", plan_v1.object_id, metadata_observation,
        ("artifact-metadata",), reason="scene metadata was read successfully",
    ))

    # Fault injection: B99 is deliberately absent.  The real tool must report
    # the failed scientific precondition without creating an output artifact.
    failure_request = PermissionRequest(
        "permission-invalid-ndvi", "Engineer", "calculate_ndvi",
        ToolEffect.WRITE_LOCAL_ARTIFACT, str(results),
    )
    failure_decision = _require_allowed(trace, policy, failure_request)
    trace.record_action(
        "action-invalid-band", "Engineer", failure_request.tool_name,
        {"file_path": str(source), "nir_band": "B99", "red_band": "B4"},
        plan_v1.object_id, failure_decision.decision_id,
    )
    failure = calculate_ndvi(str(source), nir_band="B99", red_band="B4")
    failure_observation = trace.record_observation(
        "observation-invalid-band", "Executor", "action-invalid-band",
        bool(failure.get("success")), _compact_result(failure),
    )
    if failure.get("success"):
        raise RuntimeError("Fault injection unexpectedly succeeded")

    plan_v2 = PlanVersion(
        "greenspace-plan", 2, plan_v1.goal, "recover",
        "reuse verified metadata and select B8/B4 by semantic description",
        branch_id="retry-semantic-bands", parent_version_id=plan_v1.object_id,
        trigger_event_id=failure_observation,
        restart_from_checkpoint_id="checkpoint-after-metadata",
    )
    trace.record_plan_version(plan_v2)

    retry_request = PermissionRequest(
        "permission-retry-ndvi", "Engineer", "calculate_ndvi",
        ToolEffect.WRITE_LOCAL_ARTIFACT, str(results),
    )
    retry_decision = _require_allowed(trace, policy, retry_request)
    retry_action_event = trace.record_action(
        "action-retry-semantic-bands", "Engineer", retry_request.tool_name,
        {"file_path": str(source), "nir_band": "B8", "red_band": "B4"},
        plan_v2.object_id, retry_decision.decision_id,
        branch_id=plan_v2.branch_id,
    )
    retry = calculate_ndvi(str(source), nir_band="B8", red_band="B4")
    retry_observation = trace.record_observation(
        "observation-retry", "Executor", "action-retry-semantic-bands",
        bool(retry.get("success")), _compact_result(retry),
    )
    if not retry.get("success"):
        raise RuntimeError(retry.get("message", "valid retry failed"))
    output_path = str(retry["data"]["output_path"])
    trace.record_artifact(
        "artifact-ndvi", "Executor", "action-retry-semantic-bands", output_path, True
    )
    trace.record_checkpoint(Checkpoint(
        "checkpoint-after-retry", plan_v2.object_id, retry_observation,
        ("artifact-metadata", "artifact-ndvi"), branch_id=plan_v2.branch_id,
        reason="retry completed and both artifacts remain valid",
    ))

    denied_request = PermissionRequest(
        "permission-outside-results", "Engineer", "calculate_ndvi",
        ToolEffect.WRITE_LOCAL_ARTIFACT, str(root.parent / "outside-results" / "ndvi.tif"),
    )
    denied_decision = policy.evaluate(denied_request)
    trace.record_permission(denied_request, denied_decision)
    if denied_decision.outcome != PermissionOutcome.DENY:
        raise RuntimeError("Out-of-root write was not denied")

    trace.record_final_status("completed_after_local_recovery", ["artifact-ndvi"])
    trace_path = trace.write(destination / "adaptive_recovery_trace.json")
    graph = build_process_graph(trace.run_id, trace.events)
    graph_path = destination / "adaptive_process_graph.json"
    graph_path.write_text(json.dumps(graph.to_dict(), indent=2), encoding="utf-8")

    summary = {
        "run_id": run_id,
        "purpose": "Chapter 1 mechanism fixture; not a scientific accuracy evaluation",
        "fault_injection": "B99 was deliberately supplied as a missing band label",
        "failure_observed": not failure["success"],
        "revised_plan": plan_v2.object_id,
        "reused_artifacts": ["artifact-metadata"],
        "retry_succeeded": retry["success"],
        "denied_action": denied_decision.to_dict(),
        "output_artifact": output_path,
        "event_count": len(trace.events),
        "process_node_count": len(graph.nodes),
        "process_edge_count": len(graph.edges),
    }
    summary_path = destination / "adaptive_pilot_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {"trace": trace_path, "graph": graph_path, "summary": summary_path}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = generate_adaptive_evidence(root / "results" / "ch1_d2_closeout")
    print("D2 adaptive no-API pilot: PASS")
    for label, path in paths.items():
        print(f"  {label}: {path}")


if __name__ == "__main__":
    main()
