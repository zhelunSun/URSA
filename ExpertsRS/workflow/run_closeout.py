"""Generate the deterministic repair and controlled-stop evidence for M1."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Supports ``python workflow/run_closeout.py`` from the preserved ExpertsRS surface.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from workflow import ArtifactSpec, ArtifactType, TaskSpec, WorkflowGraph, WorkflowNode
from workflow import WorkflowTrace, apply_targeted_repair, build_operator_catalog, validate_workflow


def _run_case(
    *,
    run_id: str,
    task: TaskSpec,
    graph: WorkflowGraph,
    output_path: Path,
) -> tuple[Path, str, bool]:
    catalog = build_operator_catalog()
    trace = WorkflowTrace(run_id)
    trace.record_plan(task, graph)
    before = validate_workflow(task, graph, catalog)
    trace.record_validation(before)
    decision = apply_targeted_repair(graph, before, catalog)
    trace.record_repair(decision, graph)
    after = validate_workflow(task, graph, catalog)
    trace.record_validation(after)
    final_status = "validated_after_repair" if decision.status == "repaired" and after.valid else "controlled_stop"
    trace.record_final_status(final_status, list(graph.artifacts))
    return trace.write(output_path), decision.status, after.valid


def generate_closeout_evidence(output_dir: str | Path) -> dict[str, Path]:
    """Write one successful repair trace and one expected controlled-stop trace."""
    output_dir = Path(output_dir)
    source_path = ROOT / "data" / "Sentinel2_Dongcheng_20230718.tif"

    repair_graph = WorkflowGraph("ch1-m1-repair-workflow")
    repair_graph.add_artifact(ArtifactSpec("sentinel_scene", ArtifactType.RASTER, str(source_path)))
    repair_graph.add_step(
        WorkflowNode(
            "compute_ndvi",
            "expertsrs.calculate_ndvi.v1",
            {"file_path": "sentinel_scene"},
            "ndvi",
        ),
        ArtifactType.INDEX_RASTER,
    )
    repair_path, repair_decision, repair_valid = _run_case(
        run_id="ch1-m1-repair",
        task=TaskSpec(
            "ch1-m1-repair-task",
            "Create a greenspace mask from Sentinel-2 imagery.",
            (ArtifactType.MASK_RASTER,),
            aoi="Dongcheng, Beijing",
            time_range="2023-07-18",
        ),
        graph=repair_graph,
        output_path=output_dir / "repair_trace.json",
    )

    stop_graph = WorkflowGraph("ch1-m1-controlled-stop-workflow")
    stop_graph.add_artifact(ArtifactSpec("sentinel_scene", ArtifactType.RASTER, str(source_path)))
    stop_graph.add_step(
        WorkflowNode(
            "invalid_sentinel2_lst",
            "expertsrs.calculate_lst.v1",
            {"file_path": "sentinel_scene"},
            "lst",
            {
                "sensor": "landsat-8",
                "input_unit": "toa_radiance_w_m2_sr_um",
            },
        ),
        ArtifactType.INDEX_RASTER,
    )
    stop_path, stop_decision, stop_valid = _run_case(
        run_id="ch1-m1-controlled-stop",
        task=TaskSpec(
            "ch1-m1-controlled-stop-task",
            "Derive land-surface temperature from the Sentinel-2 scene.",
            (ArtifactType.INDEX_RASTER,),
            validation_needs=("thermal-band and radiometric-unit preconditions",),
        ),
        graph=stop_graph,
        output_path=output_dir / "controlled_stop_trace.json",
    )

    if not (repair_decision == "repaired" and repair_valid):
        raise RuntimeError("Repair evidence did not reach a valid post-repair workflow.")
    if not (stop_decision == "stopped" and not stop_valid):
        raise RuntimeError("Controlled-stop evidence did not preserve the unsupported violation.")

    return {"repair": repair_path, "controlled_stop": stop_path}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "ch1_m1_closeout",
        help="Directory for the two JSON traces.",
    )
    args = parser.parse_args()
    paths = generate_closeout_evidence(args.output_dir)
    print("M1 deterministic closeout evidence: PASS")
    print(f"  repair:          {paths['repair']}")
    print(f"  controlled stop: {paths['controlled_stop']}")


if __name__ == "__main__":
    main()
