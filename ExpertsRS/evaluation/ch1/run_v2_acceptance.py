"""No-API v0.5.2 acceptance runner using the authoritative runtime."""

from __future__ import annotations

import asyncio
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .d3_light_loader import load_panel
from .d3_light_protocol import balanced_case_order, build_case_slots
from .d3_light_runner import run_unified_d3_case
from .v2_evaluator import V2_PROTOCOL_VERSION, evaluate_v2_unified_run


def run_v2_scripted_acceptance(destination: str | Path) -> list[Path]:
    """Execute the fixed 15 slots without an API call and write non-overwrite evidence."""
    root = Path(destination)
    if root.exists():
        raise FileExistsError(f"Refusing to overwrite v2 acceptance directory: {root}")
    root.mkdir(parents=True)
    panel = load_panel()
    panel_path = Path(__file__).with_name("d3_light_panel_v1.json")
    records: list[Path] = []
    evaluations: list[dict[str, Any]] = []
    run_manifests: list[dict[str, Any]] = []
    for index, slot in enumerate(balanced_case_order(build_case_slots(panel)), start=1):
        result = asyncio.run(run_unified_d3_case(slot, destination=root / "runs"))
        evaluation = evaluate_v2_unified_run(result, slot, panel=panel)
        record = {
            "protocol_version": V2_PROTOCOL_VERSION,
            "case_id": slot.case_id,
            "mode": "unified_runtime_scripted_offline_v2",
            "result": result.model_dump(mode="json"),
            "evaluation": evaluation,
        }
        path = root / f"{index:02d}_{slot.case_id}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        records.append(path)
        evaluations.append(evaluation)
        run_manifests.append(json.loads((Path(result.trace_path).parent / "manifest.json").read_text(encoding="utf-8")))
        if not evaluation["passed"]:
            raise RuntimeError(f"V2 evaluator failed: {slot.case_id}: {evaluation}")
    try:
        code_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[3], text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        code_commit = None
    forbidden = ("Thoughtevent", '"thought"', '"reasoning"', '"reasoning_content"')
    persisted = [path for path in root.rglob("*") if path.is_file() and path.name in {"trace.jsonl", "state.json"}]
    leak_hits = [str(path.relative_to(root)) for path in persisted if any(token in path.read_text(encoding="utf-8") for token in forbidden)]
    checksums = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }
    manifest = {
        "kind": "ch1_v2_scripted_acceptance",
        "protocol_version": V2_PROTOCOL_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "panel_sha256": hashlib.sha256(panel_path.read_bytes()).hexdigest(),
        "code_commit": code_commit,
        "python_version": sys.version,
        "platform": platform.platform(),
        "execution_mode": "scripted-offline",
        "budgets": run_manifests[0].get("budgets") if run_manifests else None,
        "case_count": len(records),
        "all_passed": True,
        "graph_alignment": {
            "plan_action_consistent": all(item["plan_action_consistent"] for item in evaluations),
            "plan_observation_consistent": all(item["plan_observation_consistent"] for item in evaluations),
            "scientist_revision_consistent": all(item["scientist_revision_consistent"] for item in evaluations),
        },
        "delivery_obligation_closure": all(item["obligation_chain_complete"] for item in evaluations),
        "privacy_leak_scan": {"passed": not leak_hits, "forbidden_tokens": list(forbidden), "hits": leak_hits},
        "artifact_sha256": checksums,
        "claim_boundary": {
            "supported": [
                "v2 planned graph constrains scripted runtime actions",
                "observed graph can be reconstructed from runtime facts",
                "report completeness and thought-event persistence checks close in offline acceptance",
            ],
        "not_supported": [
                "live-model reliability or generalization",
                "scientific or administrative-area correctness of green-cover metrics",
                "independent checkpoint benefit, planning superiority, or stable treatment effect",
            ],
        },
        "overwrite_policy": "never_overwrite",
        "records": [path.name for path in records],
    }
    (root / "acceptance_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return records


if __name__ == "__main__":
    destination = Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light" / "v2_scripted_acceptance"
    paths = run_v2_scripted_acceptance(destination)
    print(f"v2 scripted acceptance complete: {len(paths)} cases")
