# URSA Upgrade Progress

> Project: LLM-based User-Centric Remote Sensing Analysis System
> Repo: `https://github.com/zhelunSun/URSA`
> Local path: `c:\Users\zhelunStation\WorkBuddy\Claw\URSA`

---

## Phase 0 - Engineering Fixes ✅ Completed

| # | Item | Change |
|---|------|--------|
| 0.1 | API key security | New `.env.example`, `.gitignore`, `llm_config_list.py`; old JSON → `.json.template` |
| 0.2 | Remove hardcoded data paths | Engineer prompt now dynamically discovers data files |
| 0.3 | results/ directory creation | Notebook init cell: `os.makedirs(exist_ok=True)` |
| 0.4 | Dependency manifest | New `requirements.txt` |

---

## Phase 1 - Tool Module ✅ Completed (2026.04.14)

Refactors the Engineer agent from "freeform Python code generation" to "calling standardized remote sensing tools".

### Implemented Tool Kits

```
tools/
├── __init__.py       # Unified exports: get_all_tools, get_tool_schemas
├── io_kit.py         # ✅ Raster I/O, metadata query, band extraction
├── index_kit.py      # ✅ NDVI, EVI, NDWI, LST, NBR, MSAVI
├── analysis_kit.py   # ✅ Threshold segmentation, area stats, mask, zonal stats
├── viz_kit.py        # ✅ Thematic map, index heatmap, false color composite
└── registry.py       # ✅ AutoGen function_map + tool schema registration
```

**18 tool functions total**, all registered to the Engineer agent via `function_map`.

### Notebook Changes
- New cell: tool loading (`from tools import ...`)
- Engineer agent: `function_map=function_map` + `tools=tool_schemas`
- StateFlow annotations updated

### Engineer Prompt Changes
- From "write Python code freely" → "prefer tool calls, write only glue code"
- New tool catalog with descriptions and parameters for each tool
- Error handling: check `success` field
- Band convention: 1-based (Band 4 = index 4, not 3)

---

## Phase 2 - Data Module (GEE) 📋 Planned

New `data/gee_client.py`: automatically fetch satellite data from GEE based on user-specified time range and location.

---

## Phase 3 - Workflow Enhancements 📋 Planned

- Enhanced error auto-retry
- Multi-task template library
- User history memory

---

## Current File Structure

```
URSA/
├── .gitignore                    ✨ Phase 0
├── requirements.txt              ✨ Phase 0
├── ExpertsRS/
│   ├── .env.example              ✨ Phase 0
│   ├── llm_config_list.py        ✨ Phase 0
│   ├── llm_config_list.json.template  ✨ Phase 0
│   ├── prompts.py                ✨ Phase 0 + 1
│   ├── ExpertsRS_notebook.ipynb  ✨ Phase 0 + 1
│   ├── test_tools.py             ✨ Phase 1
│   ├── data/
│   └── tools/                    ✨ Phase 1
│       ├── __init__.py
│       ├── io_kit.py
│       ├── index_kit.py
│       ├── analysis_kit.py
│       ├── viz_kit.py
│       └── registry.py
└── assets/
```

---

## Full Change Summary

### Phase 0 - Engineering Fixes ✅

| File | Change |
|------|--------|
| `ExpertsRS/llm_config_list.py` | New: load API key from `.env` |
| `ExpertsRS/.env.example` | New: user setup guide |
| `ExpertsRS/llm_config_list.json` → `.json.template` | Renamed: kept as template reference |
| `.gitignore` | New: excludes `.env`, `results/`, `__pycache__/` |
| `requirements.txt` | New: dependency manifest |
| `prompts.py` | Dynamic data path discovery, remove hardcoded filenames |
| `ExpertsRS_notebook.ipynb` | Config loading refactor, results/ directory creation |

### Phase 1 - Tool Module ✅

| File | Change |
|------|--------|
| `tools/__init__.py` | Unified exports |
| `tools/io_kit.py` | 5 tools: list data, read metadata, read single/multiband, save raster |
| `tools/index_kit.py` | 6 tools: NDVI, EVI, NDWI, NBR, LST, MSAVI |
| `tools/analysis_kit.py` | 4 tools: threshold, area stats, mask, zonal stats |
| `tools/viz_kit.py` | 3 tools: index heatmap, thematic map, false color composite |
| `tools/registry.py` | AutoGen function_map + OpenAI function_call schema registration |
| `prompts.py` | Engineer prompt fully refactored, tool-first |
| `ExpertsRS_notebook.ipynb` | New tool loading cell, Engineer registers function_map |
| `test_tools.py` | Tool module validation (12/12 pass) |
