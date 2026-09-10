import asyncio
import copy
import json
from pathlib import Path

import pytest

from ExpertsRS.classification_bridge import (factual_deliverables, file_hash, invoke, make_record,
                                            public_facts, resolve_arguments, validate_final)
from ExpertsRS.classification_comparison import ClassificationComparisonSystem, run_single
from ExpertsRS.decisions import ScriptedDecisionProvider
from ExpertsRS.models import RunRequest
from ExpertsRS.system import ExpertsRSSystem, LocalToolExecutor
from ExpertsRS.test_domain_runtime import domain_request


def packet_for(request):
    return {"request":request.request,"product_year":request.product_year,
            "resources":[{"resource_id":k,**{field:value for field,value in v.items() if field != "path"}} for k,v in resources_for(request).items()],
            "deliverables":["class_counts"]}


def resources_for(request):
    result = {}
    for key, resource in request.input_resources.items():
        result[key] = {"path":str(resource.path),"artifact_type":resource.artifact_type,"sha256":file_hash(resource.path)}
        if resource.artifact_type == "aoi":
            result[key]["components"] = {suffix:file_hash(resource.path.with_suffix(suffix)) for suffix in (".shp",".shx",".dbf",".prj")}
    return result


class ScriptedSingle:
    async def decide(self, role, view):
        artifacts = view["available_artifacts"]
        if not artifacts:
            d = {"kind":"tool","tool":"summarize_classification","inputs":{"file_path":"classification","aoi_path":"study_area"},"parameters":{"year":2025}}
        elif len(artifacts) == 1:
            d = {"kind":"tool","tool":"plot_classification_map","inputs":{"file_path":"classification","aoi_path":"study_area","composition_path":artifacts[0]["artifact_id"]},"parameters":{"year":2025}}
        else:
            d = {"kind":"final","answer":"Existing product composition, valid pixel denominator.",
                 "artifact_refs":[a["artifact_id"] for a in artifacts],"deliverables":view["factual_deliverables"]}
        return {**d,"_provider_usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}


def test_both_runners_use_real_shared_tools_and_equal_numeric_facts(domain_request):
    request = RunRequest(**{**domain_request.model_dump(),"classification_admission":"ch3-k0-dev-v1"})
    packet = packet_for(request)
    system = ClassificationComparisonSystem(packet, ScriptedDecisionProvider())
    result = asyncio.run(system.run(request))
    assert result.status == "completed", result.model_dump()
    u = json.loads((result.trace_path.parent/"state.json").read_text(encoding="utf-8"))
    g = asyncio.run(run_single(packet,resources_for(request),request.output_dir/"single",ScriptedSingle(),request.budgets.model_dump()))
    assert g["status"] == "completed", g
    assert g["tool_calls"] == result.validation.tool_calls == 2
    assert public_facts(u)[0]["facts"] == public_facts(g)[0]["facts"]
    assert list(public_facts(g)[0]["facts"]["counts"].values()) == [2]*8
    assert str(request.input_resources["classification"].path) not in json.dumps(public_facts(g))
    validate_final(g,[a["artifact_id"] for a in g["artifacts"]],factual_deliverables(g))
    Path(g["artifacts"][0]["uri"]).write_bytes(b"changed")
    with pytest.raises(ValueError,match="changed"):
        validate_final(g,[a["artifact_id"] for a in g["artifacts"]],factual_deliverables(g))


def test_missing_aoi_reaches_manager_without_calling_tools(domain_request):
    request = RunRequest(**{**domain_request.model_dump(),"classification_admission":"ch3-k0-dev-v1",
                           "input_resources":{"classification":domain_request.input_resources["classification"]}})
    class Clarify:
        async def decide(self,role,view):
            assert role == "Manager"
            assert [r["artifact_id"] for r in view["input_resources"]] == ["classification"]
            return {"kind":"clarify","question":"Which study area boundary should be used?"}
    result = asyncio.run(ClassificationComparisonSystem(packet_for(request),Clarify()).run(request))
    assert result.status == "needs_clarification" and result.validation.tool_calls == 0


def test_shared_boundary_refuses_missing_aoi_wrong_parameters_and_foreign_output(domain_request):
    state = {"product_year":2025,"run_dir":str(domain_request.output_dir),"input_resources":resources_for(domain_request),
             "allowed_data_roots":[str(domain_request.output_dir.parent)],"artifacts":[]}
    inputs={"file_path":"classification","aoi_path":"study_area"}
    with pytest.raises(ValueError,match="year"):
        resolve_arguments(state,"summarize_classification",inputs,{"year":2024})
    bad=copy.deepcopy(state); bad["input_resources"].pop("study_area")
    with pytest.raises(ValueError,match="missing"):
        resolve_arguments(bad,"summarize_classification",inputs,{"year":2025})
    with pytest.raises(ValueError,match="outside"):
        make_record(state,"run:action:01","summarize_classification",{"success":True,"data":{"output_path":state["input_resources"]["classification"]["path"]}})
    state["input_resources"]["study_area"]["components"][".dbf"]="0"*64
    with pytest.raises(ValueError,match="AOI component"):
        resolve_arguments(state,"summarize_classification",inputs,{"year":2025})


def test_generic_loop_does_not_accept_malformed_final_or_exceed_budget(domain_request):
    class Bad:
        async def decide(self,role,view):
            return {"kind":"final","answer":"done","_provider_usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}
    state=asyncio.run(run_single(packet_for(domain_request),resources_for(domain_request),domain_request.output_dir/"bad",Bad(),domain_request.budgets.model_dump()))
    assert state["status"] == "failed" and state["tool_calls"] == 0
    small={**domain_request.budgets.model_dump(),"max_total_tokens_recorded":1}
    state=asyncio.run(run_single(packet_for(domain_request),resources_for(domain_request),domain_request.output_dir/"budget",Bad(),small))
    assert state["status"] == "controlled_stop" and state["model_calls"] == 1


def test_adapter_keeps_existing_scheduler():
    assert ClassificationComparisonSystem._drive is ExpertsRSSystem._drive
    assert ClassificationComparisonSystem._execute_action is ExpertsRSSystem._execute_action
