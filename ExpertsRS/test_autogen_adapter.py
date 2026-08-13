"""integration: compatibility checks for the pinned modern AutoGen boundary."""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest

try:
    from ExpertsRS import ExpertsRSSystem, RunRequest, RunStatus
    from ExpertsRS.decisions import AutoGenSelectorDecisionProvider
except ModuleNotFoundError:  # Support discovery from ExpertsRS/.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ExpertsRS import ExpertsRSSystem, RunRequest, RunStatus
    from ExpertsRS.decisions import AutoGenSelectorDecisionProvider


class AutoGenAdapterTests(unittest.TestCase):
    @staticmethod
    def _client(response: str | None = None):
        from autogen_core.models import ChatCompletionClient, CreateResult, RequestUsage

        class MinimalClient(ChatCompletionClient):
            @property
            def model_info(self):
                return {"vision": False, "function_calling": False, "json_output": False, "family": "unknown", "structured_output": False}

            @property
            def capabilities(self):
                return self.model_info

            async def create(self, *args, **kwargs):
                if response is None:
                    raise AssertionError("No model request expected in adapter construction test")
                return CreateResult(
                    finish_reason="stop", content=response,
                    usage=RequestUsage(prompt_tokens=1, completion_tokens=1), cached=False,
                )

            async def create_stream(self, *args, **kwargs):  # pragma: no cover
                if False:
                    yield None

            async def close(self):
                return None

            def actual_usage(self):
                return None

            def total_usage(self):
                return None

            def count_tokens(self, messages, *, tools=None):
                return 0

            def remaining_tokens(self, messages, *, tools=None):
                return 1

        return MinimalClient()

    def test_modern_team_is_constructed_and_state_is_portable(self):
        provider = AutoGenSelectorDecisionProvider.create(self._client(), {
            "Manager": "Return JSON decisions.",
            "Scientist": "Return JSON decisions.",
            "Engineer": "Return JSON decisions.",
        })
        state = asyncio.run(provider.save_state())
        self.assertIn("agent_states", state)
        asyncio.run(provider.load_state(state))

    def test_role_decision_runs_through_selector_group_chat(self):
        provider = AutoGenSelectorDecisionProvider.create(self._client('{"kind":"handoff","target":"Scientist"}'), {
            "Manager": "Return JSON decisions.",
            "Scientist": "Return JSON decisions.",
            "Engineer": "Return JSON decisions.",
        })
        decision = asyncio.run(provider.decide("Manager", {"request": "NDVI", "phase": "initial"}))
        self.assertEqual(decision, {"kind": "handoff", "target": "Scientist"})
        state = asyncio.run(provider.save_state())
        self.assertTrue(state["agent_states"]["manager"]["agent_state"]["llm_context"]["messages"])

    def test_unified_runtime_persists_actual_team_state(self):
        responses = iter([
            '{"kind":"handoff","target":"Scientist"}',
            '{"kind":"plan","operation":"ndvi","next_action":"read_raster_metadata"}',
            '{"kind":"action","tool_name":"read_raster_metadata"}',
            '{"kind":"action","tool_name":"calculate_ndvi"}',
            '{"kind":"action","tool_name":"plot_index_map","artifact_refs":["team:action:02:index_raster"]}',
            '{"kind":"handoff","target":"Manager"}',
        ])

        class SequencedClient(type(self._client("{}"))):
            async def create(self, *args, **kwargs):
                from autogen_core.models import CreateResult, RequestUsage
                return CreateResult(
                    finish_reason="stop", content=next(responses),
                    usage=RequestUsage(prompt_tokens=1, completion_tokens=1), cached=False,
                )

        provider = AutoGenSelectorDecisionProvider.create(SequencedClient(), {
            "Manager": "Return JSON decisions.",
            "Scientist": "Return JSON decisions.",
            "Engineer": "Return JSON decisions.",
        })
        import json
        import tempfile
        scene = Path(__file__).parent / "data" / "Sentinel2_Dongcheng_20230718.tif"
        with tempfile.TemporaryDirectory() as directory:
            result = asyncio.run(ExpertsRSSystem(provider=provider).run(RunRequest(
                request="Map NDVI", data_paths=[scene], output_dir=Path(directory), run_id="team",
            )))
            state = json.loads((Path(directory) / "team" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertIn("provider_state", state)
        self.assertIn("agent_states", state["provider_state"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
