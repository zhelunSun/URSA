"""WP2: no-network tests for explicit runtime provider identity and failures."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from ExpertsRS import ExecutionMode, ExpertsRSSystem, ProviderConfig, RunBudgets, RunRequest, RunStatus
    from ExpertsRS.provider import ProviderFailure, _role_instructions, classify_provider_exception, create_autogen_live_provider
except ModuleNotFoundError:  # Support discovery from ExpertsRS/.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ExpertsRS import ExecutionMode, ExpertsRSSystem, ProviderConfig, RunBudgets, RunRequest, RunStatus
    from ExpertsRS.provider import ProviderFailure, _role_instructions, classify_provider_exception, create_autogen_live_provider


SCENE = Path(__file__).parent / "data" / "Sentinel2_Dongcheng_20230718.tif"


class ProviderTests(unittest.TestCase):
    def test_manager_contract_requires_metric_for_vegetation_health(self):
        self.assertIn("vegetation health", _role_instructions()["Manager"])
        self.assertIn("named metric", _role_instructions()["Manager"])

    def test_role_contract_routes_named_unsupported_indices_to_scientist_stop(self):
        self.assertIn("NDSI", _role_instructions()["Manager"])
        self.assertIn("absent from available_tools", _role_instructions()["Scientist"])

    def test_role_contract_requires_metadata_before_lst_stop(self):
        self.assertIn("operation lst", _role_instructions()["Scientist"])
        self.assertIn("thermal-precondition", _role_instructions()["Engineer"])

    def test_scripted_mode_is_explicit_in_result_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = asyncio.run(ExpertsRSSystem().run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="offline",
            )))
            manifest = json.loads((root / "offline" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(result.execution_mode, ExecutionMode.SCRIPTED_OFFLINE)
        self.assertEqual(result.provider, "scripted")
        self.assertEqual(manifest["execution_mode"], "scripted-offline")
        self.assertFalse(manifest["provider"]["api_calls_permitted"])

    def test_live_mode_requires_explicit_provider_configuration(self):
        with self.assertRaises(ValueError):
            RunRequest(request="Map NDVI", data_paths=[SCENE], output_dir=Path("."), execution_mode=ExecutionMode.AUTOGEN_LIVE)

    def test_missing_key_fails_before_provider_client_construction(self):
        config = ProviderConfig(model="test-model", api_key_env="WP2_MISSING_KEY", base_url_env="WP2_BASE_URL")
        old = os.environ.pop("WP2_MISSING_KEY", None)
        os.environ["WP2_BASE_URL"] = "https://example.invalid/v1"
        try:
            with self.assertRaisesRegex(ProviderFailure, "WP2_MISSING_KEY"):
                create_autogen_live_provider(config)
        finally:
            os.environ.pop("WP2_BASE_URL", None)
            if old is not None:
                os.environ["WP2_MISSING_KEY"] = old

    def test_missing_base_url_fails_before_provider_client_construction(self):
        config = ProviderConfig(model="test-model", api_key_env="WP4_PRESENT_KEY", base_url_env="WP4_MISSING_URL")
        os.environ["WP4_PRESENT_KEY"] = "secret-value"
        old = os.environ.pop("WP4_MISSING_URL", None)
        try:
            with self.assertRaisesRegex(ProviderFailure, "WP4_MISSING_URL"):
                create_autogen_live_provider(config)
        finally:
            os.environ.pop("WP4_PRESENT_KEY", None)
            if old is not None:
                os.environ["WP4_MISSING_URL"] = old

    def test_live_manifest_never_contains_the_provider_key(self):
        class SafeProvider:
            async def decide(self, role, state):
                return {
                    "kind": "clarify", "question": "Which output is needed?",
                    "_provider_usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
                }

        config = ProviderConfig(model="test-model", api_key_env="WP2_KEY", base_url_env="WP2_URL")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = asyncio.run(ExpertsRSSystem(provider=SafeProvider()).run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="live",
                execution_mode=ExecutionMode.AUTOGEN_LIVE, provider=config,
            )))
            run_text = "\n".join(path.read_text(encoding="utf-8") for path in (root / "live").glob("*.json*"))
        self.assertEqual(result.execution_mode, ExecutionMode.AUTOGEN_LIVE)
        self.assertEqual(result.provider, "openai-compatible")
        self.assertNotIn("WP2_KEY", run_text)
        self.assertNotIn("secret-value", run_text)

    def test_model_views_and_manifest_exclude_paths_metadata_keys_and_fixture_labels(self):
        from ExpertsRS.decisions import ScriptedDecisionProvider

        class CapturingProvider:
            def __init__(self):
                self.delegate = ScriptedDecisionProvider()
                self.views = []

            async def decide(self, role, state):
                self.views.append(json.loads(json.dumps(state)))
                return await self.delegate.decide(role, state)

        provider = CapturingProvider()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = asyncio.run(ExpertsRSSystem(provider=provider).run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="redacted",
            )))
            manifest = json.loads((root / "redacted" / "manifest.json").read_text(encoding="utf-8"))
        serialized_views = json.dumps(provider.views)
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertTrue(all(view["input_data_available"] for view in provider.views))
        self.assertTrue(all(view["input_data_count"] == 1 for view in provider.views))
        self.assertNotIn(str(SCENE), serialized_views)
        self.assertNotIn("output_path", serialized_views)
        self.assertNotIn("fixture", serialized_views)
        self.assertIn("artifact_id", serialized_views)
        self.assertTrue(manifest["provider"]["code_commit"])
        self.assertTrue(manifest["provider"]["prompt_hash"])
        self.assertTrue(manifest["provider"]["panel_hash"])

    def test_provider_timeout_and_api_error_have_distinct_sanitized_codes(self):
        self.assertEqual(classify_provider_exception(TimeoutError()).code, "provider_timeout")
        self.assertEqual(classify_provider_exception(ConnectionError()).code, "provider_api_error")
        self.assertEqual(classify_provider_exception(ValueError()).code, "provider_response_error")

    def test_provider_construction_is_no_network_and_initialization_failure_is_sanitized(self):
        config = ProviderConfig(model="test-model", api_key_env="WP4_KEY", base_url_env="WP4_URL")
        os.environ["WP4_KEY"] = "secret-value"
        os.environ["WP4_URL"] = "https://example.invalid/v1"
        try:
            provider = create_autogen_live_provider(config)
            self.assertIn("Manager", provider.agents)
            client_config = provider.model_client._raw_config
            self.assertEqual(client_config["timeout"], config.timeout_seconds)
            self.assertEqual(client_config["max_retries"], 0)
            self.assertEqual(client_config["max_tokens"], config.max_completion_tokens)
            with patch("autogen_ext.models.openai.OpenAIChatCompletionClient", side_effect=RuntimeError("secret-value")):
                with self.assertRaisesRegex(ProviderFailure, "RuntimeError") as captured:
                    create_autogen_live_provider(config)
            self.assertNotIn("secret-value", str(captured.exception))
        finally:
            os.environ.pop("WP4_KEY", None)
            os.environ.pop("WP4_URL", None)

    def test_live_manifest_freezes_sampling_retry_cache_and_token_limits(self):
        class SafeProvider:
            async def decide(self, role, state):
                return {"kind": "clarify", "question": "Which output is needed?"}

        config = ProviderConfig(model="test-model", max_completion_tokens=321)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asyncio.run(ExpertsRSSystem(provider=SafeProvider()).run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="limits",
                execution_mode=ExecutionMode.AUTOGEN_LIVE, provider=config,
            )))
            manifest = json.loads((root / "limits" / "manifest.json").read_text(encoding="utf-8"))
        provider_manifest = manifest["provider"]
        self.assertEqual(provider_manifest["temperature"], 0)
        self.assertEqual(provider_manifest["max_completion_tokens"], 321)
        self.assertEqual(provider_manifest["max_retries"], 0)
        self.assertFalse(provider_manifest["cache_enabled"])

    def test_provider_failure_preserves_partial_trace_without_fallback(self):
        class TimeoutProvider:
            async def decide(self, role, state):
                raise ProviderFailure("provider_timeout", "The provider request timed out.")

        config = ProviderConfig(model="test-model", api_key_env="WP4_KEY", base_url_env="WP4_URL")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = asyncio.run(ExpertsRSSystem(provider=TimeoutProvider()).run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="timeout",
                execution_mode=ExecutionMode.AUTOGEN_LIVE, provider=config,
            )))
            trace = result.trace_path.read_text(encoding="utf-8")
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(result.validation.tool_calls, 0)
        self.assertIn("provider_timeout", trace)

    def test_global_and_role_budgets_stop_with_explicit_terminal_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            global_stop = asyncio.run(ExpertsRSSystem().run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="global",
                budgets=RunBudgets(max_model_turns=2),
            )))
            role_stop = asyncio.run(ExpertsRSSystem().run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="role",
                budgets=RunBudgets(max_model_turns=12, max_tool_calls_engineer=0),
            )))
            global_trace = global_stop.trace_path.read_text(encoding="utf-8")
            role_trace = role_stop.trace_path.read_text(encoding="utf-8")
        self.assertEqual(global_stop.status, RunStatus.CONTROLLED_STOP)
        self.assertIn("model_turn_budget_exhausted", global_trace)
        self.assertEqual(role_stop.status, RunStatus.CONTROLLED_STOP)
        self.assertIn("engineer_tool_budget_exhausted", role_trace)


if __name__ == "__main__":
    unittest.main(verbosity=2)
