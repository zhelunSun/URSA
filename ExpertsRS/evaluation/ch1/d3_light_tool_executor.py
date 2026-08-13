"""Real local-tool executor for D3-light; no model or network dependency."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tools.registry import get_tool_by_name


DEFAULT_SOURCE = Path(__file__).resolve().parents[2] / "data" / "Sentinel2_Dongcheng_20230718.tif"


class D3LightToolExecutor:
    """Executes only registered tools and injects the approved task-11 fixture once."""

    def __init__(self, source: str | Path = DEFAULT_SOURCE) -> None:
        self.source = str(Path(source))
        self._threshold_failure_injected = False

    def begin_case(self) -> None:
        """Reset the approved transient-failure fixture for one independent case."""
        self._threshold_failure_injected = False

    def execute(
        self, tool_name: str, artifacts: dict[str, str], *, inject_transient_failure: bool = False
    ) -> dict[str, Any]:
        if tool_name == "apply_threshold" and inject_transient_failure and not self._threshold_failure_injected:
            self._threshold_failure_injected = True
            return {
                "success": False,
                "error_code": "fixture_transient_write_failure",
                "message": "Seeded D3-light fixture: the first threshold write failed before producing a mask.",
                "data": None,
            }
        tool = get_tool_by_name(tool_name)
        if tool is None:
            return {
                "success": False,
                "error_code": "tool_not_registered",
                "message": f"No registered tool named {tool_name}.",
                "data": None,
            }
        kwargs = self._arguments(tool_name, artifacts)
        try:
            return tool(**kwargs)
        except Exception as error:  # Defensive boundary: tools normally return structured errors.
            return {
                "success": False,
                "error_code": "tool_execution_exception",
                "message": f"{tool_name} raised {type(error).__name__}: {error}",
                "data": None,
            }

    def _arguments(self, tool_name: str, artifacts: dict[str, str]) -> dict[str, Any]:
        if tool_name == "read_raster_metadata":
            return {"file_path": self.source}
        if tool_name == "calculate_ndvi":
            return {"file_path": self.source, "nir_band": "B8", "red_band": "B4"}
        if tool_name == "plot_index_map":
            return {"file_path": artifacts["index_raster"], "index_name": "NDVI", "output_name": "d3_light_ndvi"}
        if tool_name == "apply_threshold":
            return {"file_path": artifacts["index_raster"], "threshold_low": 0.3, "output_name": "d3_light_greenspace"}
        if tool_name == "plot_thematic_map":
            return {"file_path": artifacts["mask_raster"], "output_name": "d3_light_greenspace"}
        if tool_name == "calculate_area":
            return {"file_path": artifacts["mask_raster"], "class_values": [1]}
        raise ValueError(f"D3-light has no fixed tool arguments for {tool_name}")
