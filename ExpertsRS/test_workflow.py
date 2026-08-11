"""Regression tests for the framework-independent workflow runtime."""

import json
import tempfile
import unittest
from pathlib import Path

from workflow import ArtifactSpec, ArtifactType, TaskSpec, WorkflowGraph, WorkflowNode
from workflow import WorkflowTrace, apply_targeted_repair, build_operator_catalog, validate_workflow
from workflow.validator import ViolationCode
from workflow.run_closeout import generate_closeout_evidence


class WorkflowRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = build_operator_catalog()
        cls.scene = str(Path(__file__).parent / "data" / "Sentinel2_Dongcheng_20230718.tif")

    def test_catalog_covers_all_registered_tools(self):
        self.assertEqual(len(self.catalog), 18)

    def test_catalog_contracts_match_callable_signatures(self):
        # build_operator_catalog performs the signature-drift check.
        self.assertEqual(len(build_operator_catalog()), 18)

    def test_valid_graph_passes_preflight(self):
        graph = WorkflowGraph("valid")
        graph.add_artifact(ArtifactSpec("source", ArtifactType.RASTER, self.scene))
        graph.add_step(WorkflowNode("ndvi", "expertsrs.calculate_ndvi.v1", {"file_path": "source"}, "ndvi"), ArtifactType.INDEX_RASTER)
        graph.add_step(WorkflowNode("mask", "expertsrs.apply_threshold.v1", {"file_path": "ndvi"}, "mask"), ArtifactType.MASK_RASTER)
        task = TaskSpec("task", "mask vegetation", (ArtifactType.MASK_RASTER,))
        self.assertTrue(validate_workflow(task, graph, self.catalog).valid)

    def test_type_mismatch_is_machine_detected(self):
        graph = WorkflowGraph("bad-type")
        graph.add_artifact(ArtifactSpec("metadata", ArtifactType.METADATA))
        graph.add_step(WorkflowNode("ndvi", "expertsrs.calculate_ndvi.v1", {"file_path": "metadata"}, "ndvi"), ArtifactType.INDEX_RASTER)
        report = validate_workflow(TaskSpec("task", "index", (ArtifactType.INDEX_RASTER,)), graph, self.catalog)
        self.assertIn(ViolationCode.TYPE_MISMATCH, {item.code for item in report.violations})

    def test_declared_output_must_match_operator_contract(self):
        graph = WorkflowGraph("bad-output")
        graph.add_artifact(ArtifactSpec("source", ArtifactType.RASTER, self.scene))
        graph.add_step(
            WorkflowNode("ndvi", "expertsrs.calculate_ndvi.v1", {"file_path": "source"}, "ndvi"),
            ArtifactType.MAP,
        )
        report = validate_workflow(TaskSpec("task", "index", (ArtifactType.INDEX_RASTER,)), graph, self.catalog)
        self.assertIn(ViolationCode.OUTPUT_TYPE_MISMATCH, {item.code for item in report.violations})

    def test_sentinel2_lst_is_rejected_before_execution(self):
        graph = WorkflowGraph("bad-lst")
        graph.add_artifact(ArtifactSpec("source", ArtifactType.RASTER, self.scene))
        graph.add_step(
            WorkflowNode(
                "lst",
                "expertsrs.calculate_lst.v1",
                {"file_path": "source"},
                "lst",
                {"sensor": "landsat-8", "input_unit": "toa_radiance_w_m2_sr_um"},
            ),
            ArtifactType.INDEX_RASTER,
        )
        report = validate_workflow(TaskSpec("task", "temperature", (ArtifactType.INDEX_RASTER,)), graph, self.catalog)
        self.assertIn(ViolationCode.MISSING_REQUIRED_BAND, {item.code for item in report.violations})

    def test_lst_requires_explicit_radiometric_configuration(self):
        graph = WorkflowGraph("unconfigured-lst")
        graph.add_artifact(ArtifactSpec("source", ArtifactType.RASTER, self.scene))
        graph.add_step(
            WorkflowNode("lst", "expertsrs.calculate_lst.v1", {"file_path": "source"}, "lst"),
            ArtifactType.INDEX_RASTER,
        )
        report = validate_workflow(TaskSpec("task", "temperature", (ArtifactType.INDEX_RASTER,)), graph, self.catalog)
        self.assertIn(ViolationCode.INVALID_CONFIG, {item.code for item in report.violations})

    def test_repair_adds_only_missing_subgraph(self):
        graph = WorkflowGraph("repair")
        graph.add_artifact(ArtifactSpec("source", ArtifactType.RASTER, self.scene))
        graph.add_step(WorkflowNode("ndvi", "expertsrs.calculate_ndvi.v1", {"file_path": "source"}, "ndvi"), ArtifactType.INDEX_RASTER)
        task = TaskSpec("task", "mask vegetation", (ArtifactType.MASK_RASTER,))
        decision = apply_targeted_repair(graph, validate_workflow(task, graph, self.catalog), self.catalog)
        self.assertEqual(decision.status, "repaired")
        self.assertEqual(graph.nodes[0].node_id, "ndvi")
        self.assertTrue(validate_workflow(task, graph, self.catalog).valid)

    def test_ambiguous_or_unsupported_repair_stops_explicitly(self):
        graph = WorkflowGraph("stop")
        graph.add_artifact(ArtifactSpec("source", ArtifactType.RASTER, self.scene))
        task = TaskSpec("task", "produce a narrative", (ArtifactType.REPORT,))
        decision = apply_targeted_repair(graph, validate_workflow(task, graph, self.catalog), self.catalog)
        self.assertEqual(decision.status, "stopped")
        self.assertEqual(len(graph.nodes), 0)

    def test_trace_is_inspectable_json(self):
        trace = WorkflowTrace("trace-test")
        trace.record_final_status("validated", ["mask"])
        with tempfile.TemporaryDirectory() as temp_dir:
            output = trace.write(Path(temp_dir) / "trace.json")
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["events"][0]["event_type"], "run_completed")

    def test_closeout_evidence_covers_repair_and_controlled_stop(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            paths = generate_closeout_evidence(temp_dir)
            repair = json.loads(paths["repair"].read_text(encoding="utf-8"))
            stopped = json.loads(paths["controlled_stop"].read_text(encoding="utf-8"))
        self.assertEqual(repair["events"][-1]["payload"]["status"], "validated_after_repair")
        self.assertEqual(stopped["events"][-1]["payload"]["status"], "controlled_stop")
        self.assertEqual(stopped["events"][2]["payload"]["decision"]["status"], "stopped")


if __name__ == "__main__":
    unittest.main(verbosity=2)
