"""
viz_kit — Visualization tools for remote sensing results

Generates publication-quality thematic maps, false-color composites,
and statistical charts. Outputs are saved to results/.
"""

import os
import numpy as np
import rasterio
from datetime import datetime

# Visualization dependencies — import lazily to fail gracefully
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


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


def _get_geo_bounds(src) -> dict:
    """Extract geographic bounds from rasterio dataset."""
    if src.crs and src.bounds:
        return {
            "left": src.bounds.left,
            "right": src.bounds.right,
            "top": src.bounds.top,
            "bottom": src.bounds.bottom,
            "crs": str(src.crs),
        }
    return {}


def _load_single_band(file_path: str):
    """Load first band as numpy array + rasterio dataset."""
    with rasterio.open(file_path) as src:
        arr = src.read(1).astype(np.float32)
        bounds = _get_geo_bounds(src)
        profile = src.profile.copy()
    return arr, bounds, profile


# ──────────────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────────────

def plot_index_map(file_path: str, index_name: str = None,
                   cmap: str = None, vmin: float = None,
                   vmax: float = None,
                   output_name: str = None,
                   show_colorbar: bool = True,
                   title: str = None) -> dict:
    """
    Plot a single-band index map (NDVI, LST, NDWI, etc.) as a GeoTIFF overlay.

    Args:
        file_path: Path to single-band raster (e.g. NDVI result).
        index_name: Name of the index for coloring and labels. Auto-detected if None.
        cmap: Matplotlib colormap name. Auto-selected if None:
              - NDVI/NDWI/NBR: 'RdYlGn'
              - LST: 'RdYlBu_r' (red=hot, blue=cold)
              - Default: 'viridis'
        vmin, vmax: Color scale bounds. Auto-computed from data if None.
        output_name: Custom name for the output file. Auto-generated if None.
        show_colorbar: Whether to show a color scale bar.
        title: Plot title. Auto-generated if None.

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "data": {output_path, file_name, index_name, cmap, vmin, vmax}
        }
    """
    if not HAS_MATPLOTLIB:
        return {
            "success": False,
            "message": "matplotlib is not installed. Install it with: pip install matplotlib",
            "data": None
        }

    try:
        arr, bounds, _ = _load_single_band(file_path)

        # Auto-detect index name and colormap
        fname = os.path.basename(file_path).lower()
        if index_name is None:
            for name in ["ndvi", "evi", "ndwi", "lst", "nbr", "msavi", "ndbi"]:
                if name in fname:
                    index_name = name.upper()
                    break
            if index_name is None:
                index_name = "Index"

        if cmap is None:
            cmap_map = {"ndvi": "RdYlGn", "lst": "RdYlBu_r", "ndwi": "Blues",
                        "nbr": "RdYlGn", "evi": "RdYlGn", "msavi": "RdYlGn"}
            cmap = cmap_map.get(index_name.lower(), "viridis")

        # Auto-compute vmin/vmax
        arr_clean = arr[~np.isnan(arr)]
        if vmin is None:
            vmin = float(np.nanmin(arr_clean)) if arr_clean.size > 0 else -1
        if vmax is None:
            vmax = float(np.nanmax(arr_clean)) if arr_clean.size > 0 else 1

        if title is None:
            title = f"{index_name} Distribution Map"

        ts = _get_timestamp()
        out_name = output_name or f"map_{index_name.lower()}_{ts}"
        fname_jpg = f"final_map_{out_name}.jpg"
        out_path = os.path.join(_ensure_results_dir(), fname_jpg)

        fig, ax = plt.subplots(figsize=(10, 8))
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

        if bounds:
            extent = [bounds["left"], bounds["right"], bounds["bottom"], bounds["top"]]
            im = ax.imshow(arr, cmap=cmap, norm=norm, extent=extent, origin="upper")
        else:
            im = ax.imshow(arr, cmap=cmap, norm=norm, origin="upper")

        ax.set_title(title, fontsize=14, pad=12)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.tick_params(labelsize=9)

        if show_colorbar:
            cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
            cbar.set_label(index_name, fontsize=11)

        plt.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)

        return {
            "success": True,
            "message": f"Map saved: {fname_jpg}",
            "data": {
                "output_path": out_path,
                "file_name": fname_jpg,
                "index_name": index_name,
                "cmap": cmap,
                "vmin": vmin,
                "vmax": vmax,
                "nan_pixels": int(np.sum(np.isnan(arr))),
            }
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"Plot failed: {e}", "data": None}


def plot_thematic_map(file_path: str, class_labels: dict = None,
                      output_name: str = None,
                      title: str = None) -> dict:
    """
    Plot a classified/thematic map with discrete color mapping for each class.

    Args:
        file_path: Path to classified raster (e.g. threshold mask from analysis_kit).
        class_labels: Dict mapping class values (int) to label strings.
                      e.g. {0: "Non-vegetation", 1: "Vegetation"}
                      If None, uses numeric values.
        output_name: Custom output name. Auto-generated if None.
        title: Plot title.

    Returns:
        dict: {success, message, data: {output_path, file_name}}
    """
    if not HAS_MATPLOTLIB:
        return {
            "success": False,
            "message": "matplotlib is not installed.",
            "data": None
        }

    try:
        arr, bounds, _ = _load_single_band(file_path)

        ts = _get_timestamp()
        out_name = output_name or os.path.splitext(os.path.basename(file_path))[0]
        fname_jpg = f"final_thematic_{out_name}_{ts}.jpg"
        out_path = os.path.join(_ensure_results_dir(), fname_jpg)

        classes = sorted([int(v) for v in np.unique(arr) if not np.isnan(v)])

        if class_labels is None:
            class_labels = {c: f"Class {c}" for c in classes}

        fig, ax = plt.subplots(figsize=(10, 8))

        # Create discrete colormap
        n = len(classes)
        cmap = plt.cm.get_cmap("Set1", n) if n <= 9 else plt.cm.get_cmap("tab20", n)

        if bounds:
            extent = [bounds["left"], bounds["right"], bounds["bottom"], bounds["top"]]
            ax.imshow(arr, cmap=cmap, vmin=min(classes) - 0.5,
                     vmax=max(classes) + 0.5, extent=extent, origin="upper")
        else:
            ax.imshow(arr, cmap=cmap, vmin=min(classes) - 0.5,
                     vmax=max(classes) + 0.5, origin="upper")

        # Legend
        handles = [plt.Rectangle((0, 0), 1, 1, color=cmap(i / n))
                   for i in range(n)]
        labels = [class_labels.get(classes[i], f"Class {classes[i]}") for i in range(n)]
        ax.legend(handles, labels, loc="lower right", fontsize=9,
                 framealpha=0.9, title="Classes")
        ax.set_title(title or f"Thematic Map: {out_name}", fontsize=13, pad=10)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        plt.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)

        return {
            "success": True,
            "message": f"Thematic map saved: {fname_jpg}",
            "data": {
                "output_path": out_path,
                "file_name": fname_jpg,
                "classes": classes,
            }
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"Thematic plot failed: {e}", "data": None}


def plot_false_color_composite(file_path: str = None,
                                nir_band: int = 8,
                                red_band: int = 4,
                                green_band: int = 3,
                                output_name: str = None) -> dict:
    """
    Generate a false-color composite image from three spectral bands.

    Default (Sentinel-2): NIR=Band8, Red=Band4, Green=Band3
    False color: NIR→Red channel, Red→Green channel, Green→Blue channel
    → Vegetation appears red, urban areas cyan/white, water dark blue.

    Args:
        file_path: Path to multi-band raster. Auto-discovers if None.
        nir_band, red_band, green_band: 1-based band indices.
        output_name: Custom output name.

    Returns:
        dict: {success, message, data: {output_path, file_name}}
    """
    if not HAS_MATPLOTLIB:
        return {
            "success": False,
            "message": "matplotlib is not installed.",
            "data": None
        }

    try:
        if file_path is None:
            from .io_kit import _resolve_data_path
            file_path = _resolve_data_path(None)

        with rasterio.open(file_path) as src:
            nir = src.read(nir_band).astype(np.float32)
            red = src.read(red_band).astype(np.float32)
            green = src.read(green_band).astype(np.float32)
            bounds = _get_geo_bounds(src)
            nodata = src.nodata

        # Replace nodata
        if nodata is not None:
            nir = np.where(nir == nodata, np.nan, nir)
            red = np.where(red == nodata, np.nan, red)
            green = np.where(green == nodata, np.nan, green)

        # Normalize to 0-1 for display
        def normalize(arr):
            lo, hi = np.nanpercentile(arr, [2, 98])
            arr_norm = (arr - lo) / (hi - lo)
            return np.clip(arr_norm, 0, 1)

        rgb = np.dstack([normalize(nir), normalize(red), normalize(green)])

        ts = _get_timestamp()
        fname_jpg = f"final_fcc_{output_name or f'bands{nir_band}{red_band}{green_band}'}_{ts}.jpg"
        out_path = os.path.join(_ensure_results_dir(), fname_jpg)

        fig, ax = plt.subplots(figsize=(10, 8))
        if bounds:
            extent = [bounds["left"], bounds["right"], bounds["bottom"], bounds["top"]]
            ax.imshow(rgb, extent=extent, origin="upper")
        else:
            ax.imshow(rgb, origin="upper")

        ax.set_title(f"False Color Composite (NIR={nir_band}, Red={red_band}, Green={green_band})",
                     fontsize=12, pad=10)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")

        plt.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)

        return {
            "success": True,
            "message": f"False-color composite saved: {fname_jpg}",
            "data": {
                "output_path": out_path,
                "file_name": fname_jpg,
                "bands": {"nir": nir_band, "red": red_band, "green": green_band},
            }
        }
    except FileNotFoundError as e:
        return {"success": False, "message": str(e), "data": None}
    except Exception as e:
        return {"success": False, "message": f"False-color composite failed: {e}", "data": None}
