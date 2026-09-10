"""Shared, closed tool boundary for the K0 development comparison.

No planner, model, evaluator reference, shell, or arbitrary file-read operation.
"""
import json
from pathlib import Path

from .domain import CLASS_NAMES, SCOPE, deliverables
from .models import ArtifactRecord
from .workflow.runtime import LocalPermissionPolicy


TOOL_TYPES = {"summarize_classification": "composition_table", "plot_classification_map": "map"}
INPUT_TYPES = {
    "summarize_classification": {"file_path": "raster", "aoi_path": "aoi"},
    "plot_classification_map": {"file_path": "raster", "aoi_path": "aoi", "composition_path": "composition_table"},
}


def file_hash(path):
    import hashlib
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tool_contracts(year):
    return [{"name": name, "operator_id": f"expertsrs.{name}.v1", "inputs": types,
             "parameters": {"year": year}, "output_type": TOOL_TYPES[name],
             "description": (
                 "Count codes 0..7 in the native-grid AOI pixel-centre mask; fractions use valid pixels. "
                 "Returns counts, fractions, valid/nodata counts and source hashes."
                 if name == "summarize_classification" else
                 "Render the same classification and AOI using a previously computed composition_table; display sampling is disclosed."
             ), "class_order": list(CLASS_NAMES), "scope": SCOPE}
            for name, types in INPUT_TYPES.items()]


def resolve_arguments(state, tool, inputs, parameters):
    if tool not in INPUT_TYPES or set(inputs) != set(INPUT_TYPES[tool]):
        raise ValueError("Unknown tool or incorrect named inputs")
    if parameters != {"year": state["product_year"]}:
        raise ValueError("Parameters must match the supplied product year")
    roots = tuple(Path(p).resolve() for p in state["allowed_data_roots"])
    records = {a["artifact_id"]: a for a in state["artifacts"]}
    arguments = dict(parameters)
    for parameter, logical_id in inputs.items():
        if not isinstance(logical_id, str):
            raise ValueError("Inputs must be logical resource or artifact IDs")
        source = state["input_resources"].get(logical_id)
        if source:
            path = Path(source["path"]).resolve()
            if source["artifact_type"] != INPUT_TYPES[tool][parameter]:
                raise ValueError("Input resource type mismatch")
            if not LocalPermissionPolicy._is_within(str(path), roots):
                raise ValueError("Input outside allowed roots")
            if file_hash(path) != source["sha256"]:
                raise ValueError("Input identity changed")
            for suffix, expected in source.get("components", {}).items():
                component = path.with_suffix(suffix).resolve()
                if not LocalPermissionPolicy._is_within(str(component), roots) or file_hash(component) != expected:
                    raise ValueError("AOI component changed or outside roots")
        else:
            record = records.get(logical_id)
            if not record or record["artifact_type"] != INPUT_TYPES[tool][parameter]:
                raise ValueError("Required upstream artifact missing or incompatible")
            path = Path(record["uri"]).resolve()
            if not path.is_relative_to(Path(state["run_dir"]).resolve()) or file_hash(path) != record["metadata"]["artifact_sha256"]:
                raise ValueError("Upstream artifact changed or outside this run")
        arguments[parameter] = str(path)
    return arguments


def make_record(state, action_id, tool, result, node_id=None):
    if not result.get("success"):
        return None
    data = result.get("data")
    if tool not in TOOL_TYPES or not isinstance(data, dict) or not isinstance(data.get("output_path"), str):
        raise ValueError("Successful tool omitted its artifact")
    root = (Path(state["run_dir"]) / "artifacts" / action_id.replace(":", "_")).resolve()
    path = Path(data["output_path"]).resolve()
    if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Artifact missing or outside action directory")
    if tool == "summarize_classification":
        persisted = json.loads(path.read_text(encoding="utf-8"))
        if persisted.get("artifact_type") != "classification_summary" or persisted.get("data") != data:
            raise ValueError("Composition metadata does not match persisted product")
    for secondary in data.get("secondary_outputs", []):
        p = Path(secondary["path"]).resolve()
        if not p.is_relative_to(root) or not p.is_file() or p.stat().st_size == 0:
            raise ValueError("Secondary artifact missing or outside action directory")
        secondary["sha256"] = file_hash(p)
    return ArtifactRecord(artifact_id=f"{action_id}:{TOOL_TYPES[tool]}", artifact_type=TOOL_TYPES[tool],
        uri=path, producer_action_id=action_id,
        producer_plan_node_id=node_id or ("composition" if tool == "summarize_classification" else "classification_map"),
        metadata={**{k:v for k,v in data.items() if k != "output_path"}, "artifact_sha256":file_hash(path)})


def verify_records(state):
    for record in state["artifacts"]:
        path = Path(record["uri"]).resolve()
        if not path.is_relative_to(Path(state["run_dir"]).resolve()) or file_hash(path) != record["metadata"]["artifact_sha256"]:
            raise ValueError("Artifact changed before delivery")
        for secondary in record["metadata"].get("secondary_outputs", []):
            p = Path(secondary["path"]).resolve()
            if not p.is_relative_to(path.parent) or file_hash(p) != secondary["sha256"]:
                raise ValueError("Secondary artifact changed before delivery")


def public_facts(state):
    # Only computed numeric facts; provenance paths and figure source locations are private.
    keys = {"year", "class_order", "counts", "fractions", "valid_pixels", "nodata_pixels", "aoi_pixel_centres", "scope"}
    return [{"artifact_id":a["artifact_id"], "artifact_type":a["artifact_type"],
             "sha256":a["metadata"]["artifact_sha256"],
             "facts":{k:v for k,v in a["metadata"].items() if k in keys}}
            for a in state["artifacts"]]


def factual_deliverables(state):
    return deliverables(state)


def validate_final(state, refs, declared):
    verify_records(state)
    actual = {a["artifact_id"] for a in state["artifacts"]}
    if len(refs) != len(set(refs)) or set(refs) != actual:
        raise ValueError("Final references must match produced artifacts")
    facts = {d["deliverable_id"]:d for d in factual_deliverables(state)}
    if len(declared) != len(facts) or {d.get("deliverable_id") for d in declared} != set(facts):
        raise ValueError("Final omitted or invented product deliverables")
    for item in declared:
        if item != facts[item["deliverable_id"]]:
            raise ValueError("Final product values or scope disagree with tool facts")


def invoke(state, tool, inputs, parameters, executor):
    if state["tool_calls"] >= state["budgets"]["max_tool_calls"]:
        raise ValueError("tool_call_budget_exhausted")
    action_id = f"{state['run_id']}:action:{state['tool_calls']+1:02d}"
    state["tool_calls"] += 1
    event = {"action_id":action_id,"tool":tool,"inputs":inputs,"parameters":parameters}
    try:
        arguments = resolve_arguments(state, tool, inputs, parameters)
        result = executor.execute(tool, arguments, Path(state["run_dir"])/"artifacts"/action_id.replace(":","_"))
        record = make_record(state, action_id, tool, result)
        if record:
            state["artifacts"].append(record.model_dump(mode="json"))
        observation = {"tool":tool,"success":bool(result.get("success")),
                       "message":str(result.get("message", "")),"error_code":result.get("error_code")}
        if record:
            observation.update(artifact_id=record.artifact_id,artifact_type=record.artifact_type)
    except (OSError, ValueError, KeyError, TypeError) as error:
        observation = {"tool":tool,"success":False,"message":str(error),"error_code":"tool_contract_error"}
    state["tool_events"].append({**event,"observation":observation})
    return observation
