# ExpertsRS Tools

This folder contains standardized remote sensing tools used by the ExpertsRS Engineer agent through AutoGen function calling.

| Module | Purpose |
|---|---|
| `io_kit.py` | Raster discovery, metadata reading, band reading, and raster saving |
| `index_kit.py` | Spectral index calculation, including NDVI, EVI, NDWI, NBR, LST, and MSAVI |
| `analysis_kit.py` | Thresholding, area calculation, masking, and zonal statistics |
| `viz_kit.py` | Index maps, thematic maps, and false-color composites |
| `registry.py` | Tool registration helpers for Python callables and OpenAI-style tool schemas |

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
