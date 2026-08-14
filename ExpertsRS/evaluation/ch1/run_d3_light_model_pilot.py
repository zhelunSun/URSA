"""Double-gated entry point for one reviewed 5-task × 3-condition live pilot."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .d3_light_loader import load_panel
from .d3_light_protocol import balanced_case_order, build_case_slots
from .d3_light_runner import run_authorized_d3_pilot
from .run_d3_light_model_smoke import _load_untracked_environment, _provider_config_from_environment


def pilot_slots() -> list[Any]:
    """Return the frozen seeded balanced order for all 15 slots."""
    return balanced_case_order(build_case_slots(load_panel()))


def run_authorized_model_pilot(destination: str | Path) -> list[dict[str, Any]]:
    _load_untracked_environment()
    return asyncio.run(run_authorized_d3_pilot(destination, _provider_config_from_environment(), panel=load_panel()))


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light"
    records = run_authorized_model_pilot(root / "authorized_pilot")
    print(f"D3-light live pilot finished ({len(records)} cases); inspect pilot_summary.json before any repeat.")


if __name__ == "__main__":
    main()
