"""Domain integration boundaries, with generated fixtures kept outside evidence."""
import asyncio
import importlib.util
import json
import tempfile
from pathlib import Path

import pytest

from ExpertsRS.decisions import ScriptedDecisionProvider
from ExpertsRS.models import InputResource, RunRequest, RuntimeCapabilities
from ExpertsRS.system import ExpertsRSSystem, LocalToolExecutor


@pytest.fixture
def domain_request(tmp_path):
    if not importlib.util.find_spec("shapely") or not importlib.util.find_spec("shapefile"):
        pytest.skip("domain optional dependencies are not installed")
    import numpy as np
    import rasterio
    import shapefile
    from rasterio.transform import from_origin
    raster = tmp_path / "classification.tif"
    with rasterio.open(raster, "w", driver="GTiff", width=4, height=4, count=1,
                       dtype="uint8", crs="EPSG:4326", transform=from_origin(0, 4, 1, 1), nodata=255) as dst:
        dst.write(np.arange(16, dtype=np.uint8).reshape(4, 4) % 8, 1)
    aoi = tmp_path / "study.shp"
    with shapefile.Writer(str(aoi)) as writer:
        writer.field("id", "N")
        writer.poly([[(0, 0), (0, 4), (4, 4), (4, 0), (0, 0)]])
        writer.record(1)
    aoi.with_suffix(".prj").write_text(rasterio.crs.CRS.from_epsg(4326).to_wkt())
    return RunRequest(request="Describe the classified product in the study area with composition and map",
        output_dir=tmp_path / "runs", domain_profile="classification-v1",
        input_resources={"classification": InputResource(path=raster, artifact_type="raster"),
                         "study_area": InputResource(path=aoi, artifact_type="aoi")})


def test_helper_functions_are_not_public_tools():
    from ExpertsRS.tools.registry import get_tool_by_name, list_tools
    assert len(list_tools()) == 18
    assert get_tool_by_name("current_output_directory") is None


def test_missing_output_cannot_be_success(tmp_path):
    class LyingExecutor(LocalToolExecutor):
        def execute(self, tool_name, arguments, output_dir):
            if tool_name == "calculate_ndvi":
                return {"success": True, "message": "done", "data": {"output_path": str(output_dir / "absent.tif")}}
            return super().execute(tool_name, arguments, output_dir)
    request = RunRequest(request="Map NDVI", data_paths=[Path(__file__).parent / "data/Sentinel2_Dongcheng_20230718.tif"],
        output_dir=tmp_path, capabilities=RuntimeCapabilities(allow_plan_revision=False))
    result = asyncio.run(ExpertsRSSystem(executor=LyingExecutor()).run(request))
    assert result.status == "controlled_stop"
    assert len(result.artifacts) == 1
    assert "artifact_rejected" in result.trace_path.read_text(encoding="utf-8")


def test_out_of_scope_input_rejected_before_decision(domain_request, tmp_path):
    with pytest.raises(ValueError, match="outside allowed"):
        asyncio.run(ExpertsRSSystem(allowed_data_roots=[tmp_path / "unrelated"]).run(domain_request))


def test_foreign_output_cannot_be_registered(tmp_path):
    outside = tmp_path / "foreign.tif"
    outside.write_bytes(b"not this run's output")
    class ForeignOutput(LocalToolExecutor):
        def execute(self, tool_name, arguments, output_dir):
            if tool_name == "calculate_ndvi":
                return {"success": True, "message": "done", "data": {"output_path": str(outside)}}
            return super().execute(tool_name, arguments, output_dir)
    request = RunRequest(request="Map NDVI", data_paths=[Path(__file__).parent / "data/Sentinel2_Dongcheng_20230718.tif"],
        output_dir=tmp_path / "runs", capabilities=RuntimeCapabilities(allow_plan_revision=False))
    result = asyncio.run(ExpertsRSSystem(executor=ForeignOutput()).run(request))
    assert result.status == "controlled_stop"
    assert all(a.uri != outside for a in result.artifacts)
    assert outside.read_bytes() == b"not this run's output"


def test_changed_composition_stops_before_map(domain_request):
    class TamperTable(ScriptedDecisionProvider):
        async def decide(self, role, state):
            if role == "Engineer" and state.get("eligible_node_ids") == ["classification_map"]:
                path = next(domain_request.output_dir.rglob("classification_summary_2025.json"))
                data = json.loads(path.read_text(encoding="utf-8"))
                data["data"]["counts"]["tree"] += 1
                path.write_text(json.dumps(data), encoding="utf-8")
            return await super().decide(role, state)
    result = asyncio.run(ExpertsRSSystem(provider=TamperTable()).run(domain_request))
    assert result.status == "controlled_stop" and result.validation.tool_calls == 1


def test_plan_cannot_relabel_caller_resource(domain_request):
    class Relabel(ScriptedDecisionProvider):
        async def decide(self, role, state):
            decision = await super().decide(role, state)
            if role == "Scientist":
                decision["workflow"]["input_artifacts"][0]["artifact_type"] = "aoi"
            return decision
    result = asyncio.run(ExpertsRSSystem(provider=Relabel()).run(domain_request))
    assert result.status == "controlled_stop" and result.validation.tool_calls == 0


def test_changed_source_stops_before_second_tool(domain_request):
    class MutateSource(ScriptedDecisionProvider):
        async def decide(self, role, state):
            if role == "Engineer" and state.get("eligible_node_ids") == ["classification_map"]:
                domain_request.input_resources["classification"].path.write_bytes(b"changed")
            return await super().decide(role, state)
    result = asyncio.run(ExpertsRSSystem(provider=MutateSource()).run(domain_request))
    assert result.status == "controlled_stop" and result.validation.tool_calls == 1


def test_real_domain_chain_and_model_view_isolation(domain_request):
    views = []
    class Recording(ScriptedDecisionProvider):
        async def decide(self, role, state):
            views.append(json.dumps(state))
            return await super().decide(role, state)
    result = asyncio.run(ExpertsRSSystem(provider=Recording()).run(domain_request))
    assert result.status == "completed", result.model_dump()
    assert result.execution_mode == "scripted-offline"
    assert result.validation.tool_calls == 2
    assert {a.artifact_type for a in result.artifacts} == {"composition_table", "map"}
    table = next(a for a in result.artifacts if a.artifact_type == "composition_table")
    assert table.metadata["valid_pixels"] == 16
    assert list(table.metadata["counts"].values()) == [2] * 8
    assert all(a.uri.is_file() for a in result.artifacts)
    assert str(domain_request.input_resources["classification"].path) not in "".join(views)
    assert "reference.json" not in "".join(views)
    assert "不是面积" in result.report


def test_live_domain_profile_is_not_silently_enabled(domain_request):
    from ExpertsRS.models import ProviderConfig
    with pytest.raises(ValueError, match="offline engineering"):
        RunRequest(**{**domain_request.model_dump(), "execution_mode": "autogen-live", "provider": ProviderConfig(model="unused")})
