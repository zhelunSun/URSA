"""
io_kit — Raster I/O and metadata utilities

Provides standardized read/write access to satellite raster data.
All functions return structured dicts with 'success', 'message', and 'data' fields.
"""

import os
import json
import numpy as np
import rasterio
from rasterio.io import DatasetReader


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_project_root() -> str:
    """Return the ExpertsRS project root (parent of tools/)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _ensure_results_dir(subfolder: str = "") -> str:
    """Create results/ subfolder and return its absolute path."""
    root = _get_project_root()
    results = os.path.join(root, "results")
    if subfolder:
        results = os.path.join(results, subfolder)
    os.makedirs(results, exist_ok=True)
    return results


def _resolve_data_path(file_path: str = None) -> str:
    """Resolve a data file path to absolute, checking both relative and absolute."""
    root = _get_project_root()
    if file_path:
        if os.path.isabs(file_path) and os.path.exists(file_path):
            return file_path
        rel = os.path.join(root, file_path)
        if os.path.exists(rel):
            return rel
        # Try as-is
        if os.path.exists(file_path):
            return os.path.abspath(file_path)
        raise FileNotFoundError(f"Data file not found: {file_path}")
    # Auto-discover: look for .tif files in data/
    data_dir = os.path.join(root, "data")
    if not os.path.exists(data_dir):
        raise FileNotFoundError("No 'data/' directory found in project root.")
    tif_files = [f for f in os.listdir(data_dir) if f.lower().endswith((".tif", ".tiff"))]
    if not tif_files:
        raise FileNotFoundError("No .tif files found in data/ directory.")
    if len(tif_files) == 1:
        return os.path.join(data_dir, tif_files[0])
    # Return first match; caller should specify if multiple exist
    return os.path.join(data_dir, tif_files[0])


# ──────────────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────────────

def list_available_data_files() -> dict:
    """
    List all available raster data files in the project's data/ directory.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {
                "files": list[str],          # relative file paths
                "abs_paths": list[str],      # absolute file paths
                "count": int
            }
        }
    """
    try:
        root = _get_project_root()
        data_dir = os.path.join(root, "data")
        if not os.path.exists(data_dir):
            return {
                "success": False,
                "message": "No 'data/' directory found.",
                "data": {"files": [], "abs_paths": [], "count": 0}
            }
        files = sorted([
            f for f in os.listdir(data_dir)
            if f.lower().endswith((".tif", ".tiff"))
        ])
        abs_paths = [os.path.join(data_dir, f) for f in files]
        return {
            "success": True,
            "message": f"Found {len(files)} raster file(s).",
            "data": {"files": files, "abs_paths": abs_paths, "count": len(files)}
        }
    except Exception as e:
        return {"success": False, "message": str(e), "data": None}


def read_raster_metadata(file_path: str = None) -> dict:
    """
    Read metadata and basic properties of a raster file.

    Args:
        file_path: Path to raster file. If None, auto-discovers from data/.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {
                "width", "height", "crs", "bounds",
                "nodata", "dtype", "count" (band count),
                "transform": dict representation,
                "band_descriptions": list[str],
                "file_path", "file_name"
            }
        }
    """
    try:
        abs_path = _resolve_data_path(file_path)
        with rasterio.open(abs_path) as src:
            meta = {
                "width": src.width,
                "height": src.height,
                "crs": str(src.crs) if src.crs else None,
                "bounds": src.bounds._asdict() if src.bounds else None,
                "nodata": src.nodata,
                "dtype": src.dtypes[0],
                "count": src.count,
                "transform": str(src.transform),
                "res": src.res,
                "band_descriptions": [str(src.descriptions[i]) or f"Band {i+1}" for i in range(src.count)],
                "file_path": abs_path,
                "file_name": os.path.basename(abs_path),
            }
        return {
            "success": True,
            "message": f"Metadata read successfully: {meta['file_name']} "
                       f"({meta['width']}x{meta['height']}, {meta['count']} bands, {meta['dtype']})",
            "data": meta
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"Failed to read raster: {e}", "data": None}


def read_raster_band(file_path: str = None, band_index: int = 1) -> dict:
    """
    Read a single band from a raster file as a numpy array.

    Args:
        file_path: Path to raster file. If None, auto-discovers.
        band_index: 1-based band index (1 = first band). Use 1-based indexing
                    to match physical band numbering that scientists expect.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {
                "array_shape": tuple,
                "dtype": str,
                "min", "max", "mean" (numpy statistics),
                "nodata_value",
                "band_index_used": int,  # 1-based
                "file_path"
            }
        }
    """
    try:
        abs_path = _resolve_data_path(file_path)
        with rasterio.open(abs_path) as src:
            if band_index < 1 or band_index > src.count:
                return {
                    "success": False,
                    "message": f"Band index {band_index} out of range. "
                               f"File has {src.count} band(s). Use band_index 1 to {src.count}.",
                    "data": None
                }
            arr = src.read(band_index)
            stats = {
                "array_shape": arr.shape,
                "dtype": str(arr.dtype),
                "min": float(np.nanmin(arr)) if arr.size > 0 else None,
                "max": float(np.nanmax(arr)) if arr.size > 0 else None,
                "mean": float(np.nanmean(arr)) if arr.size > 0 else None,
                "nodata_value": src.nodata,
                "band_index_used": band_index,  # 1-based as used by caller
                "file_path": abs_path,
                "file_name": os.path.basename(abs_path),
            }
        return {
            "success": True,
            "message": (f"Band {band_index} read: shape={arr.shape}, "
                        f"dtype={arr.dtype}, range=[{stats['min']:.4f}, {stats['max']:.4f}]"),
            "data": stats
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"Failed to read band: {e}", "data": None}


def read_raster_bands(file_path: str = None, band_indices: list[int] = None) -> dict:
    """
    Read multiple bands from a raster file.

    Args:
        file_path: Path to raster file. If None, auto-discovers.
        band_indices: List of 1-based band indices. e.g. [4, 8] for Red + NIR (Sentinel-2).
                      If None, reads all bands.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {
                "band_count": int,
                "shape": tuple,
                "dtype": str,
                "bands_read": list[int],  # 1-based indices
                "file_path"
            }
        }
    """
    try:
        abs_path = _resolve_data_path(file_path)
        with rasterio.open(abs_path) as src:
            if band_indices is None:
                bands = list(range(1, src.count + 1))
            else:
                for b in band_indices:
                    if b < 1 or b > src.count:
                        return {
                            "success": False,
                            "message": f"Band index {b} out of range (1-{src.count}).",
                            "data": None
                        }
                bands = band_indices
            arrays = [src.read(b) for b in bands]
            shape = arrays[0].shape
        return {
            "success": True,
            "message": f"Read {len(bands)} band(s): indices={bands}, shape={shape}",
            "data": {
                "band_count": len(bands),
                "shape": shape,
                "dtype": str(arrays[0].dtype),
                "bands_read": bands,  # 1-based
                "file_path": abs_path,
                "file_name": os.path.basename(abs_path),
            }
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"Failed to read bands: {e}", "data": None}


def save_raster(data, output_path: str, reference_file: str = None,
                 dtype: str = None, nodata: float = None) -> dict:
    """
    Save a numpy array as a GeoTIFF raster file.

    Args:
        data: 2D numpy array (for single-band) or 3D (H, W, C).
        output_path: Output file path (relative to results/ or absolute).
        reference_file: Path to reference raster for CRS/transform.
                         If None, uses first file in data/ directory.
        dtype: Data type string (e.g. 'float32', 'uint8'). If None, infers from data.
        nodata: No-data value. If None, uses reference file's nodata or -9999 for new files.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {"output_path": str, "shape": tuple, "dtype": str}
        }
    """
    try:
        import rasterio
        from rasterio.transform import from_bounds

        # Normalize output path
        if not os.path.isabs(output_path):
            output_path = os.path.join(_ensure_results_dir(), output_path)

        data = np.asarray(data)
        if data.ndim == 2:
            data = np.expand_dims(data, axis=0)
        count, height, width = data.shape

        # Get reference metadata
        ref_path = None
        if reference_file:
            try:
                ref_path = _resolve_data_path(reference_file)
            except FileNotFoundError:
                ref_path = None

        if ref_path is None:
            try:
                ref_path = _resolve_data_path(None)
            except FileNotFoundError:
                ref_path = None

        if ref_path and os.path.exists(ref_path):
            with rasterio.open(ref_path) as ref:
                profile = ref.profile.copy()
        else:
            # Fallback: create minimal profile
            profile = {
                "driver": "GTiff",
                "height": height,
                "width": width,
                "count": count,
                "dtype": dtype or str(data.dtype),
                "crs": None,
                "transform": None,
                "nodata": nodata if nodata is not None else -9999,
            }

        # Override with explicit args
        if dtype:
            data = data.astype(dtype)
            profile["dtype"] = dtype
        else:
            profile["dtype"] = str(data.dtype)

        profile["count"] = count
        profile["height"] = height
        profile["width"] = width
        if nodata is not None:
            profile["nodata"] = nodata
        elif "nodata" not in profile:
            profile["nodata"] = -9999

        with rasterio.open(output_path, "w", **profile) as dst:
            for i in range(count):
                dst.write(data[i], i + 1)

        return {
            "success": True,
            "message": f"Saved raster: {output_path} (shape={data.shape}, dtype={profile['dtype']})",
            "data": {
                "output_path": output_path,
                "shape": tuple(data.shape),
                "dtype": profile["dtype"]
            }
        }
    except Exception as e:
        return {"success": False, "message": f"Failed to save raster: {e}", "data": None}
