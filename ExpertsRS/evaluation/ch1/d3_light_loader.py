"""Leakage-safe views of the D3-light task panel.

The tested Agent receives only the original request/context and the fixed data
contract. Fixtures and expected outcomes remain in the external evaluator view.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


PANEL_PATH = Path(__file__).with_name("d3_light_panel_v1.json")


def load_panel(path: str | Path = PANEL_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _task_by_id(panel: dict[str, Any], source_task_id: int) -> dict[str, Any]:
    matches = [
        task for task in panel["tasks"]
        if task["source_task_id"] == source_task_id
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one D3-light task {source_task_id}")
    return matches[0]


def build_agent_case(
    panel: dict[str, Any], source_task_id: int, condition_id: str
) -> dict[str, Any]:
    """Return the only fields that may enter the tested trajectory."""
    if condition_id not in panel["conditions"]:
        raise ValueError(f"Unknown D3-light condition: {condition_id}")
    task = _task_by_id(panel, source_task_id)
    return {
        "benchmark_id": panel["benchmark_id"],
        "source_task_id": source_task_id,
        "condition_id": condition_id,
        "request": task["request"],
        "context": task["context"],
        "data": {
            "raster": panel["fixed_context"]["raster"],
            "raster_sha256": panel["fixed_context"]["raster_sha256"],
        },
    }


def build_evaluator_case(
    panel: dict[str, Any], source_task_id: int, condition_id: str
) -> dict[str, Any]:
    """Return hidden fixture and scoring information for the external grader."""
    if condition_id not in panel["conditions"]:
        raise ValueError(f"Unknown D3-light condition: {condition_id}")
    task = _task_by_id(panel, source_task_id)
    return {
        "benchmark_id": panel["benchmark_id"],
        "source_task_id": source_task_id,
        "condition_id": condition_id,
        "condition": deepcopy(panel["conditions"][condition_id]),
        "fixture": deepcopy(task["fixture"]),
        "chapter1_contract": deepcopy(task["chapter1_contract"]),
        "global_scoring_contract": deepcopy(panel["global_scoring_contract"]),
    }
