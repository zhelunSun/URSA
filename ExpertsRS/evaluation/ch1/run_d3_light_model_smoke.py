"""Guarded entry point for the future unified-runtime D3 live smoke.

The D3 local-tool fixtures remain evaluator-only until an approved model
provider adapter has been wired into ``ExpertsRSSystem``.  This module must not
fall back to the former direct D3 runner, which preselected role phases and
therefore was not a valid agent-system execution.
"""

from __future__ import annotations

from pathlib import Path

def run_authorized_model_smoke(destination: str | Path) -> list[Path]:
    del destination
    raise RuntimeError(
        "D3 live execution is not yet authorized: configure and test a modern "
        "AutoGen decision provider for ExpertsRSSystem, then review the frozen "
        "provider/model, budget, disclosure and evaluator protocol."
    )


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light"
    paths = run_authorized_model_smoke(root / "authorized_smoke")
    print(f"D3-light model smoke finished ({len(paths)} cases); inspect external evaluations before any repeat.")


if __name__ == "__main__":
    main()
