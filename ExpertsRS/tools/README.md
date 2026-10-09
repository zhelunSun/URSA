# ExpertsRS Tools

This folder contains local remote sensing functions and their registry. The
historical notebook consumes the generated function-call schemas. The active
`ExpertsRSSystem` instead accepts role decisions and plan nodes, binds tool
arguments itself, and exposes an explicitly supported subset of the functions.

| Module | Purpose |
|---|---|
| `io_kit.py` | Raster discovery, metadata reading, band reading, and raster saving |
| `index_kit.py` | Spectral index calculation, including NDVI, EVI, NDWI, NBR, LST, and MSAVI |
| `analysis_kit.py` | Thresholding, area calculation, masking, and zonal statistics |
| `viz_kit.py` | Index maps, thematic maps, and false-color composites |
| `registry.py` | Tool registration helpers for Python callables and OpenAI-style tool schemas |

The legacy library has 18 registered functions: 5 I/O, 6 spectral/thermal,
4 analysis, and 3 visualization tools. Registration alone does not admit a tool
to the active runtime. Its legacy bindings currently expose metadata, NDVI,
index plotting, thresholding, thematic plotting, and area calculation. The
`classification-v1` registry adds `summarize_classification` and
`plot_classification_map`; that runtime profile exposes those two product tools.

Public entry points are exported from `__init__.py`:

```python
from tools import get_all_tools, get_tool_schemas, list_tools, print_tool_catalog
```

Spectral tools use semantic band names such as `B4` and `B8` by default and
resolve them against exact raster band descriptions. Numeric inputs remain
available only as explicit 1-based raster stack positions; a physical band
number must never be assumed to equal its position in a stacked GeoTIFF.

Scientific preconditions are fail-closed: missing semantic metadata, absent
required bands, misaligned rasters, geographic-CRS area inference without an
explicit pixel area, and unsupported sensor/unit combinations return structured
failures instead of guessed results. Nodata pixels remain outside thematic
classes and area/statistical summaries report valid and nodata counts.

`calculate_lst` is deliberately narrow: it accepts declared Landsat-8 B10 TOA
radiance (`toa_radiance_w_m2_sr_um`) and does not derive temperature from
Sentinel-2 optical stacks.

## Model-facing schema contract

Python defaults and model-required inputs have different purposes. Model
schemas require deliberate raster selection even when a Python function keeps
`file_path=None` for compatibility. Model calls to `save_raster` also require a
reference raster, and LST calls require explicit sensor and radiometric units.
Algorithm defaults such as NDVI's B8/B4 bands remain optional.

The schema builder combines signatures and type hints with explicit input
requirements and parameter descriptions extracted from Google-style `Args`.
It supports grouped/multiline descriptions, typed lists, nullable defaults,
semantic band names or verified stack indices, and numeric raster arrays.
Unknown parameter descriptions or unsupported annotations fail construction
instead of silently becoming generic strings. Non-JSON defaults such as NaN
are explained without serializing invalid JSON; undeclared arguments are
excluded by `additionalProperties: false`.

These schemas are input contracts, not filesystem permissions, provider strict
mode, or execution-time validators. Direct Python/function-map calls still use
the underlying Python defaults. The caller must validate arguments before
execution and enforce its own resource and output boundaries. Generating a
schema does not admit a tool to `ExpertsRSSystem`, which has separate workflow
contracts, bindings, and execution checks.

When adding or changing a tool, keep its callable, registry entry, parameter
semantics, workflow operator contract, and effect classification consistent.
Runtime admission additionally needs an argument resolver, artifact handling,
and tests for its execution boundaries. `get_tool_schemas()` currently exports
the legacy library; classification tool contracts have a separate adapter.

## Schema correction checkpoint 2026-10-09

The correction separates model-required inputs from convenience defaults,
removes full docstrings from tool summaries, restores informative parameter
descriptions, fixes typed collections and array inputs, and rejects unknown
fields. It changes no remote sensing algorithm, runtime scheduler, or historic
experiment result.

Validation at this checkpoint: 173 offline tests passed, including 19 new
schema tests, with 31 Rasterio deprecation warnings. Tests validate generated
schemas and positive/negative arguments with the development-only `jsonschema`
dependency, preserve direct Python defaults, and run a synthetic NDVI example
with an expected pixel value. No live model requests were made. Run the focused
checks with `python -m pytest ExpertsRS/test_tool_schemas.py -q` after installing
the project's development dependencies.

This checkpoint does not resolve the separately identified runtime delivery,
input-permission, cross-instance resume, or hard-timeout gaps, and does not
establish that every registered tool is scientifically validated.
