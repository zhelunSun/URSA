"""Typed remote-sensing tool contracts for the ExpertsRS runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

try:
    from tools import list_tools
except ImportError:
    from ExpertsRS.tools import list_tools


@dataclass(frozen=True)
class ParameterContract:
    name: str
    semantic: str
    required: bool = False
    type_hint: str = "string"
    unit: str | None = None
    default: Any = None
    notes: str | None = None


@dataclass(frozen=True)
class ArtifactContract:
    kind: str
    description: str
    path_key: str | None = "output_path"
    unit: str | None = None
    crs: str | None = None
    nodata: str | None = None


@dataclass(frozen=True)
class ToolContract:
    tool_name: str
    purpose: str
    parameters: tuple[ParameterContract, ...]
    output_artifacts: tuple[ArtifactContract, ...]
    failure_notes: tuple[str, ...]
    contract_id: str | None = None
    version: int = 1
    band_convention: str = "1-based raster band indexes where band parameters are present"
    crs_notes: str = "Outputs inherit CRS and transform from source rasters when applicable"
    nodata_notes: str = "Tools preserve or set nodata according to rasterio profile and tool-specific logic"

    def __post_init__(self):
        if self.contract_id is None:
            object.__setattr__(self, "contract_id", f"expertsrs.tool.{self.tool_name}.v{self.version}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    tool_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _p(name: str, semantic: str, required: bool = False, type_hint: str = "string",
       unit: str | None = None, default: Any = None, notes: str | None = None) -> ParameterContract:
    return ParameterContract(name, semantic, required, type_hint, unit, default, notes)


def _a(kind: str, description: str, path_key: str | None = "output_path",
       unit: str | None = None, crs: str | None = None, nodata: str | None = None) -> ArtifactContract:
    return ArtifactContract(kind, description, path_key, unit, crs, nodata)


def _c(tool_name: str, purpose: str, parameters: list[ParameterContract],
       output: ArtifactContract, failure_notes: list[str]) -> ToolContract:
    return ToolContract(
        tool_name=tool_name,
        purpose=purpose,
        parameters=tuple(parameters),
        output_artifacts=(output,),
        failure_notes=tuple(failure_notes),
    )


COMMON_RASTER_FAILURES = [
    "Input raster path is missing or cannot be resolved.",
    "Band indexes are outside the raster band count.",
    "Raster metadata, CRS, transform, or nodata values may be incomplete.",
]


TOOL_CONTRACTS: dict[str, ToolContract] = {
    "list_available_data_files": _c(
        "list_available_data_files",
        "Discover available GeoTIFF raster files under the project data directory.",
        [],
        _a("metadata", "Catalog of available raster file names and absolute paths.", path_key=None),
        ["The data directory may be absent or contain no GeoTIFF files."],
    ),
    "read_raster_metadata": _c(
        "read_raster_metadata",
        "Read raster dimensions, CRS, bounds, band count, nodata, and transform metadata.",
        [_p("file_path", "Raster path, optional when a single local data file can be auto-discovered.", False)],
        _a("metadata", "Raster metadata summary.", path_key=None),
        COMMON_RASTER_FAILURES,
    ),
    "read_raster_band": _c(
        "read_raster_band",
        "Read and summarize one raster band.",
        [
            _p("file_path", "Raster path, optional when auto-discovery is safe.", False),
            _p("band_index", "1-based raster band index.", False, "integer", default=1),
        ],
        _a("metadata", "Band statistics summary.", path_key=None),
        COMMON_RASTER_FAILURES,
    ),
    "read_raster_bands": _c(
        "read_raster_bands",
        "Read and summarize multiple raster bands.",
        [
            _p("file_path", "Raster path, optional when auto-discovery is safe.", False),
            _p("band_indices", "List of 1-based raster band indexes.", False, "array"),
        ],
        _a("metadata", "Multi-band read summary.", path_key=None),
        COMMON_RASTER_FAILURES,
    ),
    "save_raster": _c(
        "save_raster",
        "Save a numpy array as a GeoTIFF raster.",
        [
            _p("data", "Array-like raster data to save.", True, "object"),
            _p("output_path", "Output path relative to results or absolute path.", True),
            _p("reference_file", "Optional reference raster for profile, CRS, and transform.", False),
        ],
        _a("raster", "Saved GeoTIFF raster.", unit="source dependent", crs="reference raster when available"),
        ["Array shape may be unsupported.", "Reference metadata may be unavailable."],
    ),
    "calculate_ndvi": _c(
        "calculate_ndvi",
        "Calculate NDVI from NIR and red bands.",
        [_p("file_path", "Source multispectral raster.", False), _p("nir_band", "1-based NIR band.", False, "integer", default=8), _p("red_band", "1-based red band.", False, "integer", default=4)],
        _a("raster", "Single-band NDVI GeoTIFF.", unit="index [-1, 1]"),
        COMMON_RASTER_FAILURES,
    ),
    "calculate_evi": _c(
        "calculate_evi",
        "Calculate EVI from NIR, red, and blue bands.",
        [_p("file_path", "Source multispectral raster.", False), _p("nir_band", "1-based NIR band.", False, "integer", default=8), _p("red_band", "1-based red band.", False, "integer", default=4), _p("blue_band", "1-based blue band.", False, "integer", default=2)],
        _a("raster", "Single-band EVI GeoTIFF.", unit="index"),
        COMMON_RASTER_FAILURES,
    ),
    "calculate_ndwi": _c(
        "calculate_ndwi",
        "Calculate NDWI from green and NIR bands.",
        [_p("file_path", "Source multispectral raster.", False), _p("green_band", "1-based green band.", False, "integer", default=3), _p("nir_band", "1-based NIR band.", False, "integer", default=8)],
        _a("raster", "Single-band NDWI GeoTIFF.", unit="index [-1, 1]"),
        COMMON_RASTER_FAILURES,
    ),
    "calculate_nbr": _c(
        "calculate_nbr",
        "Calculate NBR from NIR and SWIR bands.",
        [_p("file_path", "Source multispectral raster.", False), _p("nir_band", "1-based NIR band.", False, "integer", default=8), _p("swir_band", "1-based SWIR band.", False, "integer", default=12)],
        _a("raster", "Single-band NBR GeoTIFF.", unit="index [-1, 1]"),
        COMMON_RASTER_FAILURES,
    ),
    "calculate_lst": _c(
        "calculate_lst",
        "Estimate land surface temperature from a thermal band.",
        [_p("file_path", "Source thermal raster.", False), _p("thermal_band", "1-based thermal band.", False, "integer", default=10), _p("emissivity", "Surface emissivity.", False, "number", default=0.95)],
        _a("raster", "Single-band LST GeoTIFF.", unit="celsius"),
        COMMON_RASTER_FAILURES + ["Single-channel LST assumptions may not match the source product."],
    ),
    "calculate_msavi": _c(
        "calculate_msavi",
        "Calculate MSAVI from NIR and red bands.",
        [_p("file_path", "Source multispectral raster.", False), _p("nir_band", "1-based NIR band.", False, "integer", default=8), _p("red_band", "1-based red band.", False, "integer", default=4)],
        _a("raster", "Single-band MSAVI GeoTIFF.", unit="index"),
        COMMON_RASTER_FAILURES,
    ),
    "apply_threshold": _c(
        "apply_threshold",
        "Create a binary mask from a single-band raster using one or two thresholds.",
        [_p("file_path", "Single-band input raster.", True), _p("threshold_low", "Lower threshold.", True, "number"), _p("threshold_high", "Optional upper threshold.", False, "number"), _p("output_name", "Semantic output label.", False)],
        _a("raster", "Binary mask GeoTIFF.", unit="class values"),
        ["Input raster may be missing.", "Thresholds may be unsuitable for the selected index."],
    ),
    "calculate_area": _c(
        "calculate_area",
        "Calculate class areas from a classified raster mask.",
        [_p("file_path", "Classified raster mask.", True), _p("pixel_area_km2", "Optional pixel area override.", False, "number", "km2"), _p("class_values", "Optional class values to summarize.", False, "array")],
        _a("metadata", "Area statistics by class.", path_key=None, unit="km2 and hectares"),
        ["Pixel area may be wrong if CRS units are not meters.", "Input classes may not match user intent."],
    ),
    "apply_mask": _c(
        "apply_mask",
        "Apply a binary mask to a raster.",
        [_p("input_file", "Raster to mask.", True), _p("mask_file", "Binary mask raster.", True), _p("mask_value", "Mask value to retain.", False, "integer", default=1)],
        _a("raster", "Masked raster GeoTIFF.", unit="source dependent"),
        ["Input and mask rasters may not be aligned.", "Mask values may not match expected class labels."],
    ),
    "zonal_statistics": _c(
        "zonal_statistics",
        "Calculate summary statistics for a value raster by zone raster.",
        [_p("zone_file", "Zone raster.", True), _p("value_file", "Value raster.", True), _p("zone_values", "Optional zone values.", False, "array")],
        _a("metadata", "Zonal statistics table.", path_key=None),
        ["Zone and value rasters may not be aligned.", "Zone values may be missing."],
    ),
    "plot_index_map": _c(
        "plot_index_map",
        "Render a continuous single-band index map.",
        [_p("file_path", "Single-band raster to render.", True), _p("index_name", "Index label.", False), _p("cmap", "Matplotlib colormap.", False)],
        _a("map", "Rendered continuous map image.", unit="image"),
        ["Matplotlib may be unavailable.", "Color scale choices may obscure interpretation."],
    ),
    "plot_thematic_map": _c(
        "plot_thematic_map",
        "Render a classified or thematic raster map.",
        [_p("file_path", "Classified raster to render.", True), _p("class_labels", "Class label mapping.", False, "object"), _p("output_name", "Output label.", False)],
        _a("map", "Rendered thematic map image.", unit="image"),
        ["Matplotlib may be unavailable.", "Class labels may not match raster values."],
    ),
    "plot_false_color_composite": _c(
        "plot_false_color_composite",
        "Render a false-color composite from NIR, red, and green bands.",
        [_p("file_path", "Source multispectral raster.", False), _p("nir_band", "1-based NIR band.", False, "integer", default=8), _p("red_band", "1-based red band.", False, "integer", default=4), _p("green_band", "1-based green band.", False, "integer", default=3)],
        _a("map", "Rendered false-color composite image.", unit="image"),
        COMMON_RASTER_FAILURES + ["Band assignments may be unsuitable for non-Sentinel products."],
    ),
}


def get_tool_contract(tool_name: str) -> ToolContract | None:
    return TOOL_CONTRACTS.get(tool_name)


def list_tool_contracts() -> list[ToolContract]:
    return [TOOL_CONTRACTS[name] for name in sorted(TOOL_CONTRACTS)]


def validate_contract_registry(tool_names: list[str] | None = None) -> list[ValidationIssue]:
    expected = set(tool_names or list_tools())
    actual = set(TOOL_CONTRACTS)
    issues: list[ValidationIssue] = []

    for name in sorted(expected - actual):
        issues.append(ValidationIssue("missing_contract", f"No ToolContract registered for {name}.", tool_name=name))
    for name in sorted(actual - expected):
        issues.append(ValidationIssue("orphan_contract", f"Contract registered for unknown tool {name}.", tool_name=name))
    for name in sorted(expected & actual):
        contract = TOOL_CONTRACTS[name]
        if not contract.output_artifacts:
            issues.append(ValidationIssue("missing_output_contract", f"Tool {name} has no output artifact contract.", tool_name=name))
        if not contract.failure_notes:
            issues.append(ValidationIssue("missing_failure_notes", f"Tool {name} has no failure notes.", tool_name=name))
    return issues
