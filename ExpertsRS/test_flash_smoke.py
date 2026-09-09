"""No-network checks for smoke admission and first-failure evidence capture."""
import argparse
import asyncio
import importlib.util
import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from autogen_core.logging import LLMCallEvent

spec = importlib.util.spec_from_file_location("flash_smoke", Path(__file__).resolve().parents[1] / "scripts/run_flash_runtime_smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


def test_no_api_consent_rejects_before_credentials(tmp_path):
    args = argparse.Namespace(allow_api=False, output=tmp_path / "new", credentials_file=Path("missing.env"))
    with patch.object(smoke, "dotenv_values", side_effect=AssertionError("credentials accessed")):
        with pytest.raises(ValueError, match="allow-api"):
            asyncio.run(smoke.run(args))
    assert not args.output.exists()


def test_existing_batch_is_not_overwritten(tmp_path):
    existing = tmp_path / "result.json"
    existing.write_text("original", encoding="utf-8")
    args = argparse.Namespace(allow_api=True, output=tmp_path, credentials_file=Path("missing.env"))
    with patch.object(smoke, "dotenv_values", side_effect=AssertionError("credentials accessed")):
        with pytest.raises(FileExistsError):
            asyncio.run(smoke.run(args))
    assert existing.read_text(encoding="utf-8") == "original"


def test_malformed_response_keeps_raw_usage_and_first_error(tmp_path):
    path = tmp_path / "journal.jsonl"
    journal = smoke.Journal(path, "test-secret")

    class InvalidProvider:
        async def decide(self, role, state):
            event = LLMCallEvent(messages=[], response={"choices": [{"message": {"content": "{bad JSON test-secret"}}]},
                                 prompt_tokens=10, completion_tokens=4)
            journal.emit(logging.LogRecord("autogen_core.events", logging.INFO, __file__, 0, event, (), None))
            raise ValueError("invalid JSON")

    try:
        with pytest.raises(ValueError, match="invalid JSON"):
            asyncio.run(smoke.JournaledProvider(InvalidProvider(), journal).decide("Manager", {"request": "test"}))
        assert journal.intents == 1
        assert journal.responses[0]["completion_tokens"] == 4
    finally:
        journal.close()
    raw = path.read_text(encoding="utf-8")
    events = [json.loads(line) for line in raw.splitlines()]
    assert [e["kind"] for e in events] == ["decision_intent", "raw_model_response", "decision_error"]
    assert "test-secret" not in raw
    assert "{bad JSON" in raw
