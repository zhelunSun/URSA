"""No-network tests for the D3-light real-model decision connector."""

import json
import os
import unittest
from copy import deepcopy

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


class MalformedHttpResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": []}


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
        self.assertEqual(request["settings"]["max_tokens"], 8192)

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

    def test_open_gate_uses_fake_client_and_preserves_provider_metadata(self):
        panel = deepcopy(self.panel)
        panel["run_gate"]["api_calls_authorized"] = True
        client = RecordingClient({
            "content": '{"kind":"stop","status":"controlled_stop","reason":"complete"}',
            "usage": {"total_tokens": 3},
            "provider_model": "frozen-model",
        })
        old_gate = os.environ.get("EXPERTSRS_D3_LIGHT_ALLOW_API")
        os.environ["EXPERTSRS_D3_LIGHT_ALLOW_API"] = "YES"
        try:
            result = ModelDecisionAdapter(panel, client).next_step(
                build_agent_case(panel, 13, "B2_adaptive"), {"phase": "initial"}
            )
        finally:
            if old_gate is None:
                os.environ.pop("EXPERTSRS_D3_LIGHT_ALLOW_API", None)
            else:
                os.environ["EXPERTSRS_D3_LIGHT_ALLOW_API"] = old_gate
        self.assertEqual(result["kind"], "stop")
        self.assertEqual(result["usage"], {"total_tokens": 3})
        self.assertEqual(result["provider_model"], "frozen-model")
        self.assertEqual(len(client.calls), 1)

    def test_strict_json_decision_parsing(self):
        self.assertEqual(
            ModelDecisionAdapter.parse_decision({"content": '{"kind":"clarify","question":"Which metric?"}'}),
            {"kind": "clarify", "question": "Which metric?"},
        )
        with self.assertRaises(ValueError):
            ModelDecisionAdapter.parse_decision({"content": "I would call NDVI."})
        with self.assertRaises(ValueError):
            ModelDecisionAdapter.parse_decision({"content": json.dumps({"kind": "action"})})
        for response in (
            {},
            {"content": '{"kind":"action","tool":"x","plan_update":1}'},
            {"content": '{"kind":"stop","status":1}'},
            {"content": '{"kind":"clarify","question":1}'},
            {"content": '{"kind":"other"}'},
        ):
            with self.assertRaises(ValueError):
                ModelDecisionAdapter.parse_decision(response)

    def test_http_client_rejects_missing_key_and_malformed_response(self):
        settings = {"temperature": 0, "top_p": 1, "max_tokens": 10, "timeout_seconds": 1}
        with self.assertRaises(APIAuthorizationError):
            OpenAICompatibleClient("", "https://api.example/v1").complete(
                model="test", messages=[], settings=settings
            )
        with self.assertRaisesRegex(ValueError, "lacks choices"):
            OpenAICompatibleClient("secret-value", "https://api.example/v1", type(
                "MalformedSession", (), {"post": lambda self, *args, **kwargs: MalformedHttpResponse()}
            )()).complete(model="test", messages=[], settings=settings)

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
        model_env = self.panel["proposed_run_protocol"]["model_selection"]["model_env"]
        old_model = os.environ.get(model_env)
        os.environ[model_env] = "other-model"
        try:
            with self.assertRaises(APIAuthorizationError):
                configured_deepseek_client(self.panel)
        finally:
            if old_model is None:
                os.environ.pop(model_env, None)
            else:
                os.environ[model_env] = old_model

    def test_default_frozen_model_constructs_client_and_role_selection_is_bounded(self):
        selection = self.panel["proposed_run_protocol"]["model_selection"]
        model_env = selection["model_env"]
        base_url_env = selection["base_url_env"]
        old_model = os.environ.pop(model_env, None)
        old_base_url = os.environ.get(base_url_env)
        os.environ[base_url_env] = "https://llmapi.paratera.com/v1"
        try:
            client = configured_deepseek_client(self.panel)
        finally:
            if old_model is not None:
                os.environ[model_env] = old_model
            if old_base_url is None:
                os.environ.pop(base_url_env, None)
            else:
                os.environ[base_url_env] = old_base_url
        self.assertEqual(client.base_url, "https://llmapi.paratera.com/v1")
        for task_id, phase, expected_role in ((13, "initial", "Manager"), (2, "metadata", "Scientist"), (2, "recovery", "Engineer")):
            request = self.connector.build_request(
                build_agent_case(self.panel, task_id, "B2_adaptive"), {"phase": phase}
            )
            self.assertIn(expected_role, request["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
