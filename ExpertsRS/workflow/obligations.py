"""Runtime-owned delivery obligations derived from the public user request.

This intentionally small registry is a safety boundary: a Scientist may add
deliverables, but cannot make a user-requested deliverable disappear by
omitting it from a TaskSpec.  Rules are deterministic and path-free so the
same request has the same public obligation manifest in offline and live runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


SAFE_GREEN_SCOPE = "有效影像像元范围内；未验证为行政区面积分母"


@dataclass(frozen=True)
class DeliveryObligation:
    obligation_id: str
    description: str
    required_plan_node_ids: tuple[str, ...]
    required_artifact_types: tuple[str, ...]
    required_scope: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "description": self.description,
            "required_plan_node_ids": list(self.required_plan_node_ids),
            "required_artifact_types": list(self.required_artifact_types),
            "required_scope": self.required_scope,
        }


def derive_delivery_obligations(request: str) -> list[DeliveryObligation]:
    """Recognise only supported, unambiguous delivery semantics.

    The wording covers the frozen English panel and the Chinese thesis-facing
    request.  It deliberately does not infer unsupported analytic products.
    """
    text = request.casefold()
    obligations: list[DeliveryObligation] = []
    green = any(token in text for token in (
        "vegetation coverage", "vegetation cover", "green cover", "greenspace",
        "green space", "植被覆盖", "绿地覆盖",
    ))
    asks_map = green and ("vegetation coverage" in text or "植被覆盖" in text) or any(
        token in text for token in ("map", "visualize", "visualise", "专题图", "地图", "制图")
    )
    asks_rate = any(token in text for token in ("rate", "percentage", "proportion", "coverage", "覆盖率", "比例"))
    if green and asks_map:
        obligations.append(DeliveryObligation(
            "vegetation_coverage_map", "Vegetation coverage thematic map derived from the threshold mask.",
            ("thematic_map",), ("map",), "supplied raster extent",
        ))
    if green and asks_rate:
        obligations.append(DeliveryObligation(
            "green_cover_rate", "Green-cover percentage supported by threshold-mask and area evidence.",
            ("threshold", "area_statistics"), ("mask_raster", "area_statistics"), SAFE_GREEN_SCOPE,
        ))
    if not green and "ndvi" in text and asks_map:
        obligations.append(DeliveryObligation(
            "ndvi_map", "NDVI map.", ("index_map",), ("map",), "supplied raster extent",
        ))
    return obligations


def validate_plan_obligations(obligations: list[dict[str, Any]], task: dict[str, Any], workflow: dict[str, Any]) -> None:
    """Fail closed when the proposed TaskSpec/graph cannot satisfy an obligation."""
    requested = set(task.get("requested_outputs", []))
    nodes = {item.get("node_id"): item for item in workflow.get("nodes", [])}
    for obligation in obligations:
        obligation_id = obligation["obligation_id"]
        if obligation_id not in requested:
            raise ValueError(f"Scientist TaskSpec omitted runtime delivery obligation: {obligation_id}")
        for node_id in obligation.get("required_plan_node_ids", []):
            node = nodes.get(node_id)
            if node is None:
                raise ValueError(f"Scientist workflow omitted obligation node: {obligation_id}:{node_id}")
            if obligation_id == "vegetation_coverage_map" and node.get("operator_id") != "expertsrs.plot_thematic_map.v1":
                raise ValueError("Vegetation coverage map must be produced by plot_thematic_map(mask_raster)")
            if obligation_id == "green_cover_rate" and node_id == "threshold" and node.get("operator_id") != "expertsrs.apply_threshold.v1":
                raise ValueError("Green cover rate requires a threshold mask")
            if obligation_id == "green_cover_rate" and node_id == "area_statistics" and node.get("operator_id") != "expertsrs.calculate_area.v1":
                raise ValueError("Green cover rate requires area statistics")


def classify_graph_diff(previous: dict[str, Any] | None, current: dict[str, Any], *, is_revision: bool) -> str:
    """Classify what a revision evidences; never imply planning superiority."""
    if not is_revision or previous is None:
        return "initial_plan"
    if previous.get("task") != current.get("task"):
        return "output_scope_delta"
    if json.dumps(previous.get("workflow"), sort_keys=True) == json.dumps(current.get("workflow"), sort_keys=True):
        return "local_reauthorization_only"
    return "structural_delta"
