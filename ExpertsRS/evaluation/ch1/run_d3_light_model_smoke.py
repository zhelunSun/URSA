"""Double-gated entry point for three authoritative D3 live smoke cases."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ExpertsRS import ProviderConfig

from .d3_light_protocol import build_case_slots
from .d3_light_runner import run_authorized_d3_smoke
from .d3_light_loader import load_panel


def _load_untracked_environment() -> None:
    """Load local credentials without overriding explicitly supplied variables."""
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def _provider_config_from_environment() -> ProviderConfig:
    """Read identifiers only; the API key itself stays in the environment."""
    model = os.getenv("EXPERTSRS_D3_LIGHT_MODEL", "")
    api_key_env = os.getenv("EXPERTSRS_D3_LIGHT_API_KEY_ENV", "")
    base_url_env = os.getenv("EXPERTSRS_D3_LIGHT_BASE_URL_ENV", "")
    if not model or not api_key_env or not base_url_env:
        raise RuntimeError(
            "Set EXPERTSRS_D3_LIGHT_MODEL, EXPERTSRS_D3_LIGHT_API_KEY_ENV, and "
            "EXPERTSRS_D3_LIGHT_BASE_URL_ENV before a reviewed live smoke."
        )
    return ProviderConfig(
        model=model, api_key_env=api_key_env, base_url_env=base_url_env,
        max_completion_tokens=int(os.getenv("EXPERTSRS_D3_LIGHT_MAX_COMPLETION_TOKENS", "1024")),
    )


def smoke_slots() -> list[Any]:
    """S1 NDVI, S2 recovery, S3 clarification; one reviewed slot each."""
    panel = load_panel()
    by_key = {(slot.source_task_id, slot.condition_id): slot for slot in build_case_slots(panel)}
    return [
        by_key[(2, "B2_adaptive")],
        by_key[(11, "B3_checkpoint")],
        by_key[(13, "B2_adaptive")],
    ]


def run_authorized_model_smoke(destination: str | Path) -> list[dict[str, Any]]:
    _load_untracked_environment()
    return asyncio.run(run_authorized_d3_smoke(
        destination, _provider_config_from_environment(), slots=smoke_slots(),
    ))


def main() -> None:
    root = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light"
    paths = run_authorized_model_smoke(root / "authorized_smoke")
    print(f"D3-light model smoke finished ({len(paths)} cases); inspect external evaluations before any repeat.")


if __name__ == "__main__":
    main()
