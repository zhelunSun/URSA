"""No-API preparation: public packets plus private integrity/port receipts.

Reads an existing local run for resource bindings; never supplies its answers,
plans, trace, artifacts or evaluator rules to the public packet.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from ExpertsRS.knowledge_port import KnowledgeRequest, UnavailableKnowledgePort, validate_exchange

PROTOCOL = REPO / "ExpertsRS/evaluation/ch3_preparation_v1.json"


def component_hashes(resource):
    components = resource.get("components", {})
    allowed = {".shp", ".shx", ".dbf", ".prj", ".cpg"}
    if not isinstance(components, dict) or any(
        suffix not in allowed or not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
        for suffix, value in components.items()
    ):
        raise ValueError("Only named AOI sidecar SHA256 values may enter the public packet")
    return dict(components)


def run_path(value, run_dir):
    path = Path(value)
    return (path if path.is_absolute() else run_dir / path).resolve()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def public_packet(case, state):
    # Explicit projection, not removal of a blacklist from raw state.
    resources = []
    for resource_id in case["resources"]:
        resource = state["input_resources"][resource_id]
        resources.append({"resource_id": resource_id, "artifact_type": resource["artifact_type"],
                          "sha256": resource["sha256"], "components": component_hashes(resource)})
    return {"schema_version": "ch3-public-task-v1", "case_id": case["case_id"],
            "request": case["request"], "product_year": state["product_year"], "resources": resources,
            "deliverables": case["deliverables"], "knowledge_status": "unavailable",
            "tool_names": ["summarize_classification", "plot_classification_map"]}


def verify_existing_run(state, run_dir):
    checked = {}
    for resource_id, resource in state["input_resources"].items():
        path = run_path(resource["path"], run_dir)
        if digest(path) != resource["sha256"]:
            raise ValueError(f"Input drift: {resource_id}")
        checked[resource_id] = resource["sha256"]
        for suffix, expected in component_hashes(resource).items():
            if digest(path.with_suffix(suffix)) != expected:
                raise ValueError(f"AOI component drift: {suffix}")
            checked[f"{resource_id}{suffix}"] = expected
    for artifact in state["artifacts"]:
        path = run_path(artifact["uri"], run_dir)
        if not path.is_relative_to(run_dir.resolve()):
            raise ValueError("Foreign artifact")
        if digest(path) != artifact["metadata"]["artifact_sha256"]:
            raise ValueError("Artifact drift")
        checked[artifact["artifact_id"]] = digest(path)
    return checked


def prepare(run_dir, output):
    run_dir = run_dir.resolve()
    if output.exists():
        raise FileExistsError("Preparation output already exists; use a new run ID")
    output.mkdir(parents=True)
    private = output / "private"
    private.mkdir()
    receipt = {"status": "started", "api_calls": 0, "new_task_executions": 0,
               "scope": "Existing-run integrity and preparation contracts only"}
    try:
        state_path = run_dir / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state["domain_profile"] != "classification-v1" or state["product_year"] != 2025:
            raise ValueError("Requires the existing 2025 classification development run")
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        receipt["code_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        receipt["source_hashes"] = {str(p.relative_to(REPO)): digest(p) for p in (
            PROTOCOL, Path(__file__).resolve(), REPO / "ExpertsRS/knowledge_port.py")}
        receipt["existing_state_sha256"] = digest(state_path)
        receipt["verified_files"] = verify_existing_run(state, run_dir)
        public = output / "public"
        public.mkdir()
        packet_hashes = {}
        for case in protocol["cases"]:
            packet = public_packet(case, state)
            path = public / f"{case['case_id']}.json"
            path.write_text(json.dumps(packet, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            packet_hashes[path.name] = digest(path)
        request = KnowledgeRequest(request_id="dev-port-unavailable", question="Can the supplied product establish verified core habitat?",
                                   scope="2025 supplied study area")
        response = UnavailableKnowledgePort().query(request)
        validate_exchange(request, response)
        (private / "knowledge_exchange.json").write_text(json.dumps({"request":request.model_dump(),
            "response":response.model_dump()}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        receipt.update(status="passed", public_packet_hashes=packet_hashes,
                       knowledge_port_status=response.status, comparator_status="not_implemented",
                       isolation_status="data_projection_only_not_process_sandbox")
        if digest(state_path) != receipt["existing_state_sha256"]:
            raise ValueError("Raw state changed")
    except Exception as error:
        receipt.update(status="failed", error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        (private / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--existing-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.existing_run, args.output), ensure_ascii=False, indent=2))
