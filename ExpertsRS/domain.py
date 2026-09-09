"""Explicit, versioned classification profile; no scheduler or evaluator data."""

from .models import ToolBinding

PROFILE = "classification-v1"
SCOPE = "原网格研究范围内的有效分类像元；不是面积、专题准确率或生态功能估计"
CLASS_NAMES = ("tree", "shrub", "grass", "wetland", "impervious_surface", "water", "cropland", "bare_land")


def bindings(year):
    return {name: ToolBinding(tool_name=name, safe_parameters={"year": year}) for name in (
        "summarize_classification", "plot_classification_map",
    )}


def obligations():
    return [
        {"obligation_id": "class_composition", "description": "Eight-class counts and fractions in the supplied AOI",
         "required_plan_node_ids": ["composition"], "required_artifact_types": ["composition_table"], "required_scope": SCOPE},
        {"obligation_id": "classification_map", "description": "Spatial map of the same classification and AOI",
         "required_plan_node_ids": ["classification_map"], "required_artifact_types": ["map"], "required_scope": SCOPE},
    ]


def scripted_plan(request, year):
    """Engineering fixture only. A future live planner must be admitted separately."""
    return {
        "kind": "plan",
        "task": {"task_id": "classification_description", "goal": request,
                 "expected_outputs": ["composition_table", "map"],
                 "requested_outputs": ["class_composition", "classification_map"],
                 "required_metrics": [], "constraints": {"year": year, "profile": PROFILE}},
        "workflow": {"workflow_id": "classification_description",
            "input_artifacts": [{"artifact_id": "classification", "artifact_type": "raster"},
                                {"artifact_id": "study_area", "artifact_type": "aoi"}],
            "nodes": [
                {"node_id": "composition", "operator_id": "expertsrs.summarize_classification.v1",
                 "inputs": {"file_path": "classification", "aoi_path": "study_area"},
                 "output_artifact_id": "composition_table", "config": {"year": year}, "depends_on": []},
                {"node_id": "classification_map", "operator_id": "expertsrs.plot_classification_map.v1",
                 "inputs": {"file_path": "classification", "aoi_path": "study_area", "composition_path": "composition_table"},
                 "output_artifact_id": "classification_map", "config": {"year": year}, "depends_on": ["composition"]},
            ]},
    }


def deliverables(state):
    by_node = {a.get("producer_plan_node_id"): a for a in state["artifacts"]}
    result = []
    table = by_node.get("composition")
    if table:
        data = table["metadata"]
        counts, fractions = data["counts"], data["fractions"]
        value = "; ".join(f"{name}: {counts[name]} ({fractions[name]:.2%})" for name in CLASS_NAMES)
        value += f"; valid={data['valid_pixels']}; nodata={data['nodata_pixels']}"
        result.append({"deliverable_id": "class_composition", "status": "delivered", "value": value,
                       "unit": "pixels / fraction", "scope": SCOPE, "artifact_refs": [table["artifact_id"]]})
    plotted = by_node.get("classification_map")
    if plotted and table:
        result.append({"deliverable_id": "classification_map", "status": "delivered",
                       "value": f"{state['product_year']} classification map; display sampling disclosed",
                       "unit": None, "scope": SCOPE,
                       "artifact_refs": [plotted["artifact_id"], table["artifact_id"]]})
    return result
