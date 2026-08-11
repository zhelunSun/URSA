"""Deterministic tests for the Chapter 1 scientific precondition boundary."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from tools.analysis_kit import apply_mask, apply_threshold, calculate_area, zonal_statistics
from tools.index_kit import calculate_evi, calculate_lst, calculate_msavi, calculate_ndvi


def _write_raster(
    path: Path,
    bands: list[np.ndarray],
    *,
    descriptions: list[str] | None = None,
    crs: str = "EPSG:32650",
    nodata=None,
    transform=None,
) -> None:
    profile = {
        "driver": "GTiff",
        "height": bands[0].shape[0],
        "width": bands[0].shape[1],
        "count": len(bands),
        "dtype": str(bands[0].dtype),
        "crs": crs,
        "transform": transform or from_origin(500000, 4400000, 10, 10),
        "nodata": nodata,
    }
    with rasterio.open(path, "w", **profile) as dataset:
        for index, band in enumerate(bands, start=1):
            dataset.write(band, index)
        if descriptions:
            for index, description in enumerate(descriptions, start=1):
                dataset.set_band_description(index, description)


class ScientificPreconditionTests(unittest.TestCase):
    def _remove_tool_output(self, result: dict) -> None:
        if result.get("success") and result.get("data", {}).get("output_path"):
            Path(result["data"]["output_path"]).unlink(missing_ok=True)

    def test_ndvi_resolves_semantic_bands_not_physical_numbers_as_positions(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "described.tif"
            red = np.full((2, 2), 2, dtype=np.float32)
            nir = np.full((2, 2), 6, dtype=np.float32)
            _write_raster(source, [red, nir], descriptions=["B4", "B8"])

            result = calculate_ndvi(str(source))
            try:
                self.assertTrue(result["success"], result["message"])
                selection = result["data"]["band_selection"]
                self.assertEqual(selection["nir"]["stack_index"], 2)
                self.assertEqual(selection["red"]["stack_index"], 1)
                self.assertEqual(selection["nir"]["resolution"], "band_description")
                self.assertAlmostEqual(result["data"]["mean"], 0.5, places=6)
            finally:
                self._remove_tool_output(result)

    def test_semantic_band_request_stops_when_descriptions_are_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "anonymous_stack.tif"
            _write_raster(
                source,
                [np.ones((2, 2), dtype=np.float32), np.ones((2, 2), dtype=np.float32)],
            )
            result = calculate_ndvi(str(source))
        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "scientific_precondition_failed")
        self.assertIn("no band descriptions", result["message"])

    def test_evi_scales_sentinel_integer_reflectance_before_constant_term(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reflectance.tif"
            blue = np.array([[1000, 0], [1000, 1000]], dtype=np.float32)
            red = np.array([[2000, 0], [2000, 2000]], dtype=np.float32)
            nir = np.array([[6000, 0], [6000, 6000]], dtype=np.float32)
            _write_raster(source, [blue, red, nir], descriptions=["B2", "B4", "B8"])
            result = calculate_evi(str(source))
            try:
                self.assertTrue(result["success"], result["message"])
                self.assertAlmostEqual(result["data"]["mean"], 1.0 / 2.05, places=6)
                self.assertEqual(result["data"]["nan_count"], 1)
                self.assertEqual(result["data"]["reflectance_scale"], 10000.0)
            finally:
                self._remove_tool_output(result)

    def test_msavi_records_reflectance_scale(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "reflectance.tif"
            red = np.full((2, 2), 2000, dtype=np.float32)
            nir = np.full((2, 2), 6000, dtype=np.float32)
            _write_raster(source, [red, nir], descriptions=["B4", "B8"])
            result = calculate_msavi(str(source))
            try:
                self.assertTrue(result["success"], result["message"])
                self.assertEqual(result["data"]["reflectance_scale"], 10000.0)
                self.assertGreater(result["data"]["mean"], 0)
            finally:
                self._remove_tool_output(result)

    def test_lst_rejects_sentinel2_even_when_a_tenth_stack_band_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sentinel2.tif"
            descriptions = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
            bands = [np.full((2, 2), 10, dtype=np.float32) for _ in descriptions]
            _write_raster(source, bands, descriptions=descriptions)
            result = calculate_lst(
                str(source),
                sensor="landsat-8",
                input_unit="toa_radiance_w_m2_sr_um",
            )
        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "scientific_precondition_failed")
        self.assertIn("B10", result["message"])

    def test_threshold_counts_nodata_outside_both_classes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "index.tif"
            values = np.array([[0.1, 0.4], [np.nan, 0.7]], dtype=np.float32)
            _write_raster(source, [values], nodata=np.nan)
            result = apply_threshold(str(source), 0.3, output_name="nodata_test")
            try:
                self.assertTrue(result["success"], result["message"])
                data = result["data"]
                self.assertEqual(data["total_pixels"], 4)
                self.assertEqual(data["valid_pixels"], 3)
                self.assertEqual(data["nodata_pixels"], 1)
                self.assertEqual(data["pixel_counts"], {"class_0": 1, "class_1": 2})
                with rasterio.open(data["output_path"]) as mask:
                    self.assertEqual(set(np.unique(mask.read(1))), {0, 1, 255})
            finally:
                self._remove_tool_output(result)

    def test_area_uses_projected_units_and_excludes_nodata(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "mask_utm.tif"
            mask = np.array([[0, 1], [255, 1]], dtype=np.uint8)
            _write_raster(source, [mask], nodata=255)
            result = calculate_area(str(source))
        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["data"]["pixel_counts"], {"0": 1, "1": 2})
        self.assertAlmostEqual(result["data"]["pixel_area_km2"], 0.0001, places=8)
        self.assertEqual(result["data"]["nodata_pixels"], 1)

    def test_area_stops_on_geographic_crs_without_verified_override(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "mask_wgs84.tif"
            mask = np.ones((2, 2), dtype=np.uint8)
            _write_raster(source, [mask], crs="EPSG:4326")
            result = calculate_area(str(source))
        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "scientific_precondition_failed")
        self.assertIn("geographic CRS", result["message"])

    def test_mask_stops_when_grids_are_not_aligned(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.tif"
            mask = Path(directory) / "mask.tif"
            _write_raster(source, [np.ones((2, 2), dtype=np.float32)])
            _write_raster(
                mask,
                [np.ones((2, 2), dtype=np.uint8)],
                transform=from_origin(500010, 4400000, 10, 10),
            )
            result = apply_mask(str(source), str(mask))
        self.assertFalse(result["success"])
        self.assertEqual(result.get("error_code"), "scientific_precondition_failed")
        self.assertIn("aligned rasters", result["message"])

    def test_zonal_statistics_excludes_value_and_zone_nodata(self):
        with tempfile.TemporaryDirectory() as directory:
            zones = Path(directory) / "zones.tif"
            values = Path(directory) / "values.tif"
            _write_raster(
                zones,
                [np.array([[1, 1], [255, 2]], dtype=np.uint8)],
                nodata=255,
            )
            _write_raster(
                values,
                [np.array([[2.0, np.nan], [100.0, 8.0]], dtype=np.float32)],
                nodata=np.nan,
            )
            result = zonal_statistics(str(zones), str(values))
        self.assertTrue(result["success"], result["message"])
        self.assertEqual(result["data"]["zones"]["1"]["pixel_count"], 1)
        self.assertEqual(result["data"]["zones"]["1"]["mean"], 2.0)
        self.assertEqual(result["data"]["zones"]["2"]["mean"], 8.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
