"""Offline regressions for NDVI delivery identity and legacy input admission."""
import asyncio
import copy
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from ExpertsRS import ExpertsRSSystem, RunRequest, RunStatus
from ExpertsRS.decisions import ScriptedDecisionProvider
from ExpertsRS.workflow.obligations import derive_delivery_obligations, validate_plan_obligations
import ExpertsRS.system as runtime


@pytest.fixture
def scene(tmp_path):
    path = tmp_path / "inputs" / "scene.tif"
    path.parent.mkdir()
    with rasterio.open(path, "w", driver="GTiff", height=4, width=4, count=2,
                       dtype="float32", crs="EPSG:32650", transform=from_origin(0, 40, 10, 10)) as dst:
        dst.write(np.stack([np.full((4, 4), 2), np.full((4, 4), 6)]).astype("float32"))
        dst.set_band_description(1, "B4")
        dst.set_band_description(2, "B8")
    return path


def ndvi_plan(*, metadata=True):
    task, workflow = ScriptedDecisionProvider._workflow("ndvi", "Map NDVI")
    if not metadata:
        workflow["nodes"] = workflow["nodes"][1:]
        workflow["nodes"][0]["depends_on"] = []
        task["expected_outputs"].remove("metadata")
    return {"kind": "plan", "task": task, "workflow": workflow}


def compute_only():
    proposal = ndvi_plan(metadata=False)
    proposal["workflow"]["nodes"] = proposal["workflow"]["nodes"][:1]
    proposal["task"]["expected_outputs"] = ["index_raster"]
    proposal["task"]["requested_outputs"] = []
    return proposal


class FixedPlan(ScriptedDecisionProvider):
    def __init__(self, proposal):
        self.proposal = proposal

    async def decide(self, role, state):
        if role == "Scientist":
            return copy.deepcopy(self.proposal)
        return await super().decide(role, state)


class SpyExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, tool_name, arguments, output_dir):
        self.calls.append((tool_name, arguments))
        return {"success": False, "data": None, "error_code": "permission_denied",
                "message": "Synthetic spy stopped before tool execution"}


def request(scene, tmp_path, *, goal="Map NDVI", run_id="case"):
    return RunRequest(request=goal, data_paths=[scene], output_dir=tmp_path / "runs", run_id=run_id)


@pytest.mark.parametrize("operator,artifact_type", [
    ("expertsrs.read_raster_metadata.v1", "metadata"),
    ("expertsrs.calculate_ndvi.v1", "index_raster"),
])
def test_node_named_index_map_cannot_substitute_for_an_ndvi_map(scene, tmp_path, operator, artifact_type):
    proposal = compute_only()
    proposal["task"].update(expected_outputs=[artifact_type], requested_outputs=["ndvi_map"])
    proposal["workflow"]["nodes"][0].update(node_id="index_map", operator_id=operator)
    result = asyncio.run(ExpertsRSSystem(provider=FixedPlan(proposal)).run(request(scene, tmp_path)))
    assert result.status == RunStatus.CONTROLLED_STOP
    assert result.validation.tool_calls == 0


def test_ndvi_map_obligation_requires_a_real_ndvi_producer():
    proposal = ndvi_plan(metadata=False)
    proposal["workflow"]["nodes"] = proposal["workflow"]["nodes"][1:]
    proposal["workflow"]["nodes"][0].update(inputs={"file_path": "input_raster"}, depends_on=[])
    proposal["workflow"]["input_artifacts"][0]["artifact_type"] = "index_raster"
    obligations = [item.to_dict() for item in derive_delivery_obligations("Map NDVI")]
    with pytest.raises(ValueError, match="NDVI"):
        validate_plan_obligations(obligations, proposal["task"], proposal["workflow"])


@pytest.mark.parametrize("corruption", ["map_type", "index_type", "producer", "stale_binding", "pending"])
def test_report_facts_require_current_successful_map_and_index_evidence(corruption):
    proposal = ndvi_plan(metadata=False)
    records = [
        {"artifact_id": "index", "artifact_type": "index_raster", "validated": True, "producer_plan_node_id": "ndvi"},
        {"artifact_id": "map", "artifact_type": "map", "validated": True, "producer_plan_node_id": "index_map"},
    ]
    state = {"planned_graph": proposal, "artifacts": records,
             "node_states": {"ndvi": "succeeded", "index_map": "succeeded"},
             "workflow_artifact_records": {"ndvi_raster": "index", "ndvi_map": "map"},
             "delivery_obligations": [o.to_dict() for o in derive_delivery_obligations("Map NDVI")]}
    if corruption == "map_type":
        records[1]["artifact_type"] = "metadata"
    elif corruption == "index_type":
        records[0]["artifact_type"] = "metadata"
    elif corruption == "producer":
        records[1]["producer_plan_node_id"] = "other_node"
    elif corruption == "stale_binding":
        state["workflow_artifact_records"]["ndvi_map"] = "nonexistent"
    else:
        state["node_states"]["index_map"] = "pending"
    assert ExpertsRSSystem()._report_deliverables(state) == []


@pytest.mark.parametrize("metadata", [True, False])
def test_real_ndvi_chain_delivers_correct_pixels_and_map(scene, tmp_path, metadata):
    result = asyncio.run(ExpertsRSSystem(provider=FixedPlan(ndvi_plan(metadata=metadata)),
                                       allowed_data_roots=[scene.parent]).run(request(scene, tmp_path)))
    assert result.status == RunStatus.COMPLETED
    assert result.validation.tool_calls == (3 if metadata else 2)
    assert "ndvi_map: delivered" in result.report
    index = next(a for a in result.artifacts if a.artifact_type == "index_raster")
    assert any(a.artifact_type == "map" and Path(a.uri).is_file() for a in result.artifacts)
    with rasterio.open(index.uri) as dataset:
        np.testing.assert_allclose(dataset.read(1), 0.5)


@pytest.mark.parametrize("path_form", ["direct", "traversal", "sibling_prefix", "second_input"])
def test_outside_input_rejected_before_any_preflight_or_raster_read(scene, tmp_path, monkeypatch, path_form):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source = scene
    paths = [source]
    if path_form == "traversal":
        paths = [allowed / ".." / "inputs" / "scene.tif"]
    elif path_form == "sibling_prefix":
        allowed = tmp_path / "input"
        allowed.mkdir()
    elif path_form == "second_input":
        valid = allowed / "valid.tif"
        valid.write_bytes(source.read_bytes())
        paths = [valid, source]
    open_spy = Mock(wraps=rasterio.open)
    preflight_spy = Mock(wraps=runtime.validate_workflow)
    monkeypatch.setattr(rasterio, "open", open_spy)
    monkeypatch.setattr(runtime, "validate_workflow", preflight_spy)
    executor = SpyExecutor()
    system = ExpertsRSSystem(provider=FixedPlan(compute_only()), executor=executor, allowed_data_roots=[allowed])
    req = RunRequest(request="Compute NDVI", data_paths=paths, output_dir=tmp_path / "runs", run_id="outside")
    result = asyncio.run(system.run(req))
    assert result.status == RunStatus.CONTROLLED_STOP
    assert open_spy.call_count == 0
    assert preflight_spy.call_count == 0
    assert result.validation.model_turns == result.validation.tool_calls == 0
    assert executor.calls == []


def test_input_scope_is_rechecked_before_plan_preflight(scene, tmp_path, monkeypatch):
    system = ExpertsRSSystem(allowed_data_roots=[scene.parent])
    req = request(scene, tmp_path, goal="Compute NDVI")
    state = system._initial_state(req, "case", system._new_run_dir(req.output_dir, "case"))
    state["allowed_data_roots"] = [str(tmp_path / "other")]
    preflight = Mock(side_effect=AssertionError("Input was inspected before admission"))
    monkeypatch.setattr(runtime, "validate_workflow", preflight)
    with pytest.raises(ValueError, match="allowed data roots"):
        system._accept_plan(state, compute_only())
    assert preflight.call_count == 0


def test_input_scope_is_rechecked_before_tool_execution(scene, tmp_path):
    executor = SpyExecutor()
    system = ExpertsRSSystem(executor=executor, allowed_data_roots=[scene.parent])
    req = request(scene, tmp_path, goal="Compute NDVI")
    state = system._initial_state(req, "case", system._new_run_dir(req.output_dir, "case"))
    system._accept_plan(state, compute_only())
    state["allowed_data_roots"] = [str(tmp_path / "other")]
    observation = system._execute_action(state, {"kind": "action", "node_id": "ndvi"})
    assert observation["error_code"] == "permission_denied"
    assert state["tool_calls"] == 0
    assert executor.calls == []
