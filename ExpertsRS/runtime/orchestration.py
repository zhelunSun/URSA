"""Framework-neutral orchestration nodes for ExpertsRS runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .artifacts import RunArtifactStore
from .evaluator import RuntimeEvaluator
from .state import AgentRole, RunState, WorkflowPhase
from .tool_runtime import ToolRuntime
from .workflow import RuntimeWorkflow


NodeContext = dict[str, Any]
NodeHandler = Callable[[RuntimeWorkflow, NodeContext], "NodeResult"]


@dataclass
class NodeResult:
    node_name: str
    role: str
    status: str = "ok"
    message: str = ""
    next_node: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_name": self.node_name,
            "role": self.role,
            "status": self.status,
            "message": self.message,
            "next_node": self.next_node,
            "details": self.details,
        }


class RuntimeOrchestrator:
    """Drive named runtime nodes over a shared RuntimeWorkflow.

    This is the stable orchestration surface that a future LangGraph adapter can
    wrap. Nodes are deterministic callables in this layer; LLM-backed agents can
    later be slotted behind the same node contract.
    """

    def __init__(
        self,
        workflow: RuntimeWorkflow,
        nodes: dict[str, NodeHandler],
        start_node: str,
        max_steps: int = 20,
    ):
        if start_node not in nodes:
            raise ValueError(f"Unknown start node {start_node!r}")
        self.workflow = workflow
        self.nodes = nodes
        self.start_node = start_node
        self.max_steps = max_steps

    def run(self, context: NodeContext | None = None) -> RuntimeWorkflow:
        context = context or {}
        node_name: str | None = self.start_node
        trace: list[dict[str, Any]] = []

        for _ in range(self.max_steps):
            if node_name is None:
                self.workflow.state.metrics["orchestration_trace"] = trace
                self.workflow.artifacts.write_manifest(self.workflow.state)
                return self.workflow
            if node_name not in self.nodes:
                raise ValueError(f"Unknown node {node_name!r}")

            result = self.nodes[node_name](self.workflow, context)
            trace.append(result.to_dict())
            self.workflow.state.add_decision(
                result.role,
                result.message or f"Completed node {result.node_name}",
                {"node_result": result.to_dict()},
            )
            node_name = result.next_node

        raise RuntimeError(f"Orchestration exceeded max_steps={self.max_steps}")


def manager_node(workflow: RuntimeWorkflow, context: NodeContext) -> NodeResult:
    user_request = context.get("user_request") or workflow.state.user_request or "Map vegetation using NDVI thresholding."
    workflow.initialize_request(user_request)
    workflow.set_structured_request(
        aoi=context.get("aoi", "local raster extent"),
        time_period=context.get("time_period", "local raster acquisition period"),
        resolution=context.get("resolution", "source raster resolution"),
        output=context.get("output", "vegetation mask, vegetation area, thematic map, and runtime report"),
    )
    return NodeResult("manager", AgentRole.MANAGER.value, message="Structured the user request.", next_node="scientist")


def scientist_node(workflow: RuntimeWorkflow, context: NodeContext) -> NodeResult:
    threshold = context.get("threshold", 0.3)
    workflow.set_method_plan(
        {
            "template": "vegetation_mapping_ndvi_threshold",
            "dataset": "auto-discovered local multispectral raster",
            "method": "NDVI thresholding",
            "threshold": threshold,
            "tool_sequence": [
                "list_available_data_files",
                "read_raster_metadata",
                "calculate_ndvi",
                "apply_threshold",
                "calculate_area",
                "plot_thematic_map",
            ],
        },
        assumptions=[
            "Band indexes follow Sentinel-2 conventions unless the user overrides them.",
            "A single local raster can stand in for external data retrieval during runtime smoke tests.",
        ],
    )
    return NodeResult("scientist", AgentRole.SCIENTIST.value, message="Prepared deterministic NDVI method plan.", next_node="approval")


def approval_node(workflow: RuntimeWorkflow, context: NodeContext) -> NodeResult:
    response = context.get("plan_approval_response", "approved by deterministic orchestrator")
    workflow.approve_plan(response=response)
    return NodeResult("approval", AgentRole.USER.value, message="Approved method plan checkpoint.", next_node="engineer")


def engineer_node(workflow: RuntimeWorkflow, context: NodeContext) -> NodeResult:
    threshold = context.get("threshold", 0.3)
    data_result = workflow.discover_data()
    if not data_result.get("success") or not data_result.get("data", {}).get("abs_paths"):
        workflow.state.add_error("engineer_node", "No local raster data available.")
        return NodeResult("engineer", AgentRole.ENGINEER.value, status="blocked", message="No local raster data available.", next_node="verifier")

    source_path = data_result["data"]["abs_paths"][0]
    metadata = workflow.tools.call(workflow.state, "read_raster_metadata", file_path=source_path)
    ndvi = workflow.tools.call(workflow.state, "calculate_ndvi", file_path=source_path)
    ndvi_path = ndvi["data"]["output_path"] if ndvi.get("success") else None

    mask_path = None
    area = None
    map_result = None
    if ndvi_path:
        mask = workflow.tools.call(
            workflow.state,
            "apply_threshold",
            file_path=ndvi_path,
            threshold_low=threshold,
            output_name="vegetation",
        )
        mask_path = mask["data"]["output_path"] if mask.get("success") else None

    if mask_path:
        area = workflow.tools.call(workflow.state, "calculate_area", file_path=mask_path)
        map_result = workflow.tools.call(
            workflow.state,
            "plot_thematic_map",
            file_path=mask_path,
            class_labels={0: "Non-vegetation", 1: "Vegetation"},
            output_name="vegetation_mask",
            title="Vegetation Mask from NDVI Threshold",
        )

    context["engineer_outputs"] = {
        "metadata": metadata,
        "ndvi": ndvi,
        "area": area,
        "map": map_result,
        "threshold": threshold,
    }
    workflow.artifacts.write_manifest(workflow.state)
    return NodeResult("engineer", AgentRole.ENGINEER.value, message="Executed NDVI vegetation tool sequence.", next_node="verifier")


def verifier_node(workflow: RuntimeWorkflow, context: NodeContext) -> NodeResult:
    result = workflow.evaluate()
    status = "ok" if result.passed else "failed"
    return NodeResult("verifier", AgentRole.VERIFIER.value, status=status, message=result.summary, next_node="reporter")


def reporter_node(workflow: RuntimeWorkflow, context: NodeContext) -> NodeResult:
    outputs = context.get("engineer_outputs", {})
    area_text = ""
    area = outputs.get("area")
    if area and area.get("success"):
        area_text = f"\n- Area statistics: {area.get('data', {}).get('areas_hectares', {})}"

    map_text = ""
    map_result = outputs.get("map")
    if map_result and map_result.get("success"):
        map_text = f"\n- Thematic map: {map_result['data']['output_path']}"

    metadata_text = ""
    metadata = outputs.get("metadata")
    if metadata and metadata.get("success"):
        metadata_text = f"\n- Source raster: {metadata['data'].get('file_name')}"

    workflow.write_report_stub(
        "# Vegetation Mapping Runtime Report\n\n"
        f"- Request: {workflow.state.user_request}"
        f"\n- AOI: {workflow.state.structured_request.get('aoi')}"
        f"\n- Time period: {workflow.state.structured_request.get('time_period')}"
        f"\n- Method: NDVI >= {outputs.get('threshold', 0.3)}"
        f"{metadata_text}{area_text}{map_text}"
        f"\n- Evaluation: {workflow.state.metrics.get('evaluation_status')}\n"
    )
    workflow.state.set_phase(WorkflowPhase.COMPLETE)
    workflow.artifacts.write_manifest(workflow.state)
    return NodeResult("reporter", AgentRole.REPORTER.value, message="Wrote final runtime report.", next_node=None)


def build_vegetation_orchestrator(
    user_request: str = "Map vegetation using NDVI thresholding.",
    artifact_base_dir: str | None = None,
) -> RuntimeOrchestrator:
    workflow = RuntimeWorkflow(
        state=RunState(user_request=user_request),
        tool_runtime=ToolRuntime(),
        artifact_store=RunArtifactStore(base_dir=artifact_base_dir),
        evaluator=RuntimeEvaluator(),
    )
    return RuntimeOrchestrator(
        workflow=workflow,
        nodes={
            "manager": manager_node,
            "scientist": scientist_node,
            "approval": approval_node,
            "engineer": engineer_node,
            "verifier": verifier_node,
            "reporter": reporter_node,
        },
        start_node="manager",
    )
