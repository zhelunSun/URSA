"""Offline public-schema contracts, validated independently with JSON Schema."""

import inspect
import json
from unittest.mock import patch

import numpy as np
import pytest
import rasterio
from jsonschema import Draft7Validator, ValidationError
from rasterio.transform import from_origin

from tools.index_kit import calculate_ndvi
from tools.output_context import use_output_directory
from tools.registry import _build_schema, get_all_tools, get_tool_by_name, get_tool_schemas


def contract(name):
    return next(item["function"] for item in get_tool_schemas() if item["function"]["name"] == name)


def validate(name, arguments):
    Draft7Validator(contract(name)["parameters"]).validate(arguments)


def test_all_public_contracts_are_valid_json_and_match_callable_parameters():
    schemas = get_tool_schemas()
    assert len(schemas) == len(get_all_tools()) == 18
    json.dumps(schemas, allow_nan=False)
    for schema in schemas:
        function = schema["function"]
        Draft7Validator.check_schema(function["parameters"])
        assert set(function["parameters"]["properties"]) == set(inspect.signature(get_tool_by_name(function["name"])).parameters)


@pytest.mark.parametrize("arguments", [{}, {"file_path": None}, {"file_path": ""},
                                      {"file_path": "scene.tif", "unexpected": True}])
def test_model_ndvi_cannot_omit_or_empty_the_selected_input(arguments):
    with pytest.raises(ValidationError):
        validate("calculate_ndvi", arguments)


def test_default_bands_are_optional_and_explicit_stack_indices_are_supported():
    validate("calculate_ndvi", {"file_path": "scene.tif"})
    validate("calculate_ndvi", {"file_path": "scene.tif", "nir_band": 2, "red_band": "B4"})
    with pytest.raises(ValidationError):
        validate("calculate_ndvi", {"file_path": "scene.tif", "nir_band": False})
    assert contract("calculate_ndvi")["parameters"]["properties"]["nir_band"]["default"] == "B8"


def test_schema_admitted_ndvi_arguments_execute_with_semantic_band_defaults(tmp_path):
    source = tmp_path / "scene.tif"
    with rasterio.open(source, "w", driver="GTiff", width=2, height=2, count=2,
                       dtype="float32", crs="EPSG:32650", transform=from_origin(0, 20, 10, 10)) as dst:
        dst.write(np.stack([np.full((2, 2), 2), np.full((2, 2), 6)]).astype("float32"))
        dst.set_band_description(1, "B4")
        dst.set_band_description(2, "B8")
    arguments = {"file_path": str(source)}
    validate("calculate_ndvi", arguments)
    with use_output_directory(tmp_path / "out"):
        result = calculate_ndvi(**arguments)
    assert result["success"], result
    with rasterio.open(result["data"]["output_path"]) as dataset:
        np.testing.assert_allclose(dataset.read(1), 0.5)


def test_python_convenience_default_is_preserved_but_not_model_admitted():
    assert inspect.signature(calculate_ndvi).parameters["file_path"].default is None
    with patch("tools.index_kit._resolve_data_path", side_effect=FileNotFoundError("offline probe")) as resolve:
        assert not calculate_ndvi()["success"]
    resolve.assert_called_once_with(None)


def test_no_argument_discovery_tool_remains_valid():
    validate("list_available_data_files", {})


def test_parameter_docs_preserve_semantics_without_human_return_layout():
    function = contract("calculate_ndvi")
    assert function["description"] == "Calculate the Normalized Difference Vegetation Index (NDVI)."
    desc = function["parameters"]["properties"]["nir_band"]["description"]
    assert "Semantic NIR" in desc and "already-verified 1-based stack index" in desc
    for schema in get_tool_schemas():
        function = schema["function"]
        assert "Returns:" not in function["description"] and "Args:" not in function["description"]
        for field in function["parameters"]["properties"].values():
            assert field["description"] and not field["description"].startswith("Parameter:")


def test_grouped_arguments_and_multiline_conditions_are_preserved():
    composite = contract("plot_false_color_composite")["parameters"]["properties"]
    for name in ("nir_band", "red_band", "green_band"):
        assert "explicit verified stack indices" in composite[name]["description"]
    plot = contract("plot_index_map")["parameters"]["properties"]
    assert plot["vmin"]["description"] == plot["vmax"]["description"]
    assert "pixels >= threshold_low become 1" in contract("apply_threshold")["parameters"]["properties"]["threshold_high"]["description"]


def test_raster_io_positions_are_not_described_as_sensor_band_identifiers():
    for tool, parameter in (("read_raster_band", "band_index"), ("read_raster_bands", "band_indices")):
        desc = contract(tool)["parameters"]["properties"][parameter]["description"]
        assert "stored raster stack" in desc and "not" in desc and "sensor band identifier" in desc


@pytest.mark.parametrize("name,path_key,list_key", [
    ("read_raster_bands", "file_path", "band_indices"),
    ("calculate_area", "file_path", "class_values"),
    ("zonal_statistics", "zone_file", "zone_values"),
])
def test_integer_lists_are_arrays_not_strings(name, path_key, list_key):
    args = {path_key: "scene.tif"}
    if name == "zonal_statistics":
        args["value_file"] = "values.tif"
    validate(name, {**args, list_key: [1, 2]})
    validate(name, {**args, list_key: None})
    for invalid in ("[1,2]", ["1", "2"]):
        with pytest.raises(ValidationError):
            validate(name, {**args, list_key: invalid})


def test_lst_requires_explicit_sensor_and_radiometric_unit():
    admitted = {"file_path": "thermal.tif", "sensor": "landsat-8", "input_unit": "toa_radiance_w_m2_sr_um"}
    validate("calculate_lst", admitted)
    for invalid in ({"file_path": "thermal.tif"}, {**admitted, "sensor": "sentinel-2"}, {**admitted, "input_unit": "reflectance"}):
        with pytest.raises(ValidationError):
            validate("calculate_lst", invalid)


def test_numpy_input_requires_numeric_nested_array_and_explicit_reference():
    arguments = {"data": [[1, 2], [3, 4]], "output_path": "out.tif", "reference_file": "scene.tif"}
    validate("save_raster", arguments)
    validate("save_raster", {**arguments, "data": [[[1, 2], [3, 4]]]})
    for invalid in ({**arguments, "data": "[[1,2]]"}, {**arguments, "reference_file": None},
                    {key: value for key, value in arguments.items() if key != "reference_file"}):
        with pytest.raises(ValidationError):
            validate("save_raster", invalid)


def test_nan_default_is_not_serialized_as_invalid_json():
    field = contract("apply_mask")["parameters"]["properties"]["nodata_value"]
    assert "default" not in field
    assert "NaN" in field["description"]


def test_undocumented_new_parameters_fail_at_schema_construction():
    def incomplete(value: str):
        """A tool without parameter semantics."""
    with pytest.raises(ValueError, match="Missing model parameter description"):
        _build_schema("incomplete", incomplete)
