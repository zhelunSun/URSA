"""system-offline: end-to-end contracts for the authoritative runtime."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
import sys

try:
    from ExpertsRS import ExpertsRSSystem, LocalToolExecutor, RunRequest, RunStatus
    from ExpertsRS.models import RuntimeCapabilities
except ModuleNotFoundError:  # Support ``python -m unittest discover`` in ExpertsRS/.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ExpertsRS import ExpertsRSSystem, LocalToolExecutor, RunRequest, RunStatus
    from ExpertsRS.models import RuntimeCapabilities


SCENE = Path(__file__).parent / "data" / "Sentinel2_Dongcheng_20230718.tif"


class UnifiedSystemTests(unittest.TestCase):
    """system-offline tests use scripted decisions and the real local tools."""

    def _run(self, request: str, directory: Path, *, system: ExpertsRSSystem | None = None, capabilities: RuntimeCapabilities | None = None):
        return asyncio.run((system or ExpertsRSSystem()).run(RunRequest(
            request=request,
            data_paths=[SCENE],
            output_dir=directory,
            run_id="case",
            capabilities=capabilities or RuntimeCapabilities(),
        )))

    def test_ndvi_returns_report_artifacts_and_a_redacted_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Map NDVI for Dongcheng in summer 2023", Path(directory))
            trace = result.trace_path.read_text(encoding="utf-8")
            result_payload = json.loads((Path(directory) / "case" / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertIn("NDVI", result.report)
        self.assertEqual({item.artifact_type for item in result.artifacts}, {"metadata", "index_raster", "map"})
        self.assertNotIn(str(SCENE), trace)
        self.assertEqual(result_payload["status"], "completed")

    def test_recovery_reuses_ndvi_checkpoint_without_recomputing(self):
        system = ExpertsRSSystem(executor=LocalToolExecutor(inject_failures={"apply_threshold": 1}))
        with tempfile.TemporaryDirectory() as directory:
            result = self._run("Calculate green cover rate for Dongcheng", Path(directory), system=system)
            events = [json.loads(line) for line in result.trace_path.read_text(encoding="utf-8").splitlines()]
        actions = [event["payload"].get("tool_name") for event in events if event["event_type"] == "action_started"]
        plans = [event for event in events if event["event_type"] == "plan_version_recorded"]
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(actions.count("calculate_ndvi"), 1)
        self.assertEqual(actions.count("apply_threshold"), 2)
        self.assertEqual(len(plans), 2)
        self.assertIsNotNone(result.checkpoint_id)
        self.assertIn("mask_raster", {item.artifact_type for item in result.artifacts})

    def test_static_condition_stops_after_tool_failure(self):
        system = ExpertsRSSystem(executor=LocalToolExecutor(inject_failures={"apply_threshold": 1}))
        with tempfile.TemporaryDirectory() as directory:
            result = self._run(
                "Calculate green cover rate for Dongcheng", Path(directory), system=system,
                capabilities=RuntimeCapabilities(allow_plan_revision=False, allow_checkpoint_recovery=False),
            )
        self.assertEqual(result.status, RunStatus.CONTROLLED_STOP)

    def test_unsupported_and_scientifically_invalid_requests_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            ndsi = self._run("Map NDSI for Dongcheng", Path(directory) / "ndsi")
            lst = self._run("Derive LST for Dongcheng", Path(directory) / "lst")
        self.assertEqual(ndsi.status, RunStatus.CONTROLLED_STOP)
        self.assertEqual(lst.status, RunStatus.CONTROLLED_STOP)

    def test_clarification_can_resume_the_same_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            system = ExpertsRSSystem()
            first = self._run("What is the vegetation health condition?", root, system=system)
            resumed = asyncio.run(system.resume(first.run_id, "Please produce an NDVI map.", root))
        self.assertEqual(first.status, RunStatus.NEEDS_CLARIFICATION)
        self.assertTrue(first.questions)
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(resumed.run_id, first.run_id)

    def test_data_outside_the_allowed_root_is_denied_without_tool_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = asyncio.run(ExpertsRSSystem(allowed_data_roots=[root / "allowed"]).run(RunRequest(
                request="Map NDVI", data_paths=[SCENE], output_dir=root, run_id="denied",
            )))
        self.assertEqual(result.status, RunStatus.CONTROLLED_STOP)
        self.assertEqual(result.validation.tool_calls, 0)

    def test_duplicate_run_id_never_overwrites_prior_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._run("Map NDVI", root)
            with self.assertRaises(FileExistsError):
                self._run("Map NDVI", root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
