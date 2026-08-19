"""Authorized three-case live smoke with the v2 external evaluator."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .d3_light_runner import run_authorized_d3_smoke
from .run_d3_light_model_smoke import _load_untracked_environment, _provider_config_from_environment, smoke_slots
from .v2_evaluator import V2_PROTOCOL_VERSION, evaluate_v2_unified_run


@dataclass(frozen=True)
class _ResultProxy:
    """Only the public RunResult fields consumed by the external evaluator."""

    trace_path: Path
    status: Any


@dataclass(frozen=True)
class _StatusProxy:
    value: str


def run_v2_authorized_model_smoke(destination: str | Path) -> list[dict[str, Any]]:
    """Run S1/S2/S3 once, preserving v1 and v2 evaluator records side by side.

    The underlying entry point still enforces the reviewed panel gate and local
    API environment flag.  This wrapper adds no provider/model choice and does
    not open the separate 5x3 pilot authorization.
    """
    root = Path(destination)
    if root.exists():
        raise FileExistsError(f"Refusing to overwrite v2 live smoke directory: {root}")
    _load_untracked_environment()
    provider = _provider_config_from_environment()
    slots = smoke_slots()
    records = asyncio.run(run_authorized_d3_smoke(
        root, provider, slots=slots, continue_on_v1_evaluation_failure=True,
    ))
    v2_records: list[dict[str, Any]] = []
    for slot, record in zip(slots, records, strict=True):
        result_data = record["result"]
        result = _ResultProxy(
            trace_path=Path(result_data["trace_path"]),
            status=_StatusProxy(result_data["status"]),
        )
        evaluation = evaluate_v2_unified_run(result, slot)
        v2_record = {
            "case_id": slot.case_id,
            "protocol_version": V2_PROTOCOL_VERSION,
            "v1_evaluation": record["evaluation"],
            "v2_evaluation": evaluation,
        }
        v2_records.append(v2_record)
        if not evaluation["passed"]:
            raise RuntimeError(f"V2 live smoke evaluator failed: {slot.case_id}: {evaluation}")
    (root / "v2_smoke_summary.json").write_text(json.dumps({
        "kind": "ch1_v2_authorized_live_smoke",
        "protocol_version": V2_PROTOCOL_VERSION,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": len(v2_records),
        "all_v2_evaluations_passed": True,
        "cases": v2_records,
        "scope": "three authorized smokes only; does not authorize the v2 5x3 replay",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return v2_records


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light" / "v2_authorized_smoke"
    print(json.dumps(run_v2_authorized_model_smoke(root), indent=2, ensure_ascii=False))
