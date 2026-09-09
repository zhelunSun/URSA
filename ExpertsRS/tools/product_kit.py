"""Bounded deterministic tools for describing an existing classification product.

This module deliberately describes the supplied product only.  It does not run
classification, estimate area, assess thematic accuracy, or infer ecological
meaning.  The pixel-centre and stripe computation is adapted from
``D:/Projects/phd-thesis/urbfo-agent-demo/scripts/local/beijing_product_reference.py``
(source SHA256 ``E6205B53F7B3A19AB9FAB19BED012DDC197B0C12700403D1815B85A6BF79F3E5``),
with the evaluator intake and its reference outputs intentionally excluded.

The optional domain dependencies (``pyshp`` and ``shapely``) are imported only
when a tool is called.  This keeps the historical 18-tool import surface
usable in environments that do not install the domain extras.
"""

from __future__ import annotations

import hashlib
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.windows import Window


CLASS_ORDER = [
    "tree",
    "shrub",
    "grass",
    "wetland",
    "impervious_surface",
    "water",
    "cropland",
    "bare_land",
]
CLASS_LABELS = {
    "tree": "Tree",
    "shrub": "Shrub",
    "grass": "Grass",
    "wetland": "Wetland",
    "impervious_surface": "Impervious surface",
    "water": "Water",
    "cropland": "Cropland",
    "bare_land": "Bare land",
}
CLASS_COLORS = [
    "#236c45",
    "#85ac5d",
    "#d1d675",
    "#66b6ad",
    "#bf7170",
    "#488fc2",
    "#efc070",
    "#b6a796",
]
NODATA = 255
PREVIEW_STRIDE = 12
SCHEMA_VERSION = "classification-product-v1"
REFERENCE_COMPUTATION = {
    "source": "D:/Projects/phd-thesis/urbfo-agent-demo/scripts/local/beijing_product_reference.py",
    "sha256": "E6205B53F7B3A19AB9FAB19BED012DDC197B0C12700403D1815B85A6BF79F3E5",
    "role": "pixel-centre stripe computation and display-only preview semantics",
}


def _sha256(path: Path) -> str:
    """Hash a source file in bounded chunks without modifying or staging it."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _default_output_directory() -> Path:
    return Path(__file__).resolve().parents[2] / "results"


def _output_directory() -> Path:
    from .output_context import current_output_directory

    return Path(current_output_directory(_default_output_directory()))


def _failure(message: str, error_code: str = "product_precondition_failed") -> dict[str, Any]:
    return {"success": False, "message": message, "data": None, "error_code": error_code}


def _safe_failure(error: Exception, *, map_context: bool = False) -> dict[str, Any]:
    """Return a useful failure class without disclosing local filesystem paths."""

    text = str(error).lower()
    if isinstance(error, FileExistsError):
        return _failure("Output collision; existing artifacts were preserved.", "output_collision")
    if map_context and ("composition" in text or "hash" in text):
        return _failure("Composition provenance check failed.", "composition_provenance_mismatch")
    if isinstance(error, FileNotFoundError):
        return _failure("Classification product input is unavailable.", "product_input_unavailable")
    if isinstance(error, RuntimeError):
        return _failure("Classification product domain dependencies are unavailable.", "domain_dependency_missing")
    if isinstance(error, AssertionError):
        return _failure("Classification product integrity check failed.", "product_integrity_failed")
    if isinstance(error, (ValueError, OSError)):
        return _failure("Classification product preconditions were not met.", "product_precondition_failed")
    return _failure("Classification product tool failed.", "product_tool_error")


def _require_year(year: int) -> None:
    if isinstance(year, bool) or not isinstance(year, int):
        raise ValueError("year must be an integer")


def _required_aoi_components(aoi_path: Path) -> dict[str, Path]:
    if aoi_path.suffix.lower() != ".shp":
        raise ValueError("AOI path must point to a .shp component")
    components = {suffix: aoi_path.with_suffix(suffix) for suffix in (".shp", ".shx", ".dbf", ".prj")}
    missing = [str(path) for path in components.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing AOI component(s): " + ", ".join(missing))
    return components


def _load_aoi(aoi_path: str | Path):
    """Read and validate a polygon AOI and its declared CRS.

    Imports are local by design; ``shapely`` and ``pyshp`` are domain extras.
    """

    try:
        import shapefile
        import shapely
        from shapely.geometry import MultiPolygon, shape
        from shapely.validation import explain_validity
    except ImportError as error:
        raise RuntimeError("pyshp and shapely are required for classification products") from error

    path = Path(aoi_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"AOI file not found: {path}")
    components = _required_aoi_components(path)
    try:
        with shapefile.Reader(str(path)) as reader:
            geometries = [shape(item.__geo_interface__) for item in reader.shapes()]
    except Exception as error:
        raise ValueError(f"Unable to read AOI shapefile: {error}") from error

    polygons = []
    for geometry in geometries:
        if (
            geometry.is_empty
            or not geometry.is_valid
            or geometry.geom_type not in ("Polygon", "MultiPolygon")
        ):
            reason = explain_validity(geometry)
            raise ValueError(f"Invalid or unsupported AOI geometry: {reason}")
        polygons.extend(geometry.geoms if geometry.geom_type == "MultiPolygon" else [geometry])
    if not polygons:
        raise ValueError("AOI contains no polygon geometry")
    geometry = MultiPolygon(polygons)
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError(f"Invalid combined AOI geometry: {explain_validity(geometry)}")

    try:
        aoi_crs = rasterio.crs.CRS.from_wkt(components[".prj"].read_text(encoding="utf-8"))
    except Exception as error:
        raise ValueError(f"AOI CRS is missing or unreadable: {error}") from error
    if aoi_crs is None:
        raise ValueError("AOI CRS is missing")
    # ``prepare`` is an optimization only; intersects_xy remains the semantic
    # operation and includes points exactly on polygon boundaries.
    shapely.prepare(geometry)
    hashes = {suffix: _sha256(component) for suffix, component in components.items()}
    optional_cpg = path.with_suffix(".cpg")
    if optional_cpg.is_file():
        hashes[".cpg"] = _sha256(optional_cpg)
        components[".cpg"] = optional_cpg
    return geometry, aoi_crs, components, hashes


def _compatible_crs(raster_crs, aoi_crs) -> bool:
    if raster_crs is None or aoi_crs is None:
        return False
    if raster_crs == aoi_crs:
        return True
    # Shapefile and GeoTIFF authority-axis declarations may differ.  Explicitly
    # allow only the reference's EPSG:4326 equivalence; never reproject.
    return raster_crs.to_epsg() == aoi_crs.to_epsg() == 4326


def _centre_mask(geometry, transform, row_offset: int, height: int, width: int) -> np.ndarray:
    if transform.b != 0 or transform.d != 0 or transform.a <= 0 or transform.e >= 0:
        raise ValueError("Only north-up original grids are admitted; no implicit reprojection")
    xs = transform.c + (np.arange(width) + 0.5) * transform.a
    ys = transform.f + (np.arange(row_offset, row_offset + height) + 0.5) * transform.e
    left, bottom, right, top = geometry.bounds
    columns = np.flatnonzero((xs >= left) & (xs <= right))
    rows = np.flatnonzero((ys >= bottom) & (ys <= top))
    mask = np.zeros((height, width), dtype=bool)
    if columns.size and rows.size:
        # intersects_xy includes a pixel centre exactly on a boundary and
        # respects holes in the supplied polygon geometry.
        import shapely

        mask[np.ix_(rows, columns)] = shapely.intersects_xy(
            geometry, xs[columns][None, :], ys[rows][:, None]
        )
    return mask


def _analyze(file_path: str | Path, aoi_path: str | Path) -> tuple[dict[str, Any], np.ndarray, dict[str, Any]]:
    raster_path = Path(file_path).resolve()
    if not raster_path.is_file():
        raise FileNotFoundError(f"Raster file not found: {raster_path}")
    geometry, aoi_crs, components, component_hashes = _load_aoi(aoi_path)
    raster_hash = _sha256(raster_path)
    total_hist = np.zeros(256, dtype=np.int64)
    aoi_hist = np.zeros(256, dtype=np.int64)
    preview: np.ndarray | None = None
    preview_extent: list[float] | None = None
    raster_shape: tuple[int, int] | None = None
    raster_crs_text: str | None = None

    with rasterio.open(raster_path) as source:
        if source.count != 1:
            raise ValueError("Raster must contain exactly one band")
        if source.dtypes != ("uint8",):
            raise ValueError("Raster must be uint8")
        if source.nodata != NODATA:
            raise ValueError("Raster nodata must be 255")
        if source.crs is None:
            raise ValueError("Raster CRS is missing")
        if not _compatible_crs(source.crs, aoi_crs):
            raise ValueError("Raster/AOI CRS conflict; only identical CRS or EPSG:4326 equivalence is admitted")
        if source.width <= 0 or source.height <= 0:
            raise ValueError("Raster has no pixels")
        if not (
            source.bounds.left <= geometry.bounds[0] <= geometry.bounds[2] <= source.bounds.right
            and source.bounds.bottom <= geometry.bounds[1] <= geometry.bounds[3] <= source.bounds.top
        ):
            raise ValueError("AOI is not fully contained in raster extent")
        preview = np.full(
            ((source.height - 1) // PREVIEW_STRIDE + 1, (source.width - 1) // PREVIEW_STRIDE + 1),
            254,
            dtype=np.uint8,
        )
        raster_shape = (source.height, source.width)
        raster_crs_text = str(source.crs)
        for start in range(0, source.height, 512):
            row_count = min(512, source.height - start)
            values = source.read(1, window=Window(0, start, source.width, row_count), masked=False)
            total_hist += np.bincount(values.ravel(), minlength=256)
            if np.any((values > 7) & (values != NODATA)):
                raise ValueError("Unexpected class code in raster; admitted codes are 0-7 and nodata 255")
            mask = _centre_mask(geometry, source.transform, start, row_count, source.width)
            selected = values[mask]
            aoi_hist += np.bincount(selected, minlength=256)
            rows = np.arange(start, start + row_count)
            sampled_rows = np.flatnonzero(rows % PREVIEW_STRIDE == 0)
            view = values[sampled_rows, ::PREVIEW_STRIDE].copy()
            view[~mask[sampled_rows, ::PREVIEW_STRIDE]] = 254
            preview[rows[sampled_rows] // PREVIEW_STRIDE] = view
        if int(total_hist.sum()) != source.width * source.height:
            raise AssertionError("Full raster decode count does not close")
        if int(aoi_hist[8:255].sum()) != 0:
            raise ValueError("Unexpected class code inside AOI")
        valid = int(aoi_hist[:8].sum())
        nodata = int(aoi_hist[NODATA])
        aoi_centres = valid + nodata
        if valid == 0:
            raise ValueError("No valid classified pixel centres in AOI")
        transform = source.transform
        dx, dy = PREVIEW_STRIDE * transform.a, -PREVIEW_STRIDE * transform.e
        x0, y0 = transform.c + 0.5 * transform.a, transform.f + 0.5 * transform.e
        preview_extent = [
            x0 - dx / 2,
            x0 + (preview.shape[1] - 0.5) * dx,
            y0 - (preview.shape[0] - 0.5) * dy,
            y0 + dy / 2,
        ]

    counts = {name: int(aoi_hist[index]) for index, name in enumerate(CLASS_ORDER)}
    fractions = {name: count / valid for name, count in counts.items()}
    data = {
        "schema_version": SCHEMA_VERSION,
        "product_profile": "existing-product-eight-class",
        "year": None,
        "class_order": list(CLASS_ORDER),
        "counts": counts,
        "fractions": fractions,
        "valid_pixels": valid,
        "nodata_pixels": nodata,
        "aoi_pixel_centres": aoi_centres,
        "raster_shape": list(raster_shape or ()),
        "scope": {
            "description": "Existing classification product description within the supplied AOI.",
            "pixel_rule": "Original pixel centres intersect AOI; boundary included; holes excluded.",
            "fraction_denominator": "valid_pixels (codes 0-7 only)",
            "claims_blocked": [
                "classification accuracy",
                "true area or area fraction",
                "ecological evidence or effect",
            ],
        },
        "preview_sampling": {
            "mode": "deterministic display-only preview",
            "row_stride_original_pixels": PREVIEW_STRIDE,
            "column_stride_original_pixels": PREVIEW_STRIDE,
            "mask_rule": "same AOI pixel-centre mask; no categorical resampling",
            "runtime_metadata_contains_raster_content": False,
        },
        "provenance": {
            "raster_path": str(raster_path),
            "raster_sha256": raster_hash,
            "raster_crs": raster_crs_text,
            "aoi_path": str(Path(aoi_path).resolve()),
            "aoi_component_hashes": component_hashes,
            "aoi_crs": aoi_crs.to_string(),
            "crs_handling": "same CRS or explicit EPSG:4326 equivalence; no reprojection",
            "computation_reference": dict(REFERENCE_COMPUTATION),
        },
    }
    aux = {
        "preview": preview,
        "preview_extent": preview_extent,
        "geometry": geometry,
        "raster_hash": raster_hash,
        "aoi_component_hashes": component_hashes,
        "aoi_components": components,
        "aoi_crs": aoi_crs,
        "raster_path": raster_path,
    }
    return data, preview, aux


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _write_plot_table(path: Path, data: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    """Write the exact count table consumed by the figure contract/audit."""

    columns = ["class_code", "class", "label", "count", "fraction"]
    rows = [
        {
            "class_code": str(index),
            "class": name,
            "label": CLASS_LABELS[name],
            "count": str(data["counts"][name]),
            "fraction": repr(data["fractions"][name]),
        }
        for index, name in enumerate(CLASS_ORDER)
    ]
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return columns, rows


def _canonical_table_fingerprint(rows: list[dict[str, str]], columns: list[str]) -> str:
    normalized: list[list[Any]] = []
    for row in rows:
        normalized_row: list[Any] = []
        for column in columns:
            value = row.get(column, "").strip()
            if value == "":
                normalized_row.append(None)
                continue
            try:
                number = float(value)
                normalized_row.append(int(number) if number.is_integer() else number)
            except ValueError:
                normalized_row.append(value)
        normalized.append(normalized_row)
    payload = json.dumps(
        {"columns": columns, "rows": normalized},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def summarize_classification(file_path: str, aoi_path: str, year: int = 2025) -> dict:
    """Summarize original-grid class counts and fractions inside a polygon AOI."""

    try:
        _require_year(year)
        data, _preview, _aux = _analyze(file_path, aoi_path)
        data["year"] = year
        output_path = _output_directory() / f"classification_summary_{year}.json"
        data["output_path"] = str(output_path)
        _write_json_exclusive(output_path, {"artifact_type": "classification_summary", "data": data})
        return {
            "success": True,
            "message": "Classification product summary saved.",
            "data": data,
        }
    except FileExistsError as error:
        return _safe_failure(error)
    except (FileNotFoundError, RuntimeError, ValueError, AssertionError, OSError) as error:
        return _safe_failure(error)
    except Exception as error:  # Keep the tool boundary deterministic for callers.
        return _safe_failure(error)


def _load_composition(composition_path: str | Path) -> tuple[dict[str, Any], str]:
    path = Path(composition_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Composition JSON not found: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise ValueError(f"Composition JSON is unreadable: {error}") from error
    if not isinstance(document, dict) or document.get("artifact_type") != "classification_summary":
        raise ValueError("Composition JSON is not a freshly generated classification summary")
    data = document.get("data")
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Composition JSON has an unsupported summary schema")
    return data, _sha256(path)


def _assert_composition_provenance(
    composition: dict[str, Any], composition_hash: str, current: dict[str, Any], year: int
) -> None:
    if composition.get("year") != year:
        raise ValueError("Composition year does not match requested map year")
    if composition.get("class_order") != CLASS_ORDER:
        raise ValueError("Composition class order does not match the v1 profile")
    provenance = composition.get("provenance")
    current_provenance = current.get("provenance")
    if not isinstance(provenance, dict) or not isinstance(current_provenance, dict):
        raise ValueError("Composition provenance is missing")
    if provenance.get("raster_sha256") != current_provenance.get("raster_sha256"):
        raise ValueError("Composition raster hash does not match current raster")
    if provenance.get("aoi_component_hashes") != current_provenance.get("aoi_component_hashes"):
        raise ValueError("Composition AOI component hashes do not match current AOI")
    if not composition_hash:
        raise ValueError("Composition provenance hash is empty")


def _figure_contract(data: dict[str, Any], aux: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    transformations = [
        "validate the existing uint8 single-band raster and AOI component hashes",
        "decode every original raster pixel in fixed 512-row stripes",
        "select original pixel centres intersecting the AOI; include boundary and exclude holes",
        "exclude nodata 255 from the valid-pixel composition denominator",
        "select every 12th original row and column for a display-only preview; no categorical resampling",
        "render current decoded counts and fractions in the fixed eight-class order",
    ]
    title = f"Existing classified product ({data['year']}) — AOI product description"
    note = "Display-only product description; not accuracy evidence, not area evidence, and not ecological evidence."
    return {
        "schema_version": "1.0",
        "figure_id": f"classification-product-map-{data['year']}",
        "research_status": "existing-product-description; thematic-validity-not-assessed",
        "source_data": {
            "path": str(paths["table"]),
            "sha256": aux["table_sha256"],
            "original_sources": [
                {"path": str(aux["raster_path"]), "sha256": data["provenance"]["raster_sha256"], "section": "band 1"},
                *[
                    {"path": str(path), "sha256": data["provenance"]["aoi_component_hashes"][suffix], "section": "unmodified AOI component"}
                    for suffix, path in aux["aoi_components"].items()
                ],
            ],
        },
        "data_checks": {
            "kind": "csv",
            "required_columns": ["class_code", "class", "label", "count", "fraction"],
            "labels": {"class": list(CLASS_ORDER), "label": [CLASS_LABELS[name] for name in CLASS_ORDER]},
            "row_count": len(CLASS_ORDER),
            "numeric_columns": {
                "class_code": {"min": 0, "max": 7},
                "count": {"min": 0},
                "fraction": {"min": 0, "max": 1},
            },
            "fingerprint_columns": ["class_code", "class", "label", "count", "fraction"],
            "numeric_total": {"columns": ["count"], "expected": data["valid_pixels"]},
        },
        "transformations": transformations,
        "plot": {
            "marks": ["categorical display-only image", "AOI outline", "class-count bars", "legend"],
            "title": title,
            "status_note": note,
            "required_status_text": ["Existing classified product", "not accuracy evidence", "not area evidence", "not ecological evidence"],
            "font_family": "DejaVu Sans",
            "palette": CLASS_COLORS,
            "axes": {
                "map_x": {"label": "X coordinate (source CRS)", "unit": "source CRS", "scale": "linear"},
                "map_y": {"label": "Y coordinate (source CRS)", "unit": "source CRS", "scale": "linear"},
                "composition_x": {"label": "Valid classified pixel count", "unit": "pixel", "scale": "linear", "zero_baseline_expected": True},
            },
            "legend": "codes 0-7 with class names and current AOI counts; 255 nodata",
            "uncertainty": "No independent thematic reference or uncertainty intervals are available; none fabricated.",
        },
        "outputs": {
            "png": {"path": str(paths["png"]), "min_dpi": 300, "min_width_px": 3600, "min_height_px": 2100},
            "vector": {"path": str(paths["svg"]), "format": "svg"},
        },
        "required_vector_text": ["Existing classified product", "not accuracy evidence", "not area evidence", "Tree"],
    }


def _plot_map(data: dict[str, Any], aux: dict[str, Any], paths: dict[str, Path]) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        from matplotlib.patches import Patch
    except ImportError as error:
        raise RuntimeError("matplotlib is required to plot classification maps") from error

    matplotlib.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none"})
    preview = aux["preview"]
    display = np.ma.masked_equal(preview, 254)
    # Preserve the source class codes as lookup indices.  A nine-colour map
    # stretched over 0..255 would collapse codes 0..7 into nearly one colour.
    colors = ["#000000"] * 256
    colors[: len(CLASS_COLORS)] = CLASS_COLORS
    colors[NODATA] = "#bfc1c3"
    cmap = ListedColormap(colors)
    fig, (map_axis, bars_axis) = plt.subplots(
        1, 2, figsize=(12, 8), dpi=300, gridspec_kw={"width_ratios": [1.55, 1]},
    )
    map_axis.imshow(
        display,
        cmap=cmap,
        vmin=-0.5,
        vmax=255.5,
        interpolation="nearest",
        extent=aux["preview_extent"],
        origin="upper",
    )
    geometry = aux["geometry"]
    for polygon in geometry.geoms:
        map_axis.plot(*polygon.exterior.xy, color="#363d44", linewidth=0.8)
        for interior in polygon.interiors:
            map_axis.plot(*interior.xy, color="#363d44", linewidth=0.6)
    map_axis.set_xlabel("X coordinate (source CRS)")
    map_axis.set_ylabel("Y coordinate (source CRS)")
    map_axis.set_title("A  Spatial class preview (every 12th original row/column)", loc="left", fontsize=12, pad=12)
    map_axis.grid(alpha=0.14)
    handles = [
        Patch(facecolor=CLASS_COLORS[index], label=f"{index} {CLASS_LABELS[name]} — {data['counts'][name]:,}")
        for index, name in enumerate(CLASS_ORDER)
    ]
    handles.append(Patch(facecolor="#bfc1c3", label="255 No valid class"))
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.055, 0.095), ncol=2, fontsize=9, frameon=False)

    values = np.array([data["counts"][name] for name in CLASS_ORDER], dtype=np.int64)
    bars = bars_axis.barh(np.arange(len(CLASS_ORDER)), values, color=CLASS_COLORS, edgecolor="#555555", linewidth=0.3)
    bars_axis.set_yticks(np.arange(len(CLASS_ORDER)), [f"{index} {CLASS_LABELS[name]}" for index, name in enumerate(CLASS_ORDER)])
    bars_axis.invert_yaxis()
    bars_axis.set_xlabel("Valid classified pixel count")
    bars_axis.set_title("B  Current AOI class counts", loc="left", fontsize=12, pad=12)
    bars_axis.bar_label(bars, labels=[f"{value:,}" for value in values], padding=3, fontsize=9)
    bars_axis.spines[["top", "right"]].set_visible(False)
    bars_axis.xaxis.grid(alpha=0.16)
    bars_axis.set_axisbelow(True)
    title_object = fig.suptitle(f"Existing classified product ({data['year']}) — AOI product description", x=0.055, ha="left", fontsize=17, y=0.97)
    note_object = fig.text(0.055, 0.055, "Display-only product description; not accuracy evidence, not area evidence, and not ecological evidence.", fontsize=9)
    fig.text(0.055, 0.032, "Fractions use valid codes 0-7 within original-grid AOI pixel centres; nodata=255 excluded from that denominator.", fontsize=9)
    fig.subplots_adjust(left=0.055, right=0.97, top=0.86, bottom=0.25, wspace=0.44)
    fig.savefig(paths["png"], dpi=300, facecolor="white", edgecolor="none")
    fig.savefig(paths["svg"], facecolor="white", edgecolor="none", metadata={"Date": None})
    plt.close(fig)

    # Retain the actual renderer observations needed by the render manifest.
    aux["render_observations"] = {
        "title": title_object.get_text(),
        "status_note": note_object.get_text(),
        "font_family": "DejaVu Sans",
        "palette": CLASS_COLORS,
        "axes": {
            "map_x": {"label": map_axis.get_xlabel(), "unit": "source CRS", "scale": map_axis.get_xscale(), "limits": list(map_axis.get_xlim())},
            "map_y": {"label": map_axis.get_ylabel(), "unit": "source CRS", "scale": map_axis.get_yscale(), "limits": list(map_axis.get_ylim())},
            "composition_x": {"label": bars_axis.get_xlabel(), "unit": "pixel", "scale": bars_axis.get_xscale(), "limits": list(bars_axis.get_xlim())},
        },
        "rendered_bar_values": [float(rect.get_width()) for rect in bars],
        "rendered_image_shape": list(np.asarray(display).shape),
        "renderer": {"name": "matplotlib", "version": matplotlib.__version__},
    }


def plot_classification_map(file_path: str, aoi_path: str, composition_path: str, year: int = 2025) -> dict:
    """Render a deterministic existing-product map after provenance checking."""

    try:
        _require_year(year)
        composition, composition_hash = _load_composition(composition_path)
        current, _preview, aux = _analyze(file_path, aoi_path)
        current["year"] = year
        _assert_composition_provenance(composition, composition_hash, current, year)
        output_dir = _output_directory()
        paths = {
            "png": output_dir / f"classification_map_{year}.png",
            "svg": output_dir / f"classification_map_{year}.svg",
            "table": output_dir / f"classification_map_{year}.plot_data.csv",
            "contract": output_dir / f"classification_map_{year}.figure_contract.json",
            "manifest": output_dir / f"classification_map_{year}.render_manifest.json",
        }
        collisions = [str(path) for path in paths.values() if path.exists()]
        if collisions:
            raise FileExistsError("Refusing to overwrite existing output(s): " + ", ".join(collisions))
        columns, rows = _write_plot_table(paths["table"], current)
        aux["table_columns"] = columns
        aux["table_rows"] = rows
        aux["table_sha256"] = _sha256(paths["table"])
        contract = _figure_contract(current, aux, paths)
        _write_json_exclusive(paths["contract"], contract)
        _plot_map(current, aux, paths)
        try:
            from PIL import Image
            with Image.open(paths["png"]) as image:
                png_info = {"width_px": image.width, "height_px": image.height, "dpi": list(image.info.get("dpi", ())) }
        except ImportError as error:
            raise RuntimeError("Pillow is required to verify the rendered PNG") from error
        observations = aux["render_observations"]
        manifest = {
            "figure_id": contract["figure_id"],
            "research_status": contract["research_status"],
            "source_data_sha256": aux["table_sha256"],
            "source_aoi_component_hashes": current["provenance"]["aoi_component_hashes"],
            "composition_sha256": composition_hash,
            "numeric_fingerprint": _canonical_table_fingerprint(rows, columns),
            "data_shape": [len(rows), len(columns)],
            "transformations": contract["transformations"],
            "renderer": observations["renderer"],
            "plot": {
                "title": observations["title"],
                "status_note": observations["status_note"],
                "font_family": observations["font_family"],
                "palette": observations["palette"],
                "axes": observations["axes"],
                "uncertainty": contract["plot"]["uncertainty"],
            },
            "rendered_bar_values": observations["rendered_bar_values"],
            "rendered_image_shape": observations["rendered_image_shape"],
            "outputs": {
                "png": {"path": str(paths["png"]), "sha256": _sha256(paths["png"]), **png_info},
                "vector": {"path": str(paths["svg"]), "format": "svg", "sha256": _sha256(paths["svg"])},
            },
        }
        _write_json_exclusive(paths["manifest"], manifest)
        data = {
            "output_path": str(paths["png"]),
            "secondary_outputs": [{"path": str(paths["svg"]), "kind": "svg"}],
            "year": year,
            "class_order": list(CLASS_ORDER),
            "counts": current["counts"],
            "valid_pixels": current["valid_pixels"],
            "nodata_pixels": current["nodata_pixels"],
            "aoi_pixel_centres": current["aoi_pixel_centres"],
            "scope": current["scope"],
            "provenance": {
                "raster_sha256": current["provenance"]["raster_sha256"],
                "aoi_component_hashes": current["provenance"]["aoi_component_hashes"],
                "composition_path": str(Path(composition_path).resolve()),
                "composition_sha256": composition_hash,
                "figure_contract_path": str(paths["contract"]),
                "render_manifest_path": str(paths["manifest"]),
            },
        }
        return {"success": True, "message": "Classification product map saved.", "data": data}
    except FileExistsError as error:
        return _safe_failure(error, map_context=True)
    except (FileNotFoundError, RuntimeError, ValueError, AssertionError, OSError) as error:
        return _safe_failure(error, map_context=True)
    except Exception as error:
        return _safe_failure(error, map_context=True)


__all__ = ["summarize_classification", "plot_classification_map"]
