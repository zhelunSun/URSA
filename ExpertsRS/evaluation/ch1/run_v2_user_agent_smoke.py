"""Separate clarification/resume evidence; not part of the matched 5×3 panel."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ExpertsRS import ExpertsRSSystem, RunBudgets, RunRequest
from ExpertsRS.models import ExecutionMode
from ExpertsRS.user_agent import LiveProfiledUserAgent, RuleProfiledUserAgent, run_one_clarification_loop

from .d3_light_loader import load_panel
from .run_d3_light_model_smoke import _load_untracked_environment, _provider_config_from_environment


def _request(root: Path, mode: ExecutionMode, provider: Any | None) -> RunRequest:
    panel = load_panel()
    task = next(item for item in panel["tasks"] if item["source_task_id"] == 13)
    budget = panel["proposed_run_protocol"]["per_run_budget"]
    source = Path(__file__).resolve().parents[2] / "data" / Path(panel["fixed_context"]["raster"]).name
    return RunRequest(request=task["request"], data_paths=[source], output_dir=root,
        run_id="task13_clarification_loop", execution_mode=mode, provider=provider, budgets=RunBudgets(**budget))


def _evaluate(first: Any, resumed: Any, transcript: dict[str, Any]) -> dict[str, Any]:
    return {"passed": first.status.value == "needs_clarification" and resumed.status.value == "completed"
        and transcript["profile"].get("turn_limit") == 1, "clarification_terminal": first.status.value,
        "resumed_terminal": resumed.status.value, "used_public_resume_api": True, "boundary": transcript["boundary"]}


def run_v2_profiled_user_agent_smokes(destination: str | Path) -> dict[str, Any]:
    root = Path(destination)
    if root.exists():
        raise FileExistsError(f"Refusing to overwrite user-agent smoke directory: {root}")
    root.mkdir(parents=True)
    rule_root = root / "rule_profile"; rule_root.mkdir()
    first, resumed, transcript = asyncio.run(run_one_clarification_loop(
        ExpertsRSSystem(), _request(rule_root, ExecutionMode.SCRIPTED_OFFLINE, None), RuleProfiledUserAgent()))
    records = [{"kind": "rule", "evaluation": _evaluate(first, resumed, transcript), "run_id": resumed.run_id}]
    _load_untracked_environment()
    provider = _provider_config_from_environment()
    live_root = root / "live_profile"; live_root.mkdir()
    first, resumed, transcript = asyncio.run(run_one_clarification_loop(
        ExpertsRSSystem(), _request(live_root, ExecutionMode.AUTOGEN_LIVE, provider), LiveProfiledUserAgent(provider)))
    records.append({"kind": "live", "evaluation": _evaluate(first, resumed, transcript), "run_id": resumed.run_id})
    summary = {"kind": "ch1_v2_profiled_user_agent_smokes", "completed_at_utc": datetime.now(timezone.utc).isoformat(),
               "all_passed": all(item["evaluation"]["passed"] for item in records), "records": records,
               "scope": "isolated one-turn test fixture, not a standing fourth runtime role or a user study"}
    (root / "user_agent_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if not summary["all_passed"]:
        raise RuntimeError("Profiled UserAgent smoke did not close clarification/resume")
    return summary


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[2] / "results" / "ch1_d3_light" / "v2_profiled_user_agent_smoke"
    print(json.dumps(run_v2_profiled_user_agent_smokes(target), ensure_ascii=False, indent=2))
