"""One authorized, non-overwriting three-case runtime smoke; no silent retries.

Uses existing tasks and v2 evaluator. This is a new-model engineering run, not
recovery of an old package or a matched scientific experiment.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from autogen_core import EVENT_LOGGER_NAME
from autogen_core.logging import LLMCallEvent
from dotenv import dotenv_values
from ExpertsRS import ExpertsRSSystem, LocalToolExecutor, ProviderConfig
from ExpertsRS.provider import create_autogen_live_provider
from ExpertsRS.evaluation.ch1.d3_light_loader import load_panel
from ExpertsRS.evaluation.ch1.d3_light_protocol import api_calls_permitted
from ExpertsRS.evaluation.ch1.d3_light_runner import run_unified_d3_case
from ExpertsRS.evaluation.ch1.run_d3_light_model_smoke import smoke_slots
from ExpertsRS.evaluation.ch1.v2_evaluator import evaluate_v2_unified_run

MODEL = "deepseek-ai/DeepSeek-V4-Flash"


def now():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


class Journal(logging.Handler):
    def __init__(self, path, secret):
        super().__init__()
        self.stream = path.open("x", encoding="utf-8")
        self.secret = secret
        self.case_id = None
        self.responses = []
        self.intents = 0

    def record(self, kind, payload):
        raw = json.dumps({"at": now(), "case_id": self.case_id, "kind": kind, "payload": payload}, ensure_ascii=False)
        # No request headers are journaled. Redact an accidental echoed secret.
        self.stream.write(raw.replace(self.secret, "[REDACTED]") + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def emit(self, record):
        if isinstance(record.msg, LLMCallEvent):
            payload = json.loads(str(record.msg))
            self.record("raw_model_response", payload)
            self.responses.append({"case_id": self.case_id, **payload})

    def close(self):
        self.stream.close()
        super().close()


class JournaledProvider:
    def __init__(self, inner, journal):
        self.inner, self.journal = inner, journal

    async def decide(self, role, state):
        self.journal.intents += 1
        self.journal.record("decision_intent", {"role": role, "runtime_view": state})
        try:
            return await self.inner.decide(role, state)
        except Exception as error:
            self.journal.record("decision_error", {"role": role, "error_type": type(error).__name__})
            raise

    async def save_state(self):
        return await self.inner.save_state()

    async def load_state(self, state):
        return await self.inner.load_state(state)


async def run(args):
    if not args.allow_api:
        raise ValueError("Explicit --allow-api is required before reading credentials")
    if args.output.exists():
        raise FileExistsError("Output already exists; choose a new batch directory")
    panel = load_panel()
    if not api_calls_permitted(panel):
        raise ValueError("Existing panel gate and EXPERTSRS_D3_LIGHT_ALLOW_API=YES are required")
    raster = ROOT / "ExpertsRS/data" / Path(panel["fixed_context"]["raster"]).name
    if file_hash(raster).lower() != panel["fixed_context"]["raster_sha256"].lower():
        raise ValueError("Frozen input raster identity mismatch")
    values = dotenv_values(args.credentials_file)
    secret = values.get("SILICONFLOW_API_KEY") or ""
    base = (values.get("SILICONFLOW_BASE_URL") or "").rstrip("/")
    parsed = urlsplit(base)
    if not secret or parsed.scheme != "https" or parsed.netloc != "api.siliconflow.cn" or parsed.path != "/v1" or parsed.query or parsed.fragment:
        raise ValueError("Expected the existing SiliconFlow key and official /v1 endpoint")
    config = ProviderConfig(model=MODEL, api_key_env="SILICONFLOW_API_KEY", base_url_env="SILICONFLOW_BASE_URL",
                            enable_thinking=False, max_completion_tokens=4096, timeout_seconds=120)
    slots = smoke_slots()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {"kind": "flash_runtime_three_case_smoke", "created_at": now(), "code_commit": commit,
                "authorization": "Researcher message 2026-09-09: use existing API and DeepSeek V4 Flash for practical testing",
                "model": MODEL, "provider_config": config.model_dump(), "endpoint": base,
                "scheduled_cases": [s.case_id for s in slots], "maximum_cases": 3,
                "per_case_budget": panel["proposed_run_protocol"]["per_run_budget"],
                "effective_max_completion_tokens": config.max_completion_tokens,
                "maximum_decision_attempts": 3 * panel["proposed_run_protocol"]["per_run_budget"]["max_model_turns"],
                "stop_policy": "stop batch on first failed v2/transport-completion check; no automatic rerun",
                "hashes": {str(p.relative_to(ROOT)): file_hash(p) for p in [raster, Path(__file__),
                           ROOT / "ExpertsRS/provider.py", ROOT / "ExpertsRS/system.py",
                           ROOT / "ExpertsRS/evaluation/ch1/d3_light_panel_v1.json",
                           ROOT / "ExpertsRS/evaluation/ch1/v2_evaluator.py"]},
                "scope": "New-provider engineering smoke on existing development tasks; no method-effect or thematic-accuracy claim"}
    write_new(args.output / "batch_manifest.json", manifest)
    journal = Journal(args.output / "model_journal.jsonl", secret)
    logger = logging.getLogger(EVENT_LOGGER_NAME)
    old_level, old_propagate = logger.level, logger.propagate
    old_env = {key: os.environ.get(key) for key in [config.api_key_env, config.base_url_env]}
    os.environ[config.api_key_env], os.environ[config.base_url_env] = secret, base
    logger.addHandler(journal); logger.setLevel(logging.INFO); logger.propagate = False
    cases, started_cases, batch_error = [], [], None
    try:
        for slot in slots:
            started_cases.append(slot.case_id)
            journal.case_id = slot.case_id
            inner = create_autogen_live_provider(config)
            failures = {"apply_threshold": 1} if slot.source_task_id == 11 else {}
            system = ExpertsRSSystem(provider=JournaledProvider(inner, journal), executor=LocalToolExecutor(
                inject_failures=failures,
                injected_failure_ids={"apply_threshold": "d3-task-11-threshold-once"} if failures else {}))
            try:
                result = await run_unified_d3_case(slot, destination=args.output, system=system, provider_config=config)
            finally:
                await inner.model_client.close()
            evaluation = evaluate_v2_unified_run(result, slot)
            responses = [r for r in journal.responses if r["case_id"] == slot.case_id]
            complete = bool(responses) and all(c.get("finish_reason") == "stop" for r in responses for c in r["response"].get("choices", []))
            record = {"case_id": slot.case_id, "status": result.status.value, "v2_evaluation": evaluation,
                      "response_count": len(responses), "normal_completion_responses": complete,
                      "response_models": sorted({r["response"].get("model", "unknown") for r in responses}),
                      "passed": bool(evaluation["passed"] and complete)}
            write_new(args.output / (slot.case_id + ".evaluation.json"), record)
            cases.append(record)
            print(json.dumps(record, ensure_ascii=True), flush=True)
            if not record["passed"]:
                break
    except Exception as error:
        batch_error = type(error).__name__
        journal.record("batch_error", {"error_type": batch_error})
    finally:
        totals = {k: sum(int(r.get(k, 0)) for r in journal.responses) for k in ["prompt_tokens", "completion_tokens"]}
        totals["total_tokens"] = sum(totals.values())
        summary = {"kind": manifest["kind"], "finished_at": now(), "model": MODEL, "cases": cases,
                   "all_three_passed": len(cases) == 3 and all(c["passed"] for c in cases),
                   "decision_attempts": journal.intents, "response_count": len(journal.responses),
                   "actual_response_usage": totals, "currency_cost": None, "batch_error_type": batch_error,
                   "unrun_cases": [s.case_id for s in slots if s.case_id not in started_cases],
                   "interrupted_cases": [s for s in started_cases if s not in {c["case_id"] for c in cases}],
                   "usage_note": "Journal totals include responses rejected by decision parsing; request errors may have unreported provider usage"}
        write_new(args.output / "batch_summary.json", summary)
        logger.removeHandler(journal); logger.setLevel(old_level); logger.propagate = old_propagate
        journal.close()
        for key, value in old_env.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if summary["all_three_passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--credentials-file", type=Path, required=True)
    parser.add_argument("--allow-api", action="store_true")
    args = parser.parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    except (ValueError, FileExistsError) as error:
        print(json.dumps({"status": "preflight_rejected", "reason": str(error)}))
        raise SystemExit(2)
