"""Scripted no-API ReAct pilot using real ExpertsRS tools and trace events."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from react_orchestration import ReActRoutingState
from tools.analysis_kit import apply_threshold
from tools.index_kit import calculate_ndvi
from tools.io_kit import list_available_data_files, read_raster_metadata


def _decision(
    state: ReActRoutingState,
    agent: str,
    summary: str,
    tool: str,
    arguments: dict,
) -> None:
    message = {
        "content": summary,
        "tool_calls": [{
            "id": f"{agent}-{tool}",
            "type": "function",
            "function": {"name": tool, "arguments": json.dumps(arguments)},
        }],
    }
    state.record_decision(agent, message)
    state.record_tool_call(agent, message)


def _observation(state: ReActRoutingState, agent: str, result: dict) -> None:
    state.pending_tool_owner = agent
    state.record_observation({"content": result})
    state.pending_tool_owner = None


def main() -> None:
    root = Path(__file__).resolve().parent
    run_id = datetime.now().strftime("react_pilot_%Y%m%d%H%M%S")
    state = ReActRoutingState(run_id, root / "results" / f"{run_id}.json")

    _decision(state, "Scientist", "Decision: inspect the available scene before selecting bands.", "list_available_data_files", {})
    files = list_available_data_files()
    _observation(state, "Scientist", files)
    source = files["data"]["abs_paths"][0]

    _decision(
        state,
        "Scientist",
        "Decision: inspect scene bands and spatial metadata before planning NDVI.",
        "read_raster_metadata",
        {"file_path": source},
    )
    metadata = read_raster_metadata(source)
    _observation(state, "Scientist", metadata)
    state.record_handoff("Scientist", "Engineer", {"content": "Resolve Sentinel-2 B8 and B4 from band descriptions for an NDVI greenspace workflow."})

    ndvi_args = {"file_path": source, "nir_band": "B8", "red_band": "B4"}
    _decision(state, "Engineer", "Decision: compute NDVI from the verified NIR and red bands.", "calculate_ndvi", ndvi_args)
    ndvi = calculate_ndvi(**ndvi_args)
    _observation(state, "Engineer", ndvi)
    if not ndvi["success"]:
        state.finalise("ndvi_failed")
        raise SystemExit(ndvi["message"])

    mask_args = {
        "file_path": ndvi["data"]["output_path"],
        "threshold_low": 0.3,
        "output_name": "react_greenspace",
    }
    _decision(state, "Engineer", "Decision: threshold the observed NDVI artifact to produce the requested mask.", "apply_threshold", mask_args)
    mask = apply_threshold(**mask_args)
    _observation(state, "Engineer", mask)
    state.record_handoff("Engineer", "Manager", {"content": mask["message"]})
    state.finalise("completed" if mask["success"] else "threshold_failed")
    expected_counts = {"Scientist": 2, "Engineer": 2}
    if state.tool_calls_by_agent != expected_counts:
        raise SystemExit(
            f"Trace invariant failed: expected tool-call counts {expected_counts}, "
            f"got {state.tool_calls_by_agent}."
        )
    print(
        f"Pilot status: {'completed' if mask['success'] else 'failed'}; "
        f"tool calls: {state.tool_calls_by_agent}; trace: {state.trace_path}"
    )
    if not mask["success"]:
        raise SystemExit(mask["message"])


if __name__ == "__main__":
    main()
