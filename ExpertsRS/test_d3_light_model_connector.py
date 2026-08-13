"""No-network tests for the D3-light real-model decision connector."""

import json
import os
import unittest

from evaluation.ch1.d3_light_loader import build_agent_case, load_panel
from evaluation.ch1.d3_light_model_connector import (
    APIAuthorizationError,
    ModelDecisionAdapter,
    OpenAICompatibleClient,
    configured_deepseek_client,
)


class RecordingClient:
    def __init__(self, response=None):
        self.calls = []
        self.response = response or {"content": '{"kind":"action","tool":"read_raster_metadata"}'}

    def complete(self, *, model, messages, settings):
        self.calls.append({"model": model, "messages": messages, "settings": settings})
        return self.response


class FakeHttpResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"model": "deepseek-ai/DeepSeek-V3", "usage": {"total_tokens": 12}, "choices": [{"message": {"content": '{"kind":"stop","status":"controlled_stop","reason":"no tool"}'}}]}


class RecordingSession:
    def __init__(self):
        self.calls = []

    def post(self, endpoint, **kwargs):
        safe_kwargs = dict(kwargs)
        safe_kwargs["headers"] = {"Authorization": "<redacted>", "Content-Type": "application/json"}
        self.calls.append({"endpoint": endpoint, **safe_kwargs})
        return FakeHttpResponse()


class D3LightModelConnectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = load_panel()
        cls.client = RecordingClient()
        cls.connector = ModelDecisionAdapter(cls.panel, cls.client)

    def test_request_uses_current_role_and_frozen_sampling(self):
        case = build_agent_case(self.panel, 2, "B2_adaptive")
        request = self.connector.build_request(case, {
            "phase": "metadata",
            "available_tools": ["read_raster_metadata"],
            "remaining_tool_budget": 10,
        })
        self.assertIn("Scientist", request["messages"][0]["content"])
        self.assertEqual(request["settings"]["temperature"], 0)
        self.assertEqual(request["settings"]["max_tokens"], 6000)

    def test_request_redacts_paths_hashes_and_hidden_contracts(self):
        case = build_agent_case(self.panel, 11, "B3_checkpoint")
        request = self.connector.build_request(case, {
            "phase": "threshold",
            "available_tools": ["apply_threshold"],
            "remaining_tool_budget": 7,
            "hidden_fixture": "fixture_transient_write_failure",
            "absolute_path": "D:/private/secret.tif",
            "last_observation": {
                "success": False,
                "error_code": "fixture_transient_write_failure",
                "message": "write failed",
                "output_path": "D:/private/result.tif",
                "token": "do-not-send",
            },
        })
        payload = request["messages"][1]["content"]
        self.assertNotIn("D:/private", payload)
        self.assertNotIn("hidden_fixture", payload)
        self.assertNotIn("token", payload)
        self.assertNotIn("chapter1_contract", payload)
        self.assertNotIn("fixture_transient_write_failure", payload)
        self.assertNotIn("Seeded D3-light fixture", payload)
        self.assertIn("transient_tool_failure", payload)

    def test_closed_gate_blocks_client_before_any_network_call(self):
        case = build_agent_case(self.panel, 2, "B2_adaptive")
        before = len(self.client.calls)
        with self.assertRaises(APIAuthorizationError):
            self.connector.next_step(case, {"phase": "metadata"})
        self.assertEqual(len(self.client.calls), before)

    def test_strict_json_decision_parsing(self):
        self.assertEqual(
            ModelDecisionAdapter.parse_decision({"content": '{"kind":"clarify","question":"Which metric?"}'}),
            {"kind": "clarify", "question": "Which metric?"},
        )
        with self.assertRaises(ValueError):
            ModelDecisionAdapter.parse_decision({"content": "I would call NDVI."})
        with self.assertRaises(ValueError):
            ModelDecisionAdapter.parse_decision({"content": json.dumps({"kind": "action"})})

    def test_compatible_client_never_records_key_in_payload(self):
        session = RecordingSession()
        client = OpenAICompatibleClient("secret-value", "https://api.example/v1", session)
        result = client.complete(
            model="deepseek-ai/DeepSeek-V3",
            messages=[{"role": "user", "content": "hello"}],
            settings={"temperature": 0, "top_p": 1, "max_tokens": 10, "timeout_seconds": 1},
        )
        serialized = json.dumps(session.calls)
        self.assertEqual(result["usage"]["total_tokens"], 12)
        self.assertIn("https://api.example/v1/chat/completions", serialized)
        self.assertNotIn("secret-value", serialized)

    def test_model_override_is_refused_before_client_construction(self):
        old_model = os.environ.get("DEEPSEEK_MODEL")
        os.environ["DEEPSEEK_MODEL"] = "other-model"
        try:
            with self.assertRaises(APIAuthorizationError):
                configured_deepseek_client(self.panel)
        finally:
            if old_model is None:
                os.environ.pop("DEEPSEEK_MODEL", None)
            else:
                os.environ["DEEPSEEK_MODEL"] = old_model


if __name__ == "__main__":
    unittest.main(verbosity=2)
