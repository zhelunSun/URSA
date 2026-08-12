"""Execute all 15 D3-light slots with the deterministic no-API provider."""

from __future__ import annotations

import json
from pathlib import Path

from .d3_light_loader import load_panel
from .d3_light_protocol import balanced_case_order, build_case_slots
from .d3_light_runner import D3LightRunner, DeterministicDryRunProvider


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


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light_dry_run"
    paths = run_all_dry_cases(root)
    print(f"D3-light deterministic dry run: PASS ({len(paths)} cases)")
    print(f"  results: {root}")


if __name__ == "__main__":
    main()
