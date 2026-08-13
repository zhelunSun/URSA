"""Run the 15-slot D3-light check with real local tools and no model API.

This is a pre-flight integration check, not the live-model experiment.  It
uses the frozen deterministic decisions solely to establish that the runtime,
permissions, semantic band resolution, artifacts, recovery trace, and external
evaluator can close on the fixed raster without any network request.
"""

from __future__ import annotations

import json
from pathlib import Path

from .d3_light_loader import load_panel
from .d3_light_protocol import api_calls_permitted, balanced_case_order, build_case_slots
from .d3_light_runner import D3LightRunner, DeterministicDryRunProvider
from .d3_light_tool_executor import D3LightToolExecutor


def run_all_local_tool_cases(destination: str | Path) -> list[Path]:
    panel = load_panel()
    if api_calls_permitted(panel):
        raise RuntimeError("Local-tool pre-flight refuses to run while the model API gate is open")
    runner = D3LightRunner(panel, DeterministicDryRunProvider(), D3LightToolExecutor())
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for order, slot in enumerate(balanced_case_order(build_case_slots(panel)), start=1):
        result = runner.run(slot)
        if not result.evaluation["passed"]:
            raise RuntimeError(f"D3-light local-tool evaluator failed: {result.case_id}")
        path = root / f"{order:02d}_{result.case_id}.json"
        path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light_local_tool_check"
    paths = run_all_local_tool_cases(root)
    print(f"D3-light local-tool pre-flight: PASS ({len(paths)} cases; model API disabled)")
    print(f"  traces: {root}")


if __name__ == "__main__":
    main()
