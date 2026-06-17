"""Tool execution wrapper for the ExpertsRS runtime."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

try:
    from tools import list_tools
    from tools.registry import get_tool_by_name
except ImportError:  # Allow imports from repository root in future package layouts.
    from ExpertsRS.tools import list_tools
    from ExpertsRS.tools.registry import get_tool_by_name

from .state import AgentRole, RunState


def _summarize_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"type": type(result).__name__}

    summary: dict[str, Any] = {
        "success": result.get("success"),
        "message": result.get("message"),
    }
    data = result.get("data")
    if isinstance(data, dict):
        for key in [
            "output_path",
            "file_name",
            "count",
            "shape",
            "min",
            "max",
            "mean",
            "total_area_km2",
            "total_area_hectares",
        ]:
            if key in data:
                summary[key] = data[key]
    return summary


def _infer_artifact_kind(path: str) -> str:
    lower = path.lower()
    if lower.endswith((".tif", ".tiff")):
        return "raster"
    if lower.endswith((".jpg", ".jpeg", ".png")):
        return "map"
    if lower.endswith((".json", ".geojson")):
        return "metadata"
    return "artifact"


class ToolRuntime:
    """Execute registered RS tools and write tool traces into RunState."""

    def __init__(self):
        self.available_tools = set(list_tools())

    def call(
        self,
        state: RunState,
        tool_name: str,
        role: AgentRole | str = AgentRole.ENGINEER,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if tool_name not in self.available_tools:
            message = f"Tool {tool_name!r} is not registered"
            state.add_error("ToolRuntime.call", message, {"tool_name": tool_name})
            raise ValueError(message)

        tool = get_tool_by_name(tool_name)
        if tool is None:
            message = f"Tool {tool_name!r} could not be resolved"
            state.add_error("ToolRuntime.call", message, {"tool_name": tool_name})
            raise ValueError(message)

        call_record = state.start_tool_call(tool_name, deepcopy(kwargs), role=role)
        try:
            result = tool(**kwargs)
            summary = _summarize_result(result)
            success = bool(result.get("success")) if isinstance(result, dict) else True
            message = result.get("message") if isinstance(result, dict) else None
            state.finish_tool_call(call_record.call_id, success, message=message, result_summary=summary)

            if isinstance(result, dict) and isinstance(result.get("data"), dict):
                output_path = result["data"].get("output_path")
                if output_path:
                    state.add_artifact(
                        kind=_infer_artifact_kind(output_path),
                        path=output_path,
                        source_tool_call_id=call_record.call_id,
                        label=tool_name,
                        metadata=summary,
                    )
            return result
        except Exception as exc:
            state.finish_tool_call(call_record.call_id, False, message=str(exc))
            state.add_error(tool_name, str(exc), {"args": kwargs})
            raise
