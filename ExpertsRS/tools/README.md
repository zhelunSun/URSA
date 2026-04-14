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

Band indices are 1-based to match rasterio and physical band numbering conventions.
