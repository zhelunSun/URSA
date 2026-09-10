"""Development contracts, not knowledge quality or comparative performance tests."""
import copy
import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from ExpertsRS.knowledge_port import KnowledgeRequest, KnowledgeResponse, UnavailableKnowledgePort, validate_exchange
from scripts.prepare_ch3_validation import prepare, public_packet, verify_existing_run


def test_unavailable_port_does_not_fabricate_answer_or_usage():
    request = KnowledgeRequest(request_id="dev", question="Is this habitat?", scope="supplied product")
    response = UnavailableKnowledgePort().query(request)
    validate_exchange(request, response)
    assert response.status == "unavailable" and response.answer is None and not response.evidence
    assert (response.model_calls, response.tool_calls, response.total_tokens) == (0, 0, 0)
    with pytest.raises(ValidationError):
        KnowledgeResponse(request_id="dev", status="unavailable", answer="It is habitat", reason="offline")


def test_available_knowledge_cannot_omit_provenance_or_applicability():
    with pytest.raises(ValidationError):
        KnowledgeResponse(request_id="dev", status="available", answer="Use method X")


def test_exchange_rejects_wrong_request_and_hidden_nested_cost():
    request = KnowledgeRequest(request_id="dev", question="Q", scope="S")
    with pytest.raises(ValueError, match="another request"):
        validate_exchange(request, KnowledgeResponse(request_id="other", status="failed", reason="error"))
    with pytest.raises(ValueError, match="budget"):
        validate_exchange(request, KnowledgeResponse(request_id="dev", status="failed", reason="error", model_calls=1))


def test_projection_excludes_answers_paths_and_ursa_plan_requirements():
    state = {"product_year": 2025, "input_resources": {
        "classification": {"path": "SECRET_PATH", "artifact_type": "raster", "sha256": "a"*64},
        "study_area": {"path": "SECRET_AOI", "artifact_type": "aoi", "sha256": "b"*64}},
        "reference_answer": "SECRET_ANSWER", "plan_history": "SECRET_PLAN", "artifacts": "SECRET_ARTIFACTS"}
    case = {"case_id":"dev", "request":"Describe product", "resources":["classification"],
            "deliverables":["answer"], "evaluator_only":{"gold":"SECRET_GOLD"}}
    packet = public_packet(case, state)
    assert "SECRET" not in str(packet)
    assert [r["resource_id"] for r in packet["resources"]] == ["classification"]
    assert "workflow" not in str(packet) and "eligible_node" not in str(packet)
    state["input_resources"]["classification"]["components"] = {"answer": "SECRET_GOLD"}
    with pytest.raises(ValueError, match="sidecar SHA256"):
        public_packet(case, state)
    state["input_resources"]["classification"]["components"] = {".dbf": "SECRET_PATH"}
    with pytest.raises(ValueError, match="sidecar SHA256"):
        public_packet(case, state)


def test_hash_checks_reject_sidecar_drift_and_foreign_artifact(tmp_path):
    raster = tmp_path / "input.tif"
    raster.write_bytes(b"input")
    aoi = tmp_path / "input.shp"
    aoi.write_bytes(b"aoi")
    aoi.with_suffix(".dbf").write_bytes(b"dbf")
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    state = {"input_resources":{"classification":{"path":str(raster),"sha256":h(raster)},
             "study_area":{"path":str(aoi),"sha256":h(aoi),"components":{".dbf":h(aoi.with_suffix('.dbf'))}}},
             "artifacts":[]}
    assert len(verify_existing_run(state, tmp_path / "run")) == 3
    foreign = copy.deepcopy(state)
    foreign["artifacts"] = [{"uri":str(raster),"metadata":{"artifact_sha256":h(raster)}}]
    with pytest.raises(ValueError, match="Foreign artifact"):
        verify_existing_run(foreign, tmp_path / "run")
    aoi.with_suffix(".dbf").write_bytes(b"changed")
    with pytest.raises(ValueError, match="component drift"):
        verify_existing_run(state, tmp_path / "run")


def test_preparation_does_not_overwrite_or_hide_first_failure(tmp_path):
    output = tmp_path / "preparation"
    with pytest.raises(FileNotFoundError):
        prepare(tmp_path / "missing-source", output)
    receipt = output / "private/receipt.json"
    first = receipt.read_bytes()
    assert b'"status": "failed"' in first
    with pytest.raises(FileExistsError):
        prepare(tmp_path / "missing-source", output)
    assert receipt.read_bytes() == first


def test_relative_run_paths_do_not_depend_on_launch_directory(tmp_path, monkeypatch):
    run_dir = tmp_path / "old-run"
    run_dir.mkdir()
    source = run_dir / "input.tif"
    source.write_bytes(b"source")
    product = run_dir / "output.json"
    product.write_bytes(b"product")
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    state = {"input_resources":{"classification":{"path":"input.tif", "sha256":h(source)}},
             "artifacts":[{"artifact_id":"output", "uri":"output.json", "metadata":{"artifact_sha256":h(product)}}]}
    elsewhere = tmp_path / "launch"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert verify_existing_run(state, run_dir)["output"] == h(product)
