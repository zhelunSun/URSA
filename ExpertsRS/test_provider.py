"""WP2: no-network tests for explicit runtime provider identity and failures."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

try:
    from ExpertsRS import ExecutionMode, ExpertsRSSystem, ProviderConfig, RunRequest
    from ExpertsRS.provider import ProviderFailure, create_autogen_live_provider
except ModuleNotFoundError:  # Support discovery from ExpertsRS/.
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ExpertsRS import ExecutionMode, ExpertsRSSystem, ProviderConfig, RunRequest
    from ExpertsRS.provider import ProviderFailure, create_autogen_live_provider


SCENE = Path(__file__).parent / "data" / "Sentinel2_Dongcheng_20230718.tif"


class ProviderTests(unittest.TestCase):
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

    def test_live_manifest_never_contains_the_provider_key(self):
        class SafeProvider:
            async def decide(self, role, state):
                return {"kind": "clarify", "question": "Which output is needed?"}

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
