"""Deterministic task templates built on the ExpertsRS runtime."""

from __future__ import annotations

from pathlib import Path

from .artifacts import RunArtifactStore
from .evaluator import RuntimeEvaluator
from .state import RunState
from .tool_runtime import ToolRuntime
from .workflow import RuntimeWorkflow


def vegetation_mapping_ndvi_threshold(
    user_request: str = "Map vegetation using NDVI thresholding.",
    aoi: str = "local raster extent",
    time_period: str = "local raster acquisition period",
    threshold: float = 0.3,
    artifact_base_dir: str | Path | None = None,
) -> RuntimeWorkflow:
    """Run the first formal RS task template without LLM orchestration."""

    state = RunState(user_request=user_request)
    workflow = RuntimeWorkflow(
        state=state,
        tool_runtime=ToolRuntime(),
        artifact_store=RunArtifactStore(base_dir=artifact_base_dir),
        evaluator=RuntimeEvaluator(),
    )
    workflow.initialize_request(user_request)
    workflow.set_structured_request(
        aoi=aoi,
        time_period=time_period,
        resolution="source raster resolution",
        output="vegetation mask, vegetation area, thematic map, and runtime report",
    )
    workflow.set_method_plan(
        {
            "template": "vegetation_mapping_ndvi_threshold",
            "dataset": "auto-discovered local multispectral raster",
            "method": "NDVI thresholding",
            "threshold": threshold,
            "tool_sequence": [
                "list_available_data_files",
                "read_raster_metadata",
                "calculate_ndvi",
                "apply_threshold",
                "calculate_area",
                "plot_thematic_map",
            ],
        },
        assumptions=[
            "Band indexes follow Sentinel-2 conventions unless the user overrides them.",
            "A single local raster can stand in for external data retrieval during runtime smoke tests.",
        ],
    )
    workflow.approve_plan("approved by deterministic task template")

    data_result = workflow.discover_data()
    if not data_result.get("success") or not data_result.get("data", {}).get("abs_paths"):
        state.add_error("vegetation_mapping_ndvi_threshold", "No local raster data available for task template.")
        workflow.evaluate()
        workflow.write_report_stub("# Vegetation Mapping Runtime Report\n\nNo local raster data was available.")
        return workflow

    source_path = data_result["data"]["abs_paths"][0]
    metadata = workflow.tools.call(state, "read_raster_metadata", file_path=source_path)
    ndvi = workflow.tools.call(state, "calculate_ndvi", file_path=source_path)
    ndvi_path = ndvi["data"]["output_path"] if ndvi.get("success") else None

    mask_path = None
    area = None
    map_result = None
    if ndvi_path:
        mask = workflow.tools.call(
            state,
            "apply_threshold",
            file_path=ndvi_path,
            threshold_low=threshold,
            output_name="vegetation",
        )
        mask_path = mask["data"]["output_path"] if mask.get("success") else None
    if mask_path:
        area = workflow.tools.call(state, "calculate_area", file_path=mask_path)
        map_result = workflow.tools.call(
            state,
            "plot_thematic_map",
            file_path=mask_path,
            class_labels={0: "Non-vegetation", 1: "Vegetation"},
            output_name="vegetation_mask",
            title="Vegetation Mask from NDVI Threshold",
        )

    evaluation = workflow.evaluate()
    area_text = ""
    if area and area.get("success"):
        hectares = area.get("data", {}).get("areas_hectares", {})
        area_text = f"\n- Area statistics: {hectares}"
    map_text = ""
    if map_result and map_result.get("success"):
        map_text = f"\n- Thematic map: {map_result['data']['output_path']}"
    metadata_text = ""
    if metadata and metadata.get("success"):
        metadata_text = f"\n- Source raster: {metadata['data'].get('file_name')}"

    workflow.write_report_stub(
        "# Vegetation Mapping Runtime Report\n\n"
        f"- Request: {user_request}"
        f"\n- AOI: {aoi}"
        f"\n- Time period: {time_period}"
        f"\n- Method: NDVI >= {threshold}"
        f"{metadata_text}{area_text}{map_text}"
        f"\n- Evaluation: {evaluation.status}\n"
    )
    return workflow
