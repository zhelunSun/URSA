"""Runtime foundation verification tests."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from runtime import RunArtifactStore, RunState, RuntimeWorkflow, ToolRuntime, WorkflowPhase


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"[PASS] {message}")


def main():
    print("=" * 60)
    print("ExpertsRS Runtime Foundation Tests")
    print("=" * 60)

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

    print("=" * 60)
    print("All runtime tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
