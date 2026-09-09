"""Adapter from the existing 18-tool registry to typed planning contracts."""

from __future__ import annotations

import inspect

from .specs import ArtifactType, OperatorSpec


R = ArtifactType.RASTER
I = ArtifactType.INDEX_RASTER
M = ArtifactType.MASK_RASTER
META = ArtifactType.METADATA
MAP = ArtifactType.MAP
AREA = ArtifactType.AREA_STATISTICS


def _spec(
    name: str,
    inputs: dict[str, tuple[ArtifactType, ...]],
    output: ArtifactType,
    **kwargs,
) -> OperatorSpec:
    return OperatorSpec(
        operator_id=f"expertsrs.{name}.v1",
        tool_name=name,
        input_types=inputs,
        output_type=output,
        **kwargs,
    )


def build_operator_catalog(profile: str = "legacy") -> dict[str, OperatorSpec]:
    """Return versioned contracts for all public functions in ``tools.registry``."""
    source = {"file_path": (R,)}
    catalog = {
        "expertsrs.list_available_data_files.v1": _spec("list_available_data_files", {}, META),
        "expertsrs.read_raster_metadata.v1": _spec("read_raster_metadata", source, META, preconditions=("file_exists",)),
        "expertsrs.read_raster_band.v1": _spec("read_raster_band", source, R, preconditions=("file_exists",)),
        "expertsrs.read_raster_bands.v1": _spec("read_raster_bands", source, R, preconditions=("file_exists",)),
        "expertsrs.save_raster.v1": _spec(
            "save_raster", {"data": (R, I, M)}, R,
            required_config={"output_path": ()},
        ),
        "expertsrs.calculate_ndvi.v1": _spec(
            "calculate_ndvi", source, I, preconditions=("file_exists",),
            required_bands=("B8", "B4"),
            default_config={"nir_band": "B8", "red_band": "B4"},
        ),
        "expertsrs.calculate_evi.v1": _spec(
            "calculate_evi", source, I, preconditions=("file_exists",),
            required_bands=("B8", "B4", "B2"),
            default_config={
                "nir_band": "B8", "red_band": "B4", "blue_band": "B2",
                "reflectance_scale": 10000.0,
            },
        ),
        "expertsrs.calculate_ndwi.v1": _spec(
            "calculate_ndwi", source, I, preconditions=("file_exists",),
            required_bands=("B3", "B8"),
            default_config={"green_band": "B3", "nir_band": "B8"},
        ),
        "expertsrs.calculate_nbr.v1": _spec(
            "calculate_nbr", source, I, preconditions=("file_exists",),
            required_bands=("B8", "B12"),
            default_config={"nir_band": "B8", "swir_band": "B12"},
        ),
        "expertsrs.calculate_lst.v1": _spec(
            "calculate_lst", source, I, preconditions=("file_exists",),
            required_bands=("B10",),
            required_config={
                "sensor": ("landsat-8",),
                "input_unit": ("toa_radiance_w_m2_sr_um",),
            },
            default_config={"thermal_band": "B10", "emissivity": 0.95},
            failure_modes=("scientific_precondition_failed",),
        ),
        "expertsrs.calculate_msavi.v1": _spec(
            "calculate_msavi", source, I, preconditions=("file_exists",),
            required_bands=("B8", "B4"),
            default_config={
                "nir_band": "B8", "red_band": "B4", "reflectance_scale": 10000.0,
            },
        ),
        "expertsrs.apply_threshold.v1": _spec("apply_threshold", {"file_path": (I,)}, M, preconditions=("file_exists",), default_config={"threshold_low": 0.3}),
        "expertsrs.calculate_area.v1": _spec("calculate_area", {"file_path": (M,)}, AREA, preconditions=("file_exists",)),
        "expertsrs.apply_mask.v1": _spec("apply_mask", {"input_file": (R, I), "mask_file": (M,)}, R, preconditions=("file_exists",)),
        "expertsrs.zonal_statistics.v1": _spec("zonal_statistics", {"value_file": (R, I), "zone_file": (M,)}, META, preconditions=("file_exists",)),
        "expertsrs.plot_index_map.v1": _spec("plot_index_map", {"file_path": (I,)}, MAP, preconditions=("file_exists",)),
        "expertsrs.plot_thematic_map.v1": _spec("plot_thematic_map", {"file_path": (M,)}, MAP, preconditions=("file_exists",)),
        "expertsrs.plot_false_color_composite.v1": _spec(
            "plot_false_color_composite", source, MAP, preconditions=("file_exists",),
            required_bands=("B8", "B4", "B3"),
            default_config={"nir_band": "B8", "red_band": "B4", "green_band": "B3"},
        ),
    }

    # Keep the typed harness tied to, rather than divergent from, the tool layer.
    # The fallback preserves historical scripts that execute from ExpertsRS/.
    try:
        from ExpertsRS.tools.registry import get_all_tools, list_tools
    except ModuleNotFoundError:
        from tools.registry import get_all_tools, list_tools
    if profile == "classification-v1":
        catalog.update({
            "expertsrs.summarize_classification.v1": _spec(
                "summarize_classification", {"file_path": (R,), "aoi_path": (ArtifactType.AOI,)},
                ArtifactType.COMPOSITION_TABLE, preconditions=("file_exists",), default_config={"year": 2025},
            ),
            "expertsrs.plot_classification_map.v1": _spec(
                "plot_classification_map", {"file_path": (R,), "aoi_path": (ArtifactType.AOI,), "composition_path": (ArtifactType.COMPOSITION_TABLE,)},
                MAP, preconditions=("file_exists",), default_config={"year": 2025},
            ),
        })
    registered = set(list_tools(profile))
    contracted = {operator.tool_name for operator in catalog.values()}
    if registered != contracted:
        raise RuntimeError(f"Tool contract drift: registry={registered ^ contracted}")

    functions = {function.__name__: function for function in get_all_tools(profile)}
    for operator in catalog.values():
        signature = inspect.signature(functions[operator.tool_name])
        actual = set(signature.parameters)
        declared = (
            set(operator.input_types)
            | set(operator.default_config)
            | set(operator.required_config)
        )
        unknown = declared - actual
        required = {
            name
            for name, parameter in signature.parameters.items()
            if parameter.default is inspect.Parameter.empty
            and parameter.kind in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
        }
        missing = required - declared
        if unknown or missing:
            raise RuntimeError(
                f"Operator signature drift for {operator.tool_name}: "
                f"unknown={sorted(unknown)}, missing_required={sorted(missing)}"
            )
    return catalog
