"""Frozen, no-API run protocol and case matrix for D3-light."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import random
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .d3_light_loader import build_agent_case, build_evaluator_case, load_panel


ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT.parent
API_GATE_ENV = "EXPERTSRS_D3_LIGHT_ALLOW_API"


@dataclass(frozen=True)
class D3CaseSlot:
    source_task_id: int
    condition_id: str
    ordinal: int

    @property
    def case_id(self) -> str:
        return f"task-{self.source_task_id:02d}__{self.condition_id}"


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def build_case_slots(panel: dict[str, Any]) -> list[D3CaseSlot]:
    return [
        D3CaseSlot(task["source_task_id"], condition_id, ordinal)
        for ordinal, task in enumerate(panel["tasks"], start=1)
        for condition_id in panel["conditions"]
    ]


def balanced_case_order(slots: Iterable[D3CaseSlot], seed: int = 20260812) -> list[D3CaseSlot]:
    """Shuffle task order within each condition, then interleave conditions."""
    grouped: dict[str, list[D3CaseSlot]] = {}
    for slot in slots:
        grouped.setdefault(slot.condition_id, []).append(slot)
    rng = random.Random(seed)
    for group in grouped.values():
        rng.shuffle(group)
    ordered: list[D3CaseSlot] = []
    condition_ids = sorted(grouped)
    for row in range(max(len(grouped[key]) for key in condition_ids)):
        for condition_id in condition_ids:
            if row < len(grouped[condition_id]):
                ordered.append(grouped[condition_id][row])
    return ordered


def api_calls_permitted(panel: dict[str, Any]) -> bool:
    """Require both frozen protocol consent and an explicit local environment flag."""
    return (
        bool(panel["run_gate"]["api_calls_authorized"])
        and os.getenv(API_GATE_ENV) == "YES"
    )


def build_run_manifest(panel: dict[str, Any], slot: D3CaseSlot) -> dict[str, Any]:
    protocol = panel["proposed_run_protocol"]
    agent_case = build_agent_case(panel, slot.source_task_id, slot.condition_id)
    evaluator_case = build_evaluator_case(panel, slot.source_task_id, slot.condition_id)
    try:
        autogen_version = importlib.metadata.version("pyautogen")
    except importlib.metadata.PackageNotFoundError:
        autogen_version = "not_installed"
    return {
        "case_id": slot.case_id,
        "ordinal": slot.ordinal,
        "agent_case": agent_case,
        "evaluator_case": evaluator_case,
        "protocol": protocol,
        "provenance": {
            "git_commit": git_commit(),
            "panel_sha256": sha256_file(Path(__file__).with_name("d3_light_panel_v1.json")),
            "prompt_sha256": sha256_file(ROOT / "prompts.py"),
            "orchestration_sha256": sha256_file(ROOT / "react_orchestration.py"),
            "tool_registry_sha256": sha256_file(ROOT / "tools" / "registry.py"),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "autogen_version": autogen_version,
        },
    }


def write_dry_run_manifests(
    destination: str | Path,
    panel: dict[str, Any] | None = None,
    seed: int = 20260812,
) -> list[Path]:
    """Write all planned slots without importing a provider SDK or calling a model."""
    panel = panel or load_panel()
    if api_calls_permitted(panel):
        raise RuntimeError("Dry-run refuses to run while the API gate is open")
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for order, slot in enumerate(balanced_case_order(build_case_slots(panel), seed), start=1):
        manifest = build_run_manifest(panel, slot)
        manifest["execution_order"] = order
        manifest["mode"] = "no_api_dry_run"
        manifest["api_calls_permitted"] = False
        path = root / f"{order:02d}_{slot.case_id}.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def main() -> None:
    destination = ROOT / "results" / "ch1_d3_light_dry_run"
    paths = write_dry_run_manifests(destination)
    print(f"D3-light no-API dry run: PASS ({len(paths)} planned runs)")
    print(f"  manifests: {destination}")


if __name__ == "__main__":
    main()
