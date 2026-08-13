"""No-API tests for registered-tool-only D3-light execution."""

import unittest

from evaluation.ch1.d3_light_tool_executor import D3LightToolExecutor


class D3LightToolExecutorTests(unittest.TestCase):
    def test_unknown_tool_returns_structured_stop_evidence(self):
        result = D3LightToolExecutor().execute("calculate_ndsi", {})
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "tool_not_registered")

    def test_failure_fixture_occurs_once_and_before_real_threshold(self):
        executor = D3LightToolExecutor()
        first = executor.execute(
            "apply_threshold", {"index_raster": "missing.tif"}, inject_transient_failure=True
        )
        second = executor.execute(
            "apply_threshold", {"index_raster": "missing.tif"}, inject_transient_failure=True
        )
        self.assertFalse(first["success"])
        self.assertEqual(first["error_code"], "fixture_transient_write_failure")
        self.assertFalse(second["success"])
        self.assertNotEqual(second.get("error_code"), "fixture_transient_write_failure")


if __name__ == "__main__":
    unittest.main(verbosity=2)
