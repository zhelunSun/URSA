"""Execute all 15 D3-light slots with the deterministic no-API provider."""

from __future__ import annotations

import json
import asyncio
from pathlib import Path

from .d3_light_loader import build_evaluator_case, load_panel
from .d3_light_protocol import balanced_case_order, build_case_slots
from .d3_light_runner import D3LightRunner, DeterministicDryRunProvider, evaluate_unified_d3_run, run_unified_d3_case


def run_all_dry_cases(destination: str | Path) -> list[Path]:
    panel = load_panel()
    runner = D3LightRunner(panel, DeterministicDryRunProvider())
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for order, slot in enumerate(balanced_case_order(build_case_slots(panel)), start=1):
        result = runner.run(slot)
        if not result.evaluation["passed"]:
            raise RuntimeError(f"D3-light dry-run evaluator failed: {result.case_id}")
        path = root / f"{order:02d}_{result.case_id}.json"
        path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def run_all_unified_dry_cases(destination: str | Path) -> list[Path]:
    """Run all D3 slots through the authoritative API with scripted decisions.

    This is the current offline engineering gate.  The legacy runner above is
    intentionally retained only to reproduce its previously frozen fixture.
    """
    panel = load_panel()
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for order, slot in enumerate(balanced_case_order(build_case_slots(panel)), start=1):
        result = asyncio.run(run_unified_d3_case(slot, destination=root))
        evaluation = evaluate_unified_d3_run(
            result, build_evaluator_case(panel, slot.source_task_id, slot.condition_id),
        )
        if not evaluation["passed"]:
            raise RuntimeError(f"Unified D3 offline evaluator failed: {slot.case_id}: {evaluation}")
        path = root / f"{order:02d}_{slot.case_id}.json"
        path.write_text(json.dumps({
            "case_id": slot.case_id,
            "mode": "unified_runtime_scripted_offline",
            "result": result.model_dump(mode="json"),
            "evaluation": evaluation,
        }, indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light_dry_run"
    paths = run_all_dry_cases(root)
    print(f"D3-light deterministic dry run: PASS ({len(paths)} cases)")
    print(f"  results: {root}")


if __name__ == "__main__":
    main()
