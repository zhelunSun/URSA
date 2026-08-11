"""
analysis_kit — Thematic analysis and statistics

Threshold segmentation, area calculation, masking, and basic time-series stats.
Works on outputs from index_kit or raw bands.
"""

import os
import numpy as np
import rasterio
from datetime import datetime

from .io_kit import ScientificPreconditionError


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _ensure_results_dir() -> str:
    from .io_kit import _get_project_root
    root = _get_project_root()
    results = os.path.join(root, "results")
    os.makedirs(results, exist_ok=True)
    return results


def _load_index_raster(file_path: str):
    """Load a single-band raster with every declared nodata pixel as NaN."""
    with rasterio.open(file_path) as src:
        arr = src.read(1, masked=True).astype(np.float32).filled(np.nan)
        profile = src.profile.copy()
    return arr, profile


def _assert_same_grid(left, right, operation: str) -> None:
    """Require identical raster shape, CRS, and affine grid before pixel algebra."""
    same_transform = left.transform.almost_equals(right.transform)
    if (
        left.width != right.width
        or left.height != right.height
        or left.crs != right.crs
        or not same_transform
    ):
        raise ScientificPreconditionError(
            f"{operation} requires aligned rasters with identical shape, CRS, and transform; "
            "explicit reprojection/resampling is required first."
        )


def _save_binary_mask(mask: np.ndarray, profile: dict,
                      label: str, extra_meta: dict = None) -> dict:
    """Save a binary/classified mask as GeoTIFF."""
    ts = _get_timestamp()
    fname = f"intermediate_mask_{label.lower()}_{ts}.tif"
    out_path = os.path.join(_ensure_results_dir(), fname)

    out_profile = profile.copy()
    out_profile.update({"dtype": "uint8", "count": 1, "nodata": 255})

    with rasterio.open(out_path, "w", **out_profile) as dst:
        dst.write(mask.astype(np.uint8), 1)

    info = {
        "output_path": out_path,
        "file_name": fname,
        "shape": mask.shape,
        "total_pixels": int(mask.size),
        "unique_values": [int(v) for v in np.unique(mask)],
    }
    if extra_meta:
        info.update(extra_meta)

    return {
        "success": True,
        "message": f"Mask saved: {fname} ({np.unique(mask).tolist()})",
        "data": info
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────────────

def apply_threshold(file_path: str, threshold_low: float,
                    threshold_high: float = None,
                    output_name: str = "result") -> dict:
    """
    Apply a threshold (or dual threshold) to a raster to create a binary mask.

    Args:
        file_path: Path to single-band input raster (e.g. NDVI result from index_kit).
        threshold_low: Lower threshold value.
        threshold_high: Upper threshold value. If None, applies single threshold
                         (pixels >= threshold_low become 1).
        output_name: Descriptive label for the output (e.g. "greenspace", "water").

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {
                "output_path": str,
                "threshold": {low, high or None},
                "pixel_counts": {class_0: int, class_1: int},
                "percentages": {class_0: float, class_1: float},
                "total_pixels": int,
                "valid_pixels": int,
                "nodata_pixels": int
            }
        }
    """
    try:
        arr, profile = _load_index_raster(file_path)

        valid_mask = np.isfinite(arr)
        arr_clean = np.where(valid_mask, arr, np.nan)

        if threshold_high is not None:
            # Dual threshold: threshold_low <= value <= threshold_high
            selected = (arr_clean >= threshold_low) & (arr_clean <= threshold_high)
            th_desc = f"[{threshold_low}, {threshold_high}]"
        else:
            # Single threshold: value >= threshold_low
            selected = arr_clean >= threshold_low
            th_desc = f">= {threshold_low}"

        mask = np.full(arr.shape, 255, dtype=np.uint8)
        mask[valid_mask] = selected[valid_mask].astype(np.uint8)
        class_0 = int(np.sum(mask == 0))
        class_1 = int(np.sum(mask == 1))
        total_valid = int(np.sum(valid_mask))
        nodata_pixels = int(mask.size - total_valid)
        pct = 100 * class_1 / total_valid if total_valid > 0 else 0

        extra_meta = {
            "threshold": {"low": threshold_low, "high": threshold_high},
            "pixel_counts": {"class_0": class_0, "class_1": class_1},
            "percentages": {"class_0": round(100 - pct, 2), "class_1": round(pct, 2)},
            "total_pixels": int(mask.size),
            "valid_pixels": total_valid,
            "nodata_pixels": nodata_pixels,
        }

        return _save_binary_mask(mask, profile, output_name, extra_meta)

    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"Threshold failed: {e}", "data": None}


def calculate_area(file_path: str, pixel_area_km2: float = None,
                   class_values: list[int] = None) -> dict:
    """
    Calculate the area (in km²) of each class in a classified raster mask.

    Args:
        file_path: Path to classified raster (e.g. threshold mask).
        pixel_area_km2: Area of one pixel in km². If None, attempts to derive
                        from raster metadata (preferred).
        class_values: Specific class values to analyze. If None, uses all unique.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {
                "areas_km2": {str(class_val): float},
                "areas_hectares": {str(class_val): float},
                "pixel_counts": {str(class_val): int},
                "total_area_km2": float,
                "pixel_area_km2": float,
                "unit": "km²" / "hectares"
            }
        }
    """
    try:
        arr, profile = _load_index_raster(file_path)

        valid_mask = np.isfinite(arr)

        # Derive pixel area only from a projected CRS with known linear units.
        if pixel_area_km2 is None:
            transform = profile.get("transform")
            crs = profile.get("crs")
            if transform is None or crs is None:
                raise ScientificPreconditionError(
                    "Area requires raster transform and CRS, or an explicit pixel_area_km2 override."
                )
            if not crs.is_projected:
                raise ScientificPreconditionError(
                    f"Area cannot be derived from geographic CRS {crs}; reproject to an "
                    "appropriate projected CRS or provide a verified pixel_area_km2."
                )
            unit_name, metres_per_unit = crs.linear_units_factor
            if not np.isfinite(metres_per_unit) or metres_per_unit <= 0:
                raise ScientificPreconditionError(
                    f"Projected CRS linear unit '{unit_name}' has no usable metre conversion."
                )
            res_x = abs(transform.a) * metres_per_unit
            res_y = abs(transform.e) * metres_per_unit
            pixel_area_km2 = (res_x * res_y) / 1_000_000
        elif not np.isfinite(pixel_area_km2) or pixel_area_km2 <= 0:
            raise ScientificPreconditionError("pixel_area_km2 must be a finite positive value.")

        if class_values is None:
            classes = sorted(int(v) for v in np.unique(arr[valid_mask]))
        else:
            classes = class_values

        areas = {}
        pixels = {}
        for c in classes:
            count = int(np.sum(arr == c))
            area = count * pixel_area_km2
            areas[str(c)] = round(area, 4)
            pixels[str(c)] = count

        total_area = sum(areas.values())
        hectares = {k: round(v * 100, 2) for k, v in areas.items()}

        return {
            "success": True,
            "message": (f"Area computed: {len(classes)} class(es), "
                        f"total={total_area:.4f} km² ({total_area*100:.2f} ha)"),
            "data": {
                "areas_km2": areas,
                "areas_hectares": hectares,
                "pixel_counts": pixels,
                "total_area_km2": round(total_area, 4),
                "total_area_hectares": round(total_area * 100, 2),
                "pixel_area_km2": pixel_area_km2,
                "valid_pixels": int(np.sum(valid_mask)),
                "nodata_pixels": int(arr.size - np.sum(valid_mask)),
                "crs": str(profile.get("crs")) if profile.get("crs") else None,
            }
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return {
            "success": False,
            "message": f"Area scientific precondition failed: {e}",
            "data": None,
            "error_code": "scientific_precondition_failed",
        }
    except Exception as e:
        return {"success": False, "message": f"Area calculation failed: {e}", "data": None}


def apply_mask(input_file: str, mask_file: str,
               mask_value: int = 1, nodata_value: float = np.nan) -> dict:
    """
    Apply a binary mask to an input raster, retaining only pixels where mask == mask_value.

    Args:
        input_file: Path to input raster to be masked (e.g. NDVI).
        mask_file: Path to binary mask raster.
        mask_value: The mask value to retain (default 1).
        nodata_value: Value to assign to masked-out pixels.

    Returns:
        dict: {success, message, data: {output_path, shape, pixels_retained}}
    """
    try:
        with rasterio.open(input_file) as src_in, rasterio.open(mask_file) as src_mask:
            _assert_same_grid(src_in, src_mask, "Mask application")
            arr_in = src_in.read(1, masked=True).astype(np.float32).filled(np.nan)
            arr_mask = src_mask.read(1, masked=True).astype(np.float32).filled(np.nan)
            profile_in = src_in.profile.copy()

        retain_mask = np.isfinite(arr_in) & np.isfinite(arr_mask) & (arr_mask == mask_value)
        result = np.full(arr_in.shape, nodata_value, dtype=np.float32)
        result[retain_mask] = arr_in[retain_mask]

        ts = _get_timestamp()
        fname = f"intermediate_masked_{ts}.tif"
        out_path = os.path.join(_ensure_results_dir(), fname)

        out_profile = profile_in.copy()
        out_profile.update({"dtype": "float32", "count": 1, "nodata": nodata_value})

        with rasterio.open(out_path, "w", **out_profile) as dst:
            dst.write(result[np.newaxis, :, :].astype(np.float32))

        retained = int(np.sum(retain_mask))
        total = result.size
        pct = 100 * retained / total if total > 0 else 0

        return {
            "success": True,
            "message": f"Mask applied: {retained}/{total} pixels retained ({pct:.1f}%)",
            "data": {
                "output_path": out_path,
                "file_name": fname,
                "shape": result.shape,
                "pixels_retained": retained,
                "pixels_masked": total - retained,
                "retention_pct": round(pct, 2),
            }
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return {
            "success": False,
            "message": f"Mask scientific precondition failed: {e}",
            "data": None,
            "error_code": "scientific_precondition_failed",
        }
    except Exception as e:
        return {"success": False, "message": f"Mask application failed: {e}", "data": None}


def zonal_statistics(zone_file: str, value_file: str,
                     zone_values: list[int] = None) -> dict:
    """
    Calculate zonal statistics: mean, min, max, std of value raster within each zone.

    Args:
        zone_file: Path to zone/region raster (e.g. administrative boundary mask).
        value_file: Path to value raster (e.g. NDVI, LST).
        zone_values: Specific zone values to analyze. If None, uses all unique.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {
                "zones": {
                    "zone_value": {
                        "mean": float, "min": float, "max": float,
                        "std": float, "pixel_count": int
                    }
                }
            }
        }
    """
    try:
        with rasterio.open(zone_file) as src_z, rasterio.open(value_file) as src_v:
            _assert_same_grid(src_z, src_v, "Zonal statistics")
            arr_z = src_z.read(1, masked=True).astype(np.float32).filled(np.nan)
            arr_v = src_v.read(1, masked=True).astype(np.float32).filled(np.nan)

        if zone_values is None:
            zones = sorted(int(v) for v in np.unique(arr_z[np.isfinite(arr_z)]))
        else:
            zones = zone_values

        results = {}
        for zone in zones:
            mask = arr_z == zone
            vals = arr_v[mask]
            vals = vals[np.isfinite(vals)]
            if len(vals) > 0:
                results[str(zone)] = {
                    "mean": round(float(np.nanmean(vals)), 4),
                    "min": round(float(np.nanmin(vals)), 4),
                    "max": round(float(np.nanmax(vals)), 4),
                    "std": round(float(np.nanstd(vals)), 4),
                    "pixel_count": int(len(vals)),
                }

        return {
            "success": True,
            "message": f"Zonal stats computed for {len(results)} zone(s).",
            "data": {"zones": results, "zone_file": zone_file, "value_file": value_file}
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return {
            "success": False,
            "message": f"Zonal-statistics scientific precondition failed: {e}",
            "data": None,
            "error_code": "scientific_precondition_failed",
        }
    except Exception as e:
        return {"success": False, "message": f"Zonal statistics failed: {e}", "data": None}
