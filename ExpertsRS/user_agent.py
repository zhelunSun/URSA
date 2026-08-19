"""Isolated, one-turn clarification fixtures for Chapter 1 evidence only."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib import request as urlrequest

from .models import ProviderConfig, RunRequest, RunResult


@dataclass(frozen=True)
class UserAnswer:
    answer: str
    provenance: dict[str, Any]


class ProfiledUserAgent(Protocol):
    async def answer(self, original_request: str, manager_question: str, public_artifacts: list[dict[str, str]]) -> UserAnswer: ...


class RuleProfiledUserAgent:
    """Fixed, deterministic profile; it never sees gold, plans, or evaluator state."""
    profile_id = "rule_ndvi_map_once_v1"

    async def answer(self, original_request: str, manager_question: str, public_artifacts: list[dict[str, str]]) -> UserAnswer:
        return UserAnswer(
            "Please use NDVI as the vegetation-health indicator and provide an NDVI map.",
            {"profile_id": self.profile_id, "mode": "rule", "turn_limit": 1, "public_artifact_count": len(public_artifacts)},
        )


class LiveProfiledUserAgent:
    """One bounded provider call with a fixed profile and zero retries."""
    profile_id = "live_ndvi_map_once_v1"

    def __init__(self, provider: ProviderConfig) -> None:
        self.provider = provider

    async def answer(self, original_request: str, manager_question: str, public_artifacts: list[dict[str, str]]) -> UserAnswer:
        prompt = {
            "role": "fixed clarification user profile",
            "instruction": "Answer the manager once. Choose NDVI and request an NDVI map. Return only the answer sentence.",
            "original_request": original_request,
            "manager_question": manager_question,
            "public_artifacts": public_artifacts,
        }
        prompt_text = json.dumps(prompt, ensure_ascii=False, sort_keys=True)
        started = time.monotonic()
        payload = json.dumps({
            "model": self.provider.model,
            "messages": [{"role": "user", "content": prompt_text}],
            "temperature": 0, "top_p": 1, "max_tokens": min(256, self.provider.max_completion_tokens),
        }).encode("utf-8")
        base_url = os.environ.get(self.provider.base_url_env)
        api_key = os.environ.get(self.provider.api_key_env)
        if not base_url or not api_key:
            raise RuntimeError("Live ProfiledUserAgent is missing its configured provider environment")
        endpoint = base_url.rstrip("/") + ("/chat/completions" if not base_url.rstrip("/").endswith("chat/completions") else "")
        req = urlrequest.Request(endpoint, data=payload, method="POST", headers={
            "Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
        })
        def send() -> dict[str, Any]:
            with urlrequest.urlopen(req, timeout=self.provider.timeout_seconds) as response:  # nosec B310: reviewed configured endpoint
                return json.loads(response.read().decode("utf-8"))
        body = await asyncio.to_thread(send)
        content = str(body["choices"][0]["message"]["content"]).strip()
        if not content:
            raise RuntimeError("Live ProfiledUserAgent produced an empty answer")
        usage = body.get("usage") or {}
        return UserAnswer(content, {
            "profile_id": self.profile_id, "mode": "live", "turn_limit": 1,
            "model": self.provider.model, "temperature": 0, "max_retries": 0,
            "prompt_hash": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
            "token_usage": {key: int(usage.get(key, 0)) for key in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "wall_time_seconds": round(time.monotonic() - started, 3),
        })


async def run_one_clarification_loop(system: Any, request: RunRequest, user_agent: ProfiledUserAgent) -> tuple[RunResult, RunResult, dict[str, Any]]:
    """Run clarify → one profiled answer → the public `.resume()` API."""
    first = await system.run(request)
    if first.status.value != "needs_clarification" or not first.questions:
        raise RuntimeError("Clarification-loop fixture expected a Manager clarification terminal")
    public_artifacts = [{"artifact_id": item.artifact_id, "artifact_type": item.artifact_type} for item in first.artifacts]
    answer = await user_agent.answer(request.request, first.questions[0], public_artifacts)
    resumed = await system.resume(first.run_id, answer.answer, request.output_dir)
    transcript = {
        "kind": "isolated_profiled_user_agent_transcript",
        "original_request": request.request,
        "manager_question": first.questions[0],
        "answer": answer.answer,
        "profile": answer.provenance,
        "first_terminal_status": first.status.value,
        "resumed_terminal_status": resumed.status.value,
        "public_artifact_summary": public_artifacts,
        "boundary": "No panel gold, fault ledger, private evaluator contract, or internal plan was supplied to the UserAgent.",
    }
    path = Path(request.output_dir) / request.run_id / "profiled_user_agent_transcript.json"
    path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False), encoding="utf-8")
    return first, resumed, transcript
