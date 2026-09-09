"""Focused domain tests for the bounded existing-product tools."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
try:
    import rasterio
    import shapefile
    from rasterio.crs import CRS
    from rasterio.transform import from_origin
except ImportError as error:  # Domain extras are intentionally absent in legacy envs.
    raise unittest.SkipTest(f"classification product domain dependencies unavailable: {error}")

from tools.output_context import use_output_directory
from tools.product_kit import CLASS_ORDER, plot_classification_map, summarize_classification


class ProductToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raster = self.root / "classified.tif"
        self.aoi = self.root / "aoi.shp"
        self._write_raster()
        self._write_aoi()

    def tearDown(self):
        self.temp.cleanup()

    def _write_raster(self, *, crs: CRS | None = CRS.from_epsg(4326), fill: int | None = None):
        values = np.arange(36, dtype=np.uint8).reshape(6, 6) % 8
        # One valid centre is nodata; the other values exercise all classes.
        if fill is None:
            values[2, 2] = 255
        else:
            values[:, :] = fill
        with rasterio.open(
            self.raster,
            "w",
            driver="GTiff",
            height=6,
            width=6,
            count=1,
            dtype="uint8",
            crs=crs,
            transform=from_origin(0, 6, 1, 1),
            nodata=255,
        ) as dst:
            dst.write(values, 1)

    def _write_aoi(self, *, crs: CRS = CRS.from_epsg(4326)):
        with shapefile.Writer(str(self.aoi), shapeType=shapefile.POLYGON) as writer:
            writer.field("id", "N")
            # Centres on x/y=1.5 and 4.5 are on the AOI boundary and must be
            # included.  The 2.5,2.5 centre is strictly inside the hole.
            writer.poly(
                [
                    [(1.5, 1.5), (1.5, 4.5), (4.5, 4.5), (4.5, 1.5), (1.5, 1.5)],
                    [(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 3.0), (2.0, 2.0)],
                ]
            )
            writer.record(1)
        self.aoi.with_suffix(".prj").write_text(crs.to_wkt(), encoding="utf-8")

    def test_summary_uses_boundary_includes_holes_excludes_and_writes_json(self):
        with use_output_directory(self.root / "out"):
            result = summarize_classification(str(self.raster), str(self.aoi))
        self.assertTrue(result["success"], result)
        data = result["data"]
        # 16 boundary-inclusive centres minus one centre strictly in the hole.
        self.assertEqual(data["aoi_pixel_centres"], 15)
        self.assertEqual(data["valid_pixels"] + data["nodata_pixels"], 15)
        self.assertEqual(data["class_order"], CLASS_ORDER)
        self.assertNotIn("preview", data)
        self.assertFalse(data["preview_sampling"]["runtime_metadata_contains_raster_content"])
        written = json.loads(Path(data["output_path"]).read_text(encoding="utf-8"))
        self.assertEqual(written["data"]["counts"], data["counts"])
        self.assertEqual(set(data["provenance"]["aoi_component_hashes"]), {".shp", ".shx", ".dbf", ".prj"})

    def test_summary_refuses_output_collision(self):
        with use_output_directory(self.root / "out"):
            first = summarize_classification(str(self.raster), str(self.aoi))
            second = summarize_classification(str(self.raster), str(self.aoi))
        self.assertTrue(first["success"])
        self.assertFalse(second["success"])
        self.assertEqual(second["error_code"], "output_collision")

    def test_summary_rejects_invalid_code_anywhere_in_raster(self):
        with rasterio.open(self.raster, "r+") as dataset:
            values = dataset.read(1)
            values[0, 0] = 8
            dataset.write(values, 1)
        with use_output_directory(self.root / "out"):
            result = summarize_classification(str(self.raster), str(self.aoi))
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "product_precondition_failed")

    def test_summary_rejects_crs_mismatch_and_zero_valid(self):
        self._write_aoi(crs=CRS.from_epsg(3857))
        with use_output_directory(self.root / "out-crs"):
            mismatch = summarize_classification(str(self.raster), str(self.aoi))
        self.assertFalse(mismatch["success"])
        self.assertEqual(mismatch["error_code"], "product_precondition_failed")

        self._write_aoi()
        self._write_raster(fill=255)
        with use_output_directory(self.root / "out-empty"):
            empty = summarize_classification(str(self.raster), str(self.aoi))
        self.assertFalse(empty["success"])
        self.assertEqual(empty["error_code"], "product_precondition_failed")

    def test_map_checks_provenance_and_uses_current_counts(self):
        with use_output_directory(self.root / "out"):
            summary = summarize_classification(str(self.raster), str(self.aoi))
            self.assertTrue(summary["success"], summary)
            plotted = plot_classification_map(
                str(self.raster), str(self.aoi), summary["data"]["output_path"]
            )
        self.assertTrue(plotted["success"], plotted)
        data = plotted["data"]
        self.assertTrue(Path(data["output_path"]).is_file())
        self.assertEqual(data["secondary_outputs"][0]["kind"], "svg")
        self.assertTrue(Path(data["secondary_outputs"][0]["path"]).is_file())
        self.assertTrue(Path(data["provenance"]["figure_contract_path"]).is_file())
        self.assertTrue(Path(data["provenance"]["render_manifest_path"]).is_file())
        contract = json.loads(Path(data["provenance"]["figure_contract_path"]).read_text(encoding="utf-8"))
        self.assertIn("not accuracy evidence", " ".join(contract["plot"]["required_status_text"]))
        self.assertIn("Tree", Path(data["secondary_outputs"][0]["path"]).read_text(encoding="utf-8"))

        audit_script = Path("C:/Users/zhelunStation/.codex/skills/scientific-figures/scripts/figure_audit.py")
        audit = subprocess.run(
            [
                sys.executable,
                str(audit_script),
                "--root",
                str(self.root / "out"),
                "--contract",
                data["provenance"]["figure_contract_path"],
                "--manifest",
                data["provenance"]["render_manifest_path"],
                "--json-out",
                str(self.root / "out" / "audit.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(audit.returncode, 0, audit.stdout + audit.stderr)
        self.assertEqual(json.loads(audit.stdout)["status"], "pass")

    def test_map_rejects_changed_raster_against_frozen_composition(self):
        with use_output_directory(self.root / "out"):
            summary = summarize_classification(str(self.raster), str(self.aoi))
        self.assertTrue(summary["success"], summary)
        with rasterio.open(self.raster, "r+") as dataset:
            values = dataset.read(1)
            values[0, 0] = (int(values[0, 0]) + 1) % 8
            dataset.write(values, 1)
        with use_output_directory(self.root / "out-map"):
            result = plot_classification_map(str(self.raster), str(self.aoi), summary["data"]["output_path"])
        self.assertFalse(result["success"])
        self.assertEqual(result["error_code"], "composition_provenance_mismatch")


if __name__ == "__main__":
    unittest.main()
