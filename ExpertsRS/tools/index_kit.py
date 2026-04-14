"""
index_kit — Remote sensing index calculations

Implements standard spectral indices: NDVI, EVI, NDWI, LST, NBR, etc.
Each function takes numpy arrays (already read by io_kit) and returns a dict.
Output is always float32, saved to results/ automatically.
"""

import os
import numpy as np
import rasterio
from .io_kit import _ensure_results_dir, _resolve_data_path


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_timestamp() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _load_two_bands(file_path: str, band_a: int, band_b: int):
    """Load two bands from a raster file. Returns (arr_a, arr_b, profile).
    
    band_a and band_b are 1-based (matching the public tool interface).
    Convert to 0-based for rasterio src.read().
    """
    with rasterio.open(file_path) as src:
        arr_a = src.read(band_a - 1).astype(np.float32)
        arr_b = src.read(band_b - 1).astype(np.float32)
        profile = src.profile.copy()
    return arr_a, arr_b, profile


def _safe_divide(num, denom, fill_value: float = np.nan) -> np.ndarray:
    """Element-wise safe division, avoiding divide-by-zero."""
    denom = np.where(denom == 0, np.nan, denom)
    result = num / denom
    result = np.where(np.isnan(result), fill_value, result)
    return result


def _save_index(arr: np.ndarray, profile: dict, index_name: str,
                 suffix: str = "", metadata: dict = None) -> dict:
    """Save a computed index array as GeoTIFF."""
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
        "min": float(np.nanmin(arr)),
        "max": float(np.nanmax(arr)),
        "mean": float(np.nanmean(arr)),
        "std": float(np.nanstd(arr)),
        "nan_count": int(np.sum(np.isnan(arr))),
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


# ──────────────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────────────

def calculate_ndvi(file_path: str = None, nir_band: int = 8,
                   red_band: int = 4) -> dict:
    """
    Calculate the Normalized Difference Vegetation Index (NDVI).

    NDVI = (NIR - Red) / (NIR + Red)
    Range: -1 to +1. Higher values indicate denser vegetation.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        nir_band: 1-based NIR band index (default 8 for Sentinel-2 Band 8).
        red_band: 1-based Red band index (default 4 for Sentinel-2 Band 4).

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {output_path, file_name, shape, min, max, mean, std}
        }
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arr_nir, arr_red, profile = _load_two_bands(abs_path, nir_band, red_band)

        # Handle nodata
        nodata = profile.get("nodata")
        if nodata is not None:
            arr_nir = np.where(arr_nir == nodata, np.nan, arr_nir)
            arr_red = np.where(arr_red == nodata, np.nan, arr_red)

        numerator = arr_nir - arr_red
        denominator = arr_nir + arr_red
        ndvi = _safe_divide(numerator, denominator, fill_value=np.nan)

        # Clip to valid NDVI range
        ndvi = np.clip(ndvi, -1.0, 1.0)

        return _save_index(ndvi, profile, "NDVI",
                           suffix=f"nir{ nir_band}_red{red_band}",
                           metadata={
                               "formula": "NDVI = (NIR - Red) / (NIR + Red)",
                               "nir_band": nir_band, "red_band": red_band,
                               "sensor": "Sentinel-2" if nir_band == 8 else "Unknown",
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"NDVI calculation failed: {e}", "data": None}


def calculate_evi(file_path: str = None, nir_band: int = 8,
                   red_band: int = 4, blue_band: int = 2) -> dict:
    """
    Calculate the Enhanced Vegetation Index (EVI).

    EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)
    More sensitive to high biomass areas than NDVI.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        nir_band: 1-based NIR band index (default 8 for Sentinel-2).
        red_band: 1-based Red band index (default 4 for Sentinel-2).
        blue_band: 1-based Blue band index (default 2 for Sentinel-2 Band 2).

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        with rasterio.open(abs_path) as src:
            arr_nir = src.read(nir_band - 1).astype(np.float32)
            arr_red = src.read(red_band - 1).astype(np.float32)
            arr_blue = src.read(blue_band - 1).astype(np.float32)
            profile = src.profile.copy()

        nodata = profile.get("nodata")
        if nodata is not None:
            arr_nir = np.where(arr_nir == nodata, np.nan, arr_nir)
            arr_red = np.where(arr_red == nodata, np.nan, arr_red)
            arr_blue = np.where(arr_blue == nodata, np.nan, arr_blue)

        evi = 2.5 * (arr_nir - arr_red) / (
            arr_nir + 6 * arr_red - 7.5 * arr_blue + 1
        )
        evi = np.where(np.isinf(evi), np.nan, evi)

        return _save_index(evi, profile, "EVI",
                           suffix=f"nir{nir_band}_red{red_band}_blue{blue_band}",
                           metadata={
                               "formula": "EVI = 2.5 * (NIR - Red) / (NIR + 6*Red - 7.5*Blue + 1)",
                               "nir_band": nir_band, "red_band": red_band, "blue_band": blue_band,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"EVI calculation failed: {e}", "data": None}


def calculate_ndwi(file_path: str = None, green_band: int = 3,
                    nir_band: int = 8) -> dict:
    """
    Calculate the Normalized Difference Water Index (NDWI).

    NDWI = (Green - NIR) / (Green + NIR)
    Used to detect open water features. Range: -1 to +1.
    Positive values near +1 indicate water; vegetation is typically near 0 or negative.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        green_band: 1-based Green band index (default 3 for Sentinel-2 Band 3).
        nir_band: 1-based NIR band index (default 8 for Sentinel-2 Band 8).

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arr_green, arr_nir, profile = _load_two_bands(abs_path, green_band, nir_band)

        nodata = profile.get("nodata")
        if nodata is not None:
            arr_green = np.where(arr_green == nodata, np.nan, arr_green)
            arr_nir = np.where(arr_nir == nodata, np.nan, arr_nir)

        ndwi = _safe_divide(arr_green - arr_nir, arr_green + arr_nir)
        ndwi = np.clip(ndwi, -1.0, 1.0)

        return _save_index(ndwi, profile, "NDWI",
                           suffix=f"green{green_band}_nir{nir_band}",
                           metadata={
                               "formula": "NDWI = (Green - NIR) / (Green + NIR)",
                               "green_band": green_band, "nir_band": nir_band,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"NDWI calculation failed: {e}", "data": None}


def calculate_nbr(file_path: str = None, nir_band: int = 8,
                   swir_band: int = 12) -> dict:
    """
    Calculate the Normalized Burn Ratio (NBR).

    NBR = (NIR - SWIR) / (NIR + SWIR)
    Used for burn severity mapping. Fresh vegetation = high positive;
    burned areas = low or negative values.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        nir_band: 1-based NIR band index (default 8 for Sentinel-2 Band 8).
        swir_band: 1-based SWIR band index (default 12 for Sentinel-2 Band 12).

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arr_nir, arr_swir, profile = _load_two_bands(abs_path, nir_band, swir_band)

        nodata = profile.get("nodata")
        if nodata is not None:
            arr_nir = np.where(arr_nir == nodata, np.nan, arr_nir)
            arr_swir = np.where(arr_swir == nodata, np.nan, arr_swir)

        nbr = _safe_divide(arr_nir - arr_swir, arr_nir + arr_swir)
        nbr = np.clip(nbr, -1.0, 1.0)

        return _save_index(nbr, profile, "NBR",
                           suffix=f"nir{nir_band}_swir{swir_band}",
                           metadata={
                               "formula": "NBR = (NIR - SWIR) / (NIR + SWIR)",
                               "nir_band": nir_band, "swir_band": swir_band,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"NBR calculation failed: {e}", "data": None}


def calculate_lst(file_path: str = None, thermal_band: int = 10,
                  emissivity: float = 0.95) -> dict:
    """
    Estimate Land Surface Temperature (LST) from thermal infrared data.

    Single-channel algorithm for Landsat / Sentinel-3:
    LST (°C) = BT / (1 + (wavelength * BT / rho) * ln(emissivity)) - 273.15

    Where:
      BT = Top-of-Atmosphere brightness temperature (K)
      wavelength = central wavelength of thermal band (microns)
      rho = h*c/sigma = 14387.9 µm·K (physics constant)
      emissivity = land surface emissivity (default 0.95 for general surfaces)

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        thermal_band: 1-based thermal band index (default 10 for Landsat-8/Sentinel-3).
        emissivity: Land surface emissivity (0.0-1.0). Default 0.95 for vegetation.

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        with rasterio.open(abs_path) as src:
            if thermal_band < 1 or thermal_band > src.count:
                return {
                    "success": False,
                    "message": f"Thermal band {thermal_band} out of range (1-{src.count}).",
                    "data": None
                }
            arr = src.read(thermal_band - 1).astype(np.float64)
            profile = src.profile.copy()

        nodata = profile.get("nodata")
        if nodata is not None:
            arr = np.where(arr == nodata, np.nan, arr)

        # Physical constants
        K1_CONSTANT = 774.89   # For Band 10 (Landsat 8/9)
        K2_CONSTANT = 1321.08   # For Band 10
        RHO = 14387.9          # µm·K

        # Step 1: Convert DN to TOA radiance (if needed — assumes already brightness temp for Sentinel-3)
        # Step 2: Convert to Brightness Temperature
        bt = (K2_CONSTANT / np.log(K1_CONSTANT / arr + 1))

        # Step 3: Correct for emissivity and convert to LST
        # Use emissivity = 0.95 as default
        lst = bt / (1 + (10.9 * 1e-6 * bt / RHO) * np.log(emissivity)) - 273.15
        lst = np.where(np.isnan(lst) | np.isinf(lst), np.nan, lst)

        return _save_index(lst.astype(np.float32), profile, "LST",
                           suffix=f"band{thermal_band}_e{emissivity}",
                           metadata={
                               "formula": "Single-channel LST algorithm (°C)",
                               "thermal_band": thermal_band,
                               "emissivity": emissivity,
                               "unit": "celsius",
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"LST estimation failed: {e}", "data": None}


def calculate_msavi(file_path: str = None, nir_band: int = 8,
                     red_band: int = 4) -> dict:
    """
    Calculate the Modified Soil-Adjusted Vegetation Index (MSAVI2).

    MSAVI = (2 * NIR + 1 - sqrt((2*NIR + 1)^2 - 8*(NIR - Red))) / 2
    Reduces soil background effects in sparse vegetation areas.

    Args:
        file_path: Path to raster file. Auto-discovers if None.
        nir_band: 1-based NIR band index (default 8 for Sentinel-2).
        red_band: 1-based Red band index (default 4 for Sentinel-2).

    Returns:
        dict: {success, message, data}
    """
    try:
        abs_path = _resolve_data_path(file_path)
        arr_nir, arr_red, profile = _load_two_bands(abs_path, nir_band, red_band)

        nodata = profile.get("nodata")
        if nodata is not None:
            arr_nir = np.where(arr_nir == nodata, np.nan, arr_nir)
            arr_red = np.where(arr_red == nodata, np.nan, arr_red)

        msavi = (2 * arr_nir + 1 - np.sqrt((2 * arr_nir + 1) ** 2 - 8 * (arr_nir - arr_red))) / 2
        msavi = np.where(np.isnan(msavi) | np.isinf(msavi), np.nan, msavi)

        return _save_index(msavi, profile, "MSAVI",
                           suffix=f"nir{nir_band}_red{red_band}",
                           metadata={
                               "formula": "MSAVI2 = (2*NIR+1 - sqrt((2*NIR+1)^2 - 8*(NIR-Red))) / 2",
                               "nir_band": nir_band, "red_band": red_band,
                           })
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"MSAVI calculation failed: {e}", "data": None}
