"""Runtime foundation verification tests."""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from runtime import (
    RunArtifactStore,
    RunState,
    RuntimeEvaluator,
    RuntimeWorkflow,
    ToolRuntime,
    WorkflowPhase,
    add_evidence,
    backend_plan_to_dict,
    build_vegetation_orchestrator,
    describe_langgraph_adapter,
    finish_backend_call,
    start_backend_call,
    validate_contract_registry,
    vegetation_mapping_ndvi_threshold,
)
from tools import list_tools


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def _results_files() -> set[Path]:
    results_dir = Path(__file__).resolve().parent / "results"
    if not results_dir.exists():
        return set()
    return {path for path in results_dir.rglob("*") if path.is_file()}


def _cleanup_new_results(before: set[Path]) -> None:
    for path in sorted(_results_files() - before, reverse=True):
        path.unlink(missing_ok=True)


def main():
    print("=" * 60)
    print("ExpertsRS Runtime Foundation Tests")
    print("=" * 60)

    before_results = _results_files()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            state = RunState(user_request="Map urban greenspace for policy support.")
            store = RunArtifactStore(base_dir=tmp)
            workflow = RuntimeWorkflow(state=state, tool_runtime=ToolRuntime(), artifact_store=store)

            workflow.initialize_request(state.user_request)
            assert_true(state.phase == WorkflowPhase.CLARIFY.value, "request initialization sets clarify phase")

            workflow.set_structured_request(
                aoi="Beijing urban area",
                time_period="recent cloud-free image",
                resolution="Sentinel-2 scale",
                output="greenspace map and area statistics",
            )
            assert_true(state.structured_request["aoi"] == "Beijing urban area", "structured request is recorded")

            workflow.set_method_plan(
                {
                    "dataset": "Sentinel-2 or local equivalent",
                    "method": "NDVI thresholding",
                    "metrics": ["vegetation area", "coverage rate"],
                },
                assumptions=["Use existing local raster when online data retrieval is unavailable."],
            )
            assert_true(state.checkpoints[-1].name == "plan_approval", "plan approval checkpoint is created")

            workflow.approve_plan()
            assert_true(state.phase == WorkflowPhase.SOLVE.value, "plan approval enters solve phase")

            result = workflow.discover_data()
            assert_true("list_available_data_files" == state.tool_calls[-1].tool_name, "tool runtime records tool call")
            assert_true(result["success"] in [True, False], "tool result returns structured success flag")

            report_path = workflow.write_report_stub("# Runtime smoke report\n")
            assert_true(report_path.exists(), "report artifact is written")
            assert_true((store.run_dir / "run_manifest.json").exists(), "run manifest is written")
            assert_true(state.phase == WorkflowPhase.COMPLETE.value, "workflow can complete")

            contract_issues = validate_contract_registry(list_tools())
            assert_true(not contract_issues, "all registered tools have valid contracts")

            evaluator = RuntimeEvaluator()
            eval_result = evaluator.evaluate(state)
            assert_true(eval_result.passed, "complete runtime smoke run passes evaluator")
            store.write_manifest(state)
            assert_true("evaluation" in state.metrics, "evaluation result is recorded in state metrics")

            missing_plan = RunState(user_request="missing method plan")
            missing_plan.structured_request["aoi"] = "test"
            missing_plan.start_tool_call("list_available_data_files", {})
            missing_plan.add_artifact("report", str(report_path))
            failed_missing_plan = evaluator.evaluate(missing_plan)
            assert_true(not failed_missing_plan.passed, "evaluator fails when method plan is missing")

            unfinished = RunState(user_request="unfinished call")
            unfinished.structured_request["aoi"] = "test"
            unfinished.method_plan["method"] = "test"
            unfinished.start_tool_call("list_available_data_files", {})
            unfinished.add_artifact("report", str(report_path))
            failed_unfinished = evaluator.evaluate(unfinished)
            assert_true(not failed_unfinished.passed, "evaluator fails unfinished tool calls")

            missing_artifact = RunState(user_request="missing artifact path")
            missing_artifact.structured_request["aoi"] = "test"
            missing_artifact.method_plan["method"] = "test"
            call = missing_artifact.start_tool_call("calculate_ndvi", {})
            missing_artifact.finish_tool_call(call.call_id, True, "ok", {"contract_output_kinds": ["raster"]})
            missing_artifact.add_artifact("raster", str(Path(tmp) / "does_not_exist.tif"), source_tool_call_id=call.call_id)
            failed_artifact = evaluator.evaluate(missing_artifact)
            assert_true(not failed_artifact.passed, "evaluator fails missing artifact paths")

            missing_param = RunState(user_request="missing required parameter")
            try:
                ToolRuntime().call(missing_param, "apply_threshold", threshold_low=0.3)
            except ValueError:
                pass
            assert_true(missing_param.errors, "tool runtime records missing required parameters")

            backend_plan = backend_plan_to_dict()
            assert_true("scientist" in backend_plan and "engineer" in backend_plan, "default backend plan covers core agent roles")
            backend_call = start_backend_call(
                state,
                role="scientist",
                backend_type="llm_with_retrieval",
                provider="test_provider",
                model="test_model",
                purpose="record provenance only",
            )
            finish_backend_call(state, backend_call.call_id, status="ok", token_input=10, token_output=5, latency_ms=123)
            add_evidence(
                state,
                role="scientist",
                source="test knowledge base",
                summary="NDVI thresholding is a baseline vegetation mapping method.",
                citation="runtime-test",
            )
            store.write_manifest(state)
            assert_true(state.backend_calls[-1].finished_at is not None, "backend call provenance records completion")
            assert_true(state.evidence[-1]["citation"] == "runtime-test", "evidence provenance records citations")

            task_workflow = vegetation_mapping_ndvi_threshold(
                user_request="Map vegetation for runtime validation.",
                aoi="local test raster extent",
                time_period="local test period",
                threshold=0.3,
                artifact_base_dir=tmp,
            )
            assert_true(task_workflow.state.metrics.get("evaluation_status") == "pass", "vegetation task template passes evaluator")
            assert_true(any(item.kind == "raster" for item in task_workflow.state.artifacts), "vegetation task records raster artifacts")
            assert_true(any(item.kind == "map" for item in task_workflow.state.artifacts), "vegetation task records map artifacts")
            assert_true(any(item.kind == "report" for item in task_workflow.state.artifacts), "vegetation task records report artifact")
            assert_true((task_workflow.artifacts.run_dir / "run_manifest.json").exists(), "vegetation task writes manifest")

            orchestrator = build_vegetation_orchestrator(
                user_request="Map vegetation through orchestrated runtime nodes.",
                artifact_base_dir=tmp,
            )
            graph_description = describe_langgraph_adapter(orchestrator)
            assert_true(graph_description["start_node"] == "manager", "orchestrator exposes a graph start node")
            orchestrated = orchestrator.run({
                "aoi": "local orchestrator extent",
                "time_period": "local orchestrator period",
                "threshold": 0.3,
            })
            trace = orchestrated.state.metrics.get("orchestration_trace", [])
            assert_true([item["node_name"] for item in trace] == ["manager", "scientist", "approval", "engineer", "verifier", "reporter"], "orchestrator runs expected node sequence")
            assert_true(orchestrated.state.metrics.get("evaluation_status") == "pass", "orchestrated vegetation workflow passes evaluator")
            assert_true(orchestrated.state.phase == WorkflowPhase.COMPLETE.value, "orchestrated workflow completes")
    finally:
        _cleanup_new_results(before_results)
    print("=" * 60)
    print("All runtime tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
