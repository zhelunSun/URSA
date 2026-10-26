"""Behavioral tests for the chapter boundary, process continuation and live events."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from ExpertsRS.analysis_plan import AnalysisPlan
from ExpertsRS.decisions import ScriptedDecisionProvider
from ExpertsRS.events import read_events, run_lease
from ExpertsRS.models import ExecutionMode, ProviderConfig, RunRequest
from ExpertsRS.system import ExpertsRSSystem, LocalToolExecutor
from ExpertsRS.test_domain_runtime import domain_request
from ExpertsRS.test_runtime_delivery_input_guards import scene


def run(request, system=None):
    return asyncio.run((system or ExpertsRSSystem()).run(request))


def waiting_request(scene, tmp_path, **kwargs):
    return RunRequest(request="Assess vegetation health", data_paths=[scene],
                      output_dir=tmp_path / "runs", run_id="waiting", **kwargs)


def plan_for(request, **changes):
    fields = dict(plan_id="resource-test", revision="r1", original_goal="Resource demand",
                  execution_goal=request.request, aoi="test AOI", year=request.product_year,
                  required_deliverables=("class_composition", "classification_map"),
                  conditions=("Classified pixels only",), limitations=("Not a true-area estimate",),
                  deferred_requirements=("Independent accuracy",),
                  sources=({"source_id":"fixture", "sha256":"0"*64},))
    fields.update(changes)
    return AnalysisPlan(**fields)


def test_fresh_instance_resume_preserves_prefix_and_clears_question(scene, tmp_path):
    request = waiting_request(scene, tmp_path)
    first = run(request)
    prefix = first.trace_path.read_bytes()
    cursor = read_events(request.output_dir, first.run_id)["cursor"]
    resumed = asyncio.run(ExpertsRSSystem().resume(first.run_id, "Map NDVI", request.output_dir))
    assert resumed.status == "completed" and resumed.questions == []
    assert resumed.trace_path.read_bytes().startswith(prefix)
    new = read_events(request.output_dir, first.run_id, after=cursor)
    assert new["events"][0]["event_type"] == "user_clarification_received"
    assert new["cursor"] > cursor
    assert read_events(request.output_dir, first.run_id, after=new["cursor"])["events"] == []


def test_new_cli_process_can_resume(scene, tmp_path):
    request = waiting_request(scene, tmp_path)
    first = run(request)
    command = [sys.executable, "-B", "-m", "ExpertsRS", "resume", "--run-id", first.run_id,
               "--answer", "Map NDVI", "--output-dir", str(request.output_dir)]
    result = subprocess.run(command, cwd=Path(__file__).parents[1], capture_output=True, text=True,
                            encoding="utf-8", timeout=45)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["status"] == "completed"


def test_changed_input_rejected_without_consuming_checkpoint(scene, tmp_path):
    request = waiting_request(scene, tmp_path)
    run(request)
    state_path = request.output_dir / "waiting/state.json"
    before = state_path.read_bytes()
    scene.write_bytes(scene.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="identity"):
        asyncio.run(ExpertsRSSystem().resume("waiting", "Map NDVI", request.output_dir))
    assert state_path.read_bytes() == before


def test_injected_provider_is_not_silently_replaced(scene, tmp_path):
    class Custom(ScriptedDecisionProvider):
        pass
    request = waiting_request(scene, tmp_path)
    run(request, ExpertsRSSystem(provider=Custom()))
    with pytest.raises(ValueError, match="injected"):
        asyncio.run(ExpertsRSSystem().resume("waiting", "Map NDVI", request.output_dir))
    resumed = asyncio.run(ExpertsRSSystem(provider=Custom()).resume("waiting", "Map NDVI", request.output_dir))
    assert resumed.status == "completed"


@pytest.mark.parametrize("custom_bindings", [False, True])
def test_live_config_and_provider_state_reconstructed_without_network(scene, tmp_path, monkeypatch, custom_bindings):
    created = []
    class FakeLive(ScriptedDecisionProvider):
        restored = None
        async def decide(self, role, state):
            result = await super().decide(role, state)
            result["_provider_usage"] = {"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}
            return result
        async def save_state(self):
            return {"conversation":"saved"}
        async def load_state(self, state):
            self.restored = state
    def factory(request):
        provider = FakeLive()
        created.append((request.provider, provider))
        return provider
    monkeypatch.setattr(ExpertsRSSystem, "_provider_for_request", staticmethod(factory))
    config = ProviderConfig(model="test-model", **({"api_key_env":"TEST_KEY_NAME", "base_url_env":"TEST_URL_NAME"} if custom_bindings else {}))
    request = waiting_request(scene, tmp_path, execution_mode=ExecutionMode.AUTOGEN_LIVE, provider=config)
    run(request)
    if custom_bindings:
        with pytest.raises(ValueError, match="original provider configuration"):
            asyncio.run(ExpertsRSSystem().resume("waiting", "Map NDVI", request.output_dir))
    resumed = asyncio.run(ExpertsRSSystem().resume("waiting", "Map NDVI", request.output_dir,
                                                  provider_config=config if custom_bindings else None))
    assert resumed.status == "completed"
    assert created[0][0] == created[1][0] == config
    persisted = (request.output_dir/"waiting"/"state.json").read_text(encoding="utf-8")
    assert "TEST_KEY_NAME" not in persisted and "TEST_URL_NAME" not in persisted
    assert created[1][1].restored == {"conversation":"saved"}


def test_event_reader_observes_tool_start_before_tool_returns(scene, tmp_path):
    request = RunRequest(request="Map NDVI",data_paths=[scene],output_dir=tmp_path,run_id="events")
    observations = []
    class InspectingExecutor(LocalToolExecutor):
        def execute(self, tool_name, arguments, output_dir):
            packet = read_events(tmp_path, "events")
            observations.append(packet)
            assert packet["events"][-1]["event_type"] == "action_started"
            return super().execute(tool_name, arguments, output_dir)
    result = run(request, ExpertsRSSystem(executor=InspectingExecutor()))
    assert result.status == "completed" and len(observations) == 3
    assert observations[0]["cursor"] < observations[-1]["cursor"]


def test_cursor_and_path_contract(tmp_path):
    with pytest.raises(ValueError):
        read_events(tmp_path, "../escape")
    with pytest.raises(ValueError):
        read_events(tmp_path, "case", after=-1)
    with pytest.raises(ValueError, match="ahead"):
        read_events(tmp_path, "case", after=1)
    directory=tmp_path/"case"; directory.mkdir()
    (directory/"trace.jsonl").write_text('{"unfinished":',encoding="utf-8")
    assert read_events(tmp_path,"case")["cursor"] == 0
    (directory/"trace.jsonl").write_bytes(b'{"unfinished":"\xe5\x9f')
    assert read_events(tmp_path,"case")["cursor"] == 0
    with run_lease(directory):
        with pytest.raises(ValueError, match="active"):
            with run_lease(directory):
                pass


def test_frozen_plan_is_delivered_as_partial_and_pinned(domain_request):
    plan = plan_for(domain_request)
    request = RunRequest.model_validate({**domain_request.model_dump(),"analysis_plan":plan})
    result = run(request)
    assert result.status == "partial"
    assert len(result.artifacts) == 2
    assert "Independent accuracy" in result.report
    state=json.loads((request.output_dir/result.run_id/"state.json").read_text(encoding="utf-8"))
    assert state["analysis_plan_sha256"] == plan.fingerprint()
    assert AnalysisPlan.model_validate(state["analysis_plan"]) == plan


def test_incompatible_schema_goal_or_year_rejected(domain_request):
    plan=plan_for(domain_request)
    for changes in ({"product_year":2024},{"request":"Silently different goal"}):
        with pytest.raises(ValueError):
            RunRequest.model_validate({**domain_request.model_dump(),"analysis_plan":plan,**changes})
    with pytest.raises(ValidationError):
        AnalysisPlan.model_validate({**plan.model_dump(),"schema_version":"analysis-plan-v2"})


def test_planner_cannot_rewrite_frozen_goal(domain_request):
    class Drifting(ScriptedDecisionProvider):
        async def decide(self,role,state):
            decision=await super().decide(role,state)
            if role=="Scientist":
                decision["task"]["goal"]="Different information goal"
            return decision
    request=RunRequest.model_validate({**domain_request.model_dump(),"analysis_plan":plan_for(domain_request)})
    result=run(request,ExpertsRSSystem(provider=Drifting()))
    assert result.status == "controlled_stop" and result.validation.tool_calls == 0
