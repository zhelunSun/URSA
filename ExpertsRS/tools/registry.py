"""
registry.py — Tool registration for AutoGen

Exposes all tools as:
  1. Python function_map for AutoGen AssistantAgent
  2. OpenAI function_call schemas for structured tool calling

Usage in notebook:
    from tools import get_all_tools, get_tool_schemas

    tools = get_all_tools()           # list of actual callable functions
    schemas = get_tool_schemas()      # list of OpenAI function schemas

    engineer = autogen.AssistantAgent(
        name="Engineer",
        system_message=engineer_prompt,
        llm_config=deepseekv3_config,
        function_map={f.__name__: f for f in tools},  # ← 注册到这里
    )
"""

from copy import deepcopy
from typing import Any, Union, get_args, get_origin, get_type_hints
import inspect
import json
import re
import types

from . import io_kit, index_kit, analysis_kit, viz_kit

# Collect all tool modules
_TOOL_MODULES = [io_kit, index_kit, analysis_kit, viz_kit]

# Public tool functions (exclude private helpers and _ prefixed)
_TOOL_NAMES = {
    # io_kit
    "list_available_data_files",
    "read_raster_metadata",
    "read_raster_band",
    "read_raster_bands",
    "save_raster",
    # index_kit
    "calculate_ndvi",
    "calculate_evi",
    "calculate_ndwi",
    "calculate_nbr",
    "calculate_lst",
    "calculate_msavi",
    # analysis_kit
    "apply_threshold",
    "calculate_area",
    "apply_mask",
    "zonal_statistics",
    # viz_kit
    "plot_index_map",
    "plot_thematic_map",
    "plot_false_color_composite",
}


# A callable's convenience defaults are not the model-facing input contract.
# Keep Python callers compatible while requiring an explicit data selection in
# the legacy notebook's tool schema. This is not a filesystem permission gate.
_MODEL_REQUIRED = {
    name: {"file_path"} for name in (
        "read_raster_metadata", "read_raster_band", "read_raster_bands",
        "calculate_ndvi", "calculate_evi", "calculate_ndwi", "calculate_nbr",
        "calculate_lst", "calculate_msavi", "plot_false_color_composite",
    )
}
_MODEL_REQUIRED["calculate_lst"].update({"sensor", "input_unit"})
_MODEL_REQUIRED["save_raster"] = {"reference_file"}

_BAND_PARAMETERS = {"nir_band", "red_band", "blue_band", "green_band", "swir_band", "thermal_band"}
_PATH_PARAMETERS = {"file_path", "input_file", "mask_file", "zone_file", "value_file", "reference_file", "output_path"}


def _parameter_docs(func) -> tuple[str, dict[str, str]]:
    """Extract a summary and Google-style Args, including grouped names."""
    doc = inspect.getdoc(func) or ""
    summary = " ".join(doc.split("\n\n", 1)[0].split())
    descriptions: dict[str, list[str]] = {}
    current: list[str] = []
    in_args = False
    for line in doc.splitlines():
        if line == "Args:":
            in_args = True
            continue
        if not in_args:
            continue
        if line and not line[0].isspace():
            break
        match = re.match(r"^ {4}([a-z_]\w*(?:\s*,\s*[a-z_]\w*)*)(?:\s*\([^)]*\))?:\s*(.*)$", line)
        if match:
            current = [name.strip() for name in match[1].split(",")]
            for name in current:
                descriptions[name] = [match[2]]
        elif line.strip():
            for name in current:
                descriptions[name].append(line.strip())
    return summary, {name: " ".join(" ".join(parts).split()) for name, parts in descriptions.items()}


def _annotation_schema(annotation) -> dict:
    """Translate JSON-compatible hints; never silently turn a list into str."""
    primitive = {str: "string", int: "integer", float: "number", bool: "boolean", type(None): "null"}
    if annotation in primitive:
        return {"type": primitive[annotation]}
    origin, args = get_origin(annotation), get_args(annotation)
    if annotation is Any:
        return {}
    if origin in (Union, types.UnionType):
        return {"anyOf": [_annotation_schema(arg) for arg in args]}
    if annotation is list or origin is list:
        return {"type": "array", "items": _annotation_schema(args[0]) if args else {}}
    if annotation is dict or origin is dict:
        return {"type": "object", "additionalProperties": _annotation_schema(args[1]) if args else {}}
    raise ValueError(f"Tool parameter needs an explicit JSON contract: {annotation!r}")


def _build_schema(name: str, func) -> dict:
    """Build a model-facing contract without changing the Python callable.

    These are conventional tool schemas, not a promise of provider-side strict
    mode or execution-time validation. The authoritative runtime separately
    validates role decisions and binds logical plan inputs.
    """
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    desc, parameter_docs = _parameter_docs(func)
    explicit = _MODEL_REQUIRED.get(name, set())
    if explicit - sig.parameters.keys():
        raise ValueError(f"Model-required parameters no longer match {name}'s signature")

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        mandatory = param.default is inspect.Parameter.empty or param_name in explicit
        if mandatory:
            required.append(param_name)
        if param_name not in parameter_docs:
            raise ValueError(f"Missing model parameter description: {name}.{param_name}")
        param_desc = parameter_docs[param_name]
        # The legacy prose confuses stack positions with physical band IDs.
        # These I/O tools use Rasterio positions; only the index tools below
        # accept semantic sensor names such as B8.
        if name == "read_raster_band" and param_name == "band_index":
            param_desc = "1-based position in the stored raster stack, not a sensor band identifier. Inspect raster metadata before selecting."
        if name == "read_raster_bands" and param_name == "band_indices":
            param_desc = "List of 1-based positions in the stored raster stack, not sensor band identifiers. If omitted or null, read all stored bands."
        if name == "save_raster" and param_name == "data":
            matrix = {"type": "array", "minItems": 1, "items": {
                "type": "array", "minItems": 1, "items": {"type": "number"}}}
            field = {"anyOf": [matrix, {"type": "array", "minItems": 1, "items": deepcopy(matrix)}]}
            param_desc = "Numeric nested array: 2D (height, width) or 3D (bands, height, width)."
        elif param_name in _BAND_PARAMETERS:
            field = {"anyOf": [{"type": "string", "minLength": 1}, {"type": "integer", "minimum": 1}]}
        else:
            field = _annotation_schema(hints.get(param_name, inspect.Parameter.empty))

        if param_name in _PATH_PARAMETERS:
            field["minLength"] = 1
            if param_name in explicit:
                param_desc = ("Explicit path to the reference raster for CRS and transform."
                              if param_name == "reference_file" else "Explicit path to the input raster.")
                param_desc += " Select the intended file; omission, null and empty paths are not allowed in model calls."
        if name == "calculate_lst" and param_name in {"sensor", "input_unit"}:
            field["enum"] = ["landsat-8" if param_name == "sensor" else "toa_radiance_w_m2_sr_um"]
        if not mandatory and param.default is None:
            field = {"anyOf": [field, {"type": "null"}]}
        if not mandatory:
            # NaN (apply_mask's Python default) is not valid JSON. Explain it
            # in prose instead of producing an invalid wire default.
            try:
                json.dumps(param.default, allow_nan=False)
            except (TypeError, ValueError):
                param_desc += " If omitted, the Python tool uses a non-finite nodata value (NaN)."
            else:
                field["default"] = param.default
        field["description"] = param_desc
        properties[param_name] = field

    schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }
    return schema


def get_all_tools(profile: str = "legacy") -> list:
    """
    Return all tools as actual Python callables.
    Use this for function_map in AutoGen agents.
    """
    tools = []
    for module in _TOOL_MODULES:
        for name in dir(module):
            if name in _TOOL_NAMES:
                func = getattr(module, name)
                if callable(func):
                    tools.append(func)
    if profile == "classification-v1":
        from .product_kit import summarize_classification, plot_classification_map
        tools.extend([summarize_classification, plot_classification_map])
    elif profile != "legacy":
        raise ValueError(f"Unknown tool profile: {profile}")
    return sorted(tools, key=lambda f: f.__name__)


def get_tool_schemas() -> list:
    """
    Return all tools as OpenAI function_call schemas.
    Use this for llm_config['tools'] in AutoGen agents.
    """
    schemas = []
    for module in _TOOL_MODULES:
        for name in dir(module):
            if name in _TOOL_NAMES:
                func = getattr(module, name)
                if callable(func):
                    schemas.append(_build_schema(name, func))
    return schemas


def get_tool_by_name(name: str, profile: str = "legacy"):
    """Get a single tool by function name."""
    return next((tool for tool in get_all_tools(profile) if tool.__name__ == name), None)


def list_tools(profile: str = "legacy") -> list[str]:
    """Return the names of all available tools."""
    return sorted(tool.__name__ for tool in get_all_tools(profile))


def print_tool_catalog():
    """Print a readable catalog of all available tools."""
    print("=" * 60)
    print("ExpertsRS Tool Catalog")
    print("=" * 60)
    for module in _TOOL_MODULES:
        mod_name = module.__name__.split(".")[-1]
        funcs = [(n, getattr(module, n)) for n in dir(module)
                 if n in _TOOL_NAMES and callable(getattr(module, n))]
        if funcs:
            print(f"\n[{mod_name}]")
            for name, func in sorted(funcs, key=lambda x: x[0]):
                doc = (func.__doc__ or "").strip().split("\n")[0]
                print(f"  {name}: {doc}")
    print("\n" + "=" * 60)
