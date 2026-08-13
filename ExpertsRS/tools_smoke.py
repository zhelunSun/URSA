"""Executable compatibility smoke check for the legacy tool layer.

This is intentionally not named ``test_*.py`` so unittest discovery does not
execute it as a module.  The authoritative automated tests live in
``test_scientific_preconditions.py`` and ``test_system.py``.
"""

from __future__ import annotations

from pathlib import Path

from tools import get_all_tools, get_tool_schemas, list_tools
from tools.analysis_kit import apply_threshold
from tools.index_kit import calculate_ndvi
from tools.registry import get_tool_by_name, print_tool_catalog
from tools.viz_kit import plot_index_map


def main() -> int:
    tools = get_all_tools()
    schemas = get_tool_schemas()
    assert len(tools) == len(schemas) == len(list_tools()) == 18
    assert get_tool_by_name("calculate_ndvi") is calculate_ndvi
    assert not apply_threshold("nonexistent.tif", 0.3)["success"]
    assert not plot_index_map("nonexistent.tif")["success"]
    assert "ExpertsRS Tool Catalog" in _catalog()
    result = calculate_ndvi()
    assert "success" in result
    print(f"Tools smoke check: PASS ({len(tools)} registered tools)")
    return 0


def _catalog() -> str:
    from contextlib import redirect_stdout
    from io import StringIO

    output = StringIO()
    with redirect_stdout(output):
        print_tool_catalog()
    return output.getvalue()


if __name__ == "__main__":
    raise SystemExit(main())
