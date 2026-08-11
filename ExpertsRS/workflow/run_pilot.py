"""Run a deterministic planning/validation/repair pilot over the local Sentinel-2 scene."""

import sys
from pathlib import Path

# Supports ``python workflow/run_pilot.py`` from the preserved ExpertsRS surface.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow import ArtifactSpec, ArtifactType, TaskSpec, WorkflowGraph, WorkflowNode
from workflow import WorkflowTrace, apply_targeted_repair, build_operator_catalog, validate_workflow


def main() -> None:
    root = ROOT
    source_path = root / "data" / "Sentinel2_Dongcheng_20230718.tif"
    catalog = build_operator_catalog()
    task = TaskSpec("greenspace-pilot", "Create a greenspace mask from Sentinel-2 imagery.", (ArtifactType.MASK_RASTER,), aoi="Dongcheng, Beijing", time_range="2023-07-18")
    graph = WorkflowGraph("greenspace-pilot-workflow")
    graph.add_artifact(ArtifactSpec("sentinel_scene", ArtifactType.RASTER, str(source_path)))
    graph.add_step(WorkflowNode("compute_ndvi", "expertsrs.calculate_ndvi.v1", {"file_path": "sentinel_scene"}, "ndvi"), ArtifactType.INDEX_RASTER)

    trace = WorkflowTrace("greenspace-pilot-run")
    trace.record_plan(task, graph)
    before = validate_workflow(task, graph, catalog)
    trace.record_validation(before)
    decision = apply_targeted_repair(graph, before, catalog)
    trace.record_repair(decision, graph)
    after = validate_workflow(task, graph, catalog)
    trace.record_validation(after)
    status = "validated" if after.valid else "stopped"
    trace.record_final_status(status, list(graph.artifacts))
    output = trace.write(root / "results" / "workflow_trace_greenspace_pilot.json")
    print(f"Pilot status: {status}; trace: {output}")
    if not after.valid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
