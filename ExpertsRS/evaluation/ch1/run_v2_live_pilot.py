"""Authorized final v2 5×3 pilot; v2 is decisive and v1 is retained as history."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .d3_light_loader import load_panel
from .d3_light_protocol import balanced_case_order, build_case_slots
from .d3_light_runner import run_authorized_d3_pilot
from .run_d3_light_model_smoke import _load_untracked_environment, _provider_config_from_environment
from .run_v2_live_smoke import _ResultProxy, _StatusProxy
from .v2_evaluator import V2_PROTOCOL_VERSION, evaluate_v2_unified_run


def run_v2_authorized_model_pilot(destination: str | Path) -> list[dict[str, Any]]:
    root = Path(destination)
    if root.exists():
        raise FileExistsError(f"Refusing to overwrite v2 live pilot directory: {root}")
    _load_untracked_environment()
    provider = _provider_config_from_environment()
    panel = load_panel()
    slots = balanced_case_order(build_case_slots(panel))
    records = asyncio.run(run_authorized_d3_pilot(
        root, provider, panel=panel, continue_on_v1_evaluation_failure=True,
    ))
    v2_cases: list[dict[str, Any]] = []
    for slot, record in zip(slots, records, strict=True):
        data = record["result"]
        result = _ResultProxy(Path(data["trace_path"]), _StatusProxy(data["status"]))
        evaluation = evaluate_v2_unified_run(result, slot, panel=panel)
        v2_cases.append({"case_id": slot.case_id, "v1_evaluation": record["evaluation"], "v2_evaluation": evaluation})
    passed = len(v2_cases) == 15 and all(item["v2_evaluation"]["passed"] for item in v2_cases)
    (root / "v2_pilot_summary.json").write_text(json.dumps({
        "kind": "ch1_v2_authorized_live_pilot", "protocol_version": V2_PROTOCOL_VERSION,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(), "case_count": len(v2_cases),
        "all_v2_evaluations_passed": passed, "v2_is_decisive": True,
        "v1_role": "historical side-by-side record only", "cases": v2_cases,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    if not passed:
        raise RuntimeError("V2 5x3 pilot did not reach 15/15 closure; preserved outputs require review")
    return v2_cases


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light" / "v2_authorized_pilot"
    print(json.dumps(run_v2_authorized_model_pilot(root), indent=2, ensure_ascii=False))
