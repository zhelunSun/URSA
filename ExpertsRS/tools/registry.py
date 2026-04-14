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

from typing import get_type_hints
import inspect

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


def _build_schema(name: str, func) -> dict:
    """Build an OpenAI function_call schema from a Python function."""
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    desc = (func.__doc__ or "").strip()

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        # Skip None defaults for required list (they're optional)
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
            type_str = "string"
        else:
            type_str = "string"

        # Infer type from type hints
        if param_name in hints:
            th = hints[param_name]
            type_map = {
                str: "string",
                int: "integer",
                float: "number",
                bool: "boolean",
                list: "array",
                dict: "object",
            }
            type_str = type_map.get(th, "string")

        # Build description from param docstring context
        param_desc = f"Parameter: {param_name}"
        if param.default is not inspect.Parameter.empty:
            param_desc += f" (default: {param.default})"

        properties[param_name] = {
            "type": type_str,
            "description": param_desc,
        }

    schema = {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }
    return schema


def get_all_tools() -> list:
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


def get_tool_by_name(name: str):
    """Get a single tool by function name."""
    for module in _TOOL_MODULES:
        if hasattr(module, name):
            return getattr(module, name)
    return None


def list_tools() -> list[str]:
    """Return the names of all available tools."""
    return sorted(_TOOL_NAMES)


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
