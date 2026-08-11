"""
index_kit — Remote sensing index calculations

Implements standard spectral indices: NDVI, EVI, NDWI, LST, NBR, etc.
Each function takes numpy arrays (already read by io_kit) and returns a dict.
Output is always float32, saved to results/ automatically.
"""

import os
import numpy as np
import rasterio
from .io_kit import (
    ScientificPreconditionError,
    _ensure_results_dir,
    _resolve_band_reference,
    _resolve_data_path,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _load_resolved_bands(file_path: str, band_references: dict[str, object]):
    """Load semantically resolved bands and return arrays, profile, provenance."""
    arrays = {}
    selections = {}
    with rasterio.open(file_path) as src:
        for role, reference in band_references.items():
            index, description, resolution = _resolve_band_reference(src, reference, role=role)
            arrays[role] = (
                src.read(index, masked=True).astype(np.float32).filled(np.nan)
            )
            selections[role] = {
                "requested": reference,
                "stack_index": index,
                "description": description,
                "resolution": resolution,
            }
        profile = src.profile.copy()
    no_signal = np.logical_and.reduce([
        np.isfinite(array) & (array == 0) for array in arrays.values()
    ])
    if np.any(no_signal):
        arrays = {
            role: np.where(no_signal, np.nan, array)
            for role, array in arrays.items()
        }
    return arrays, profile, selections


def _safe_divide(num, denom, fill_value: float = np.nan) -> np.ndarray:
    """Element-wise safe division, avoiding divide-by-zero."""
    denom = np.where(denom == 0, np.nan, denom)
    result = num / denom
    result = np.where(np.isnan(result), fill_value, result)
    return result


def _save_index(arr: np.ndarray, profile: dict, index_name: str,
                 suffix: str = "", metadata: dict = None) -> dict:
    """Save a computed index array as GeoTIFF."""
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        raise ScientificPreconditionError(
            f"{index_name} produced no finite pixels after nodata and denominator checks."
        )
    ts = _get_timestamp()
    fname = f"intermediate_{index_name.lower()}_{suffix}_{ts}.tif" if suffix \
            else f"intermediate_{index_name.lower()}_{ts}.tif"
    out_path = os.path.join(_ensure_results_dir(), fname)

    out_profile = profile.copy()
    out_profile.update({
        "dtype": "float32",
        "count": 1,
        "nodata": np.nan,
    })

    with rasterio.open(out_path, "w", **out_profile) as dst:
        dst.write(arr[np.newaxis, :, :].astype(np.float32))

    meta_info = {
        "output_path": out_path,
        "file_name": fname,
        "shape": arr.shape,
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "mean": float(np.mean(valid)),
        "std": float(np.std(valid)),
        "nan_count": int(np.sum(np.isnan(arr))),
        "valid_pixels": int(valid.size),
        "total_pixels": int(arr.size),
    }
    if metadata:
        meta_info.update(metadata)

    return {
        "success": True,
        "message": (f"{index_name} computed: range=[{meta_info['min']:.4f}, "
                    f"{meta_info['max']:.4f}], mean={meta_info['mean']:.4f}"),
        "data": meta_info
    }


def _scientific_failure(index_name: str, error: Exception) -> dict:
    return {
        "success": False,
        "message": f"{index_name} scientific precondition failed: {error}",
        "data": None,
        "error_code": "scientific_precondition_failed",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────────────

def calculate_ndvi(file_path: str = None, nir_band: str = "B8",
                   red_band: str = "B4") -> dict:
    """
    Calculate the Normalized Difference Vegetation Index (NDVI).

    NDVI = (NIR - Red) / (NIR + Red)
    Range: -1 to +1. Higher values indicate denser vegetation.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        nir_band: Semantic NIR band name (default B8). A numeric string or int
                  is treated as an explicit, already-verified 1-based stack index.
        red_band: Semantic red band name (default B4), or verified stack index.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {output_path, file_name, shape, min, max, mean, std}
        }
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arrays, profile, selections = _load_resolved_bands(
            abs_path, {"nir": nir_band, "red": red_band}
        )
        arr_nir, arr_red = arrays["nir"], arrays["red"]

        numerator = arr_nir - arr_red
        denominator = arr_nir + arr_red
        ndvi = _safe_divide(numerator, denominator, fill_value=np.nan)

        # Clip to valid NDVI range
        ndvi = np.clip(ndvi, -1.0, 1.0)

        return _save_index(ndvi, profile, "NDVI",
                           suffix=f"nir{selections['nir']['stack_index']}_red{selections['red']['stack_index']}",
                           metadata={
                               "formula": "NDVI = (NIR - Red) / (NIR + Red)",
                               "band_selection": selections,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return _scientific_failure("NDVI", e)
    except Exception as e:
        return {"success": False, "message": f"NDVI calculation failed: {e}", "data": None}


def calculate_evi(file_path: str = None, nir_band: str = "B8",
                  red_band: str = "B4", blue_band: str = "B2",
                  reflectance_scale: float = 10000.0) -> dict:
    """
    Calculate the Enhanced Vegetation Index (EVI).

    EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
    More sensitive to high biomass areas than NDVI.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        nir_band: Semantic NIR band name (default B8), or verified stack index.
        red_band: Semantic red band name (default B4), or verified stack index.
        blue_band: Semantic blue band name (default B2), or verified stack index.
        reflectance_scale: Divisor converting stored values to unitless
                           reflectance. Sentinel-2 L2A integer products use 10000.

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arrays, profile, selections = _load_resolved_bands(
            abs_path, {"nir": nir_band, "red": red_band, "blue": blue_band}
        )
        if not np.isfinite(reflectance_scale) or reflectance_scale <= 0:
            raise ScientificPreconditionError("reflectance_scale must be finite and positive.")
        arr_nir = arrays["nir"] / reflectance_scale
        arr_red = arrays["red"] / reflectance_scale
        arr_blue = arrays["blue"] / reflectance_scale

        evi = 2.5 * (arr_nir - arr_red) / (
            arr_nir + 6 * arr_red - 7.5 * arr_blue + 1
        )
        evi = np.where(np.isinf(evi), np.nan, evi)

        return _save_index(evi, profile, "EVI",
                           suffix=(f"nir{selections['nir']['stack_index']}_"
                                   f"red{selections['red']['stack_index']}_"
                                   f"blue{selections['blue']['stack_index']}"),
                           metadata={
                               "formula": "EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)",
                               "band_selection": selections,
                               "reflectance_scale": reflectance_scale,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return _scientific_failure("EVI", e)
    except Exception as e:
        return {"success": False, "message": f"EVI calculation failed: {e}", "data": None}


def calculate_ndwi(file_path: str = None, green_band: str = "B3",
                   nir_band: str = "B8") -> dict:
    """
    Calculate the Normalized Difference Water Index (NDWI).

    NDWI = (Green - NIR) / (Green + NIR)
    Used to detect open water features. Range: -1 to +1.
    Positive values near +1 indicate water; vegetation is typically near 0 or negative.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        green_band: Semantic green band name (default B3), or verified stack index.
        nir_band: Semantic NIR band name (default B8), or verified stack index.

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arrays, profile, selections = _load_resolved_bands(
            abs_path, {"green": green_band, "nir": nir_band}
        )
        arr_green, arr_nir = arrays["green"], arrays["nir"]

        ndwi = _safe_divide(arr_green - arr_nir, arr_green + arr_nir)
        ndwi = np.clip(ndwi, -1.0, 1.0)

        return _save_index(ndwi, profile, "NDWI",
                           suffix=(f"green{selections['green']['stack_index']}_"
                                   f"nir{selections['nir']['stack_index']}"),
                           metadata={
                               "formula": "NDWI = (Green - NIR) / (Green + NIR)",
                               "band_selection": selections,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return _scientific_failure("NDWI", e)
    except Exception as e:
        return {"success": False, "message": f"NDWI calculation failed: {e}", "data": None}


def calculate_nbr(file_path: str = None, nir_band: str = "B8",
                  swir_band: str = "B12") -> dict:
    """
    Calculate the Normalized Burn Ratio (NBR).

    NBR = (NIR - SWIR) / (NIR + SWIR)
    Used for burn severity mapping. Fresh vegetation = high positive;
    burned areas = low or negative values.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        nir_band: Semantic NIR band name (default B8), or verified stack index.
        swir_band: Semantic SWIR band name (default B12), or verified stack index.

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arrays, profile, selections = _load_resolved_bands(
            abs_path, {"nir": nir_band, "swir": swir_band}
        )
        arr_nir, arr_swir = arrays["nir"], arrays["swir"]

        nbr = _safe_divide(arr_nir - arr_swir, arr_nir + arr_swir)
        nbr = np.clip(nbr, -1.0, 1.0)

        return _save_index(nbr, profile, "NBR",
                           suffix=(f"nir{selections['nir']['stack_index']}_"
                                   f"swir{selections['swir']['stack_index']}"),
                           metadata={
                               "formula": "NBR = (NIR - SWIR) / (NIR + SWIR)",
                               "band_selection": selections,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return _scientific_failure("NBR", e)
    except Exception as e:
        return {"success": False, "message": f"NBR calculation failed: {e}", "data": None}


def calculate_lst(file_path: str = None, thermal_band: str = "B10",
                  emissivity: float = 0.95, sensor: str = None,
                  input_unit: str = None) -> dict:
    """
    Estimate Land Surface Temperature (LST) from thermal infrared data.

    Narrow single-channel algorithm for Landsat 8 Band 10 TOA radiance:
    LST (°C) = BT / (1 + (wavelength * BT / rho) * ln(emissivity)) - 273.15

    Where:
      BT = Top-of-Atmosphere brightness temperature (K)
      wavelength = central wavelength of thermal band (microns)
      rho = h*c/sigma = 14387.9 µm·K (physics constant)
      emissivity = land surface emissivity (default 0.95 for general surfaces)

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        thermal_band: Semantic thermal band name (default B10), or a separately
                      verified explicit 1-based stack index.
        emissivity: Land surface emissivity (0.0-1.0). Default 0.95 for vegetation.
        sensor: Must be explicitly set to ``landsat-8``.
        input_unit: Must be ``toa_radiance_w_m2_sr_um``. Reflectance, raw DN,
                    and brightness-temperature inputs are not accepted.

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        sensor_name = (sensor or "").strip().lower().replace("_", "-")
        if sensor_name not in {"landsat-8", "landsat8"}:
            raise ScientificPreconditionError(
                "LST requires an explicit sensor='landsat-8'. Sentinel-2 has no "
                "thermal band and must never be routed to this operator."
            )
        if input_unit != "toa_radiance_w_m2_sr_um":
            raise ScientificPreconditionError(
                "LST requires input_unit='toa_radiance_w_m2_sr_um'; raw DN, "
                "reflectance, and unspecified units are not radiometrically admissible."
            )
        if not 0 < emissivity <= 1:
            raise ScientificPreconditionError("Emissivity must be in the interval (0, 1].")

        with rasterio.open(abs_path) as src:
            band_index, description, resolution = _resolve_band_reference(
                src, thermal_band, role="thermal"
            )
            arr = src.read(band_index, masked=True).astype(np.float64).filled(np.nan)
            profile = src.profile.copy()

        if not np.any(np.isfinite(arr) & (arr > 0)):
            raise ScientificPreconditionError("Thermal radiance contains no finite positive pixels.")

        # Landsat 8 Band 10 constants and units.
        k1 = 774.8853
        k2 = 1321.0789
        wavelength_um = 10.895
        rho_um_k = 14387.76877

        # Convert TOA spectral radiance to brightness temperature.
        bt = k2 / np.log(k1 / arr + 1)

        # Correct for emissivity and convert Kelvin to Celsius. Wavelength and
        # rho intentionally share micrometre units.
        lst = bt / (1 + (wavelength_um * bt / rho_um_k) * np.log(emissivity)) - 273.15
        lst = np.where(np.isnan(lst) | np.isinf(lst), np.nan, lst)

        return _save_index(lst.astype(np.float32), profile, "LST",
                           suffix=f"band{band_index}_e{emissivity}",
                           metadata={
                               "formula": "Landsat 8 Band 10 single-channel LST (°C)",
                               "sensor": "landsat-8",
                               "input_unit": input_unit,
                               "band_selection": {
                                   "thermal": {
                                       "requested": thermal_band,
                                       "stack_index": band_index,
                                       "description": description,
                                       "resolution": resolution,
                                   }
                               },
                               "emissivity": emissivity,
                               "unit": "celsius",
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return _scientific_failure("LST", e)
    except Exception as e:
        return {"success": False, "message": f"LST estimation failed: {e}", "data": None}


def calculate_msavi(file_path: str = None, nir_band: str = "B8",
                    red_band: str = "B4",
                    reflectance_scale: float = 10000.0) -> dict:
    """
    Calculate the Modified Soil-Adjusted Vegetation Index (MSAVI2).

    MSAVI = (2 * NIR + 1 - sqrt((2*NIR + 1)^2 - 8*(NIR - Red))) / 2
    Reduces soil background effects in sparse vegetation areas.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        nir_band: Semantic NIR band name (default B8), or verified stack index.
        red_band: Semantic red band name (default B4), or verified stack index.
        reflectance_scale: Divisor converting stored values to unitless
                           reflectance. Sentinel-2 L2A integer products use 10000.

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arrays, profile, selections = _load_resolved_bands(
            abs_path, {"nir": nir_band, "red": red_band}
        )
        if not np.isfinite(reflectance_scale) or reflectance_scale <= 0:
            raise ScientificPreconditionError("reflectance_scale must be finite and positive.")
        arr_nir = arrays["nir"] / reflectance_scale
        arr_red = arrays["red"] / reflectance_scale

        discriminant = (2 * arr_nir + 1) ** 2 - 8 * (arr_nir - arr_red)
        msavi = np.where(
            discriminant >= 0,
            (2 * arr_nir + 1 - np.sqrt(np.where(discriminant >= 0, discriminant, np.nan))) / 2,
            np.nan,
        )
        msavi = np.where(np.isnan(msavi) | np.isinf(msavi), np.nan, msavi)

        return _save_index(msavi, profile, "MSAVI",
                           suffix=f"nir{selections['nir']['stack_index']}_red{selections['red']['stack_index']}",
                           metadata={
                               "formula": "MSAVI2 = (2*NIR+1 - sqrt((2*NIR+1)^2 - 8*(NIR-Red))) / 2",
                               "band_selection": selections,
                               "reflectance_scale": reflectance_scale,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except ScientificPreconditionError as e:
        return _scientific_failure("MSAVI", e)
    except Exception as e:
        return {"success": False, "message": f"MSAVI calculation failed: {e}", "data": None}
