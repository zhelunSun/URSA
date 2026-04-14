# User-centric Remote Sensing Analysis (URSA) based on Large Language Models

> Towards the Future of Remote Sensing Analysis with state-of-the-art AI technology.

---

## 🗞️ News
- **Jan 08, 2026** — Our paper [An LLM-based multi-agent system for remote sensing analysis](https://www.tandfonline.com/doi/full/10.1080/20964471.2025.2600178) was published online in *Big Earth Data*.
- **May 20, 2025** — Our paper was submitted for review.
- **Nov 30, 2024** — Our early work was presented at [The 1st International Workshop on Remote Sensing Intelligent Mapping (RSIM)](https://www.geog-event.hku.hk/rsim)

---

## ✨ Highlights

Remote sensing analysis transforms remotely sensed data into actionable information across various domains. Nonetheless, conventional data-centric methodologies establish barriers between remote sensing data and downstream users possessing limited expertise in the field. *User-Centric Remote Sensing Analysis (URSA)* framework aims to explore new possibilities of remote sensing analysis leveraging state-of-the-art Large Language Models (LLMs). It enables human users to directly express their needs in natural language without technical barriers, while LLM-powered AI agents can understand the needs and perform according RS analysis pipeline fully automatically and return interpretable results.
![URSA main](/assets/img/1Paradgim_trans_00.jpg "Conceptual Graph")
URSA paves the way towards more accessible, interactive, and intelligent remote sensing analysis in the future.

## 🚀 Prototype: ExpertsRS

As an initial demonstration of the URSA framework, we developed **ExpertsRS** — a prototype system that showcases how user-centric remote sensing analysis can be enabled through a Large Language Model (LLM)-powered multi-agent system.

ExpertsRS is built based on [AutoGen](https://github.com/microsoft/autogen), and implements a flexible workflow where multiple AI agents interact to support users in remote sensing analysis tasks.

**Highlights of ExpertsRS:**
- The system effectively guides users to interact using **natural language**, enabling them to express their needs **without technical barriers**.
- The system possesses the capability to **autonomously select and process** pertinent remote sensing data, thereby ensuring **efficient and context-specific analysis**.
- The system's outputs were consistent with those produced by a human expert. Furthermore, by leveraging LLMs' knowledge retrieval and inference capabilities, the system could interpret results and provide additional contextual information, rendering the **outputs easy to interpret and valuable for decision-making**.
  
**You can check out the full implementation in: [`./ExpertsRS`](./ExpertsRS)**

---

## Version Notes

This repository will continue to maintain and improve the public ExpertsRS prototype.

- **v0.2 - Tool-augmented update:** adds standardized remote sensing tools for the Engineer agent, environment-based LLM configuration, dynamic GeoTIFF discovery from `ExpertsRS/data/`, structured outputs under `ExpertsRS/results/`, and tool validation tests.
- **v0.1 - Paper prototype:** initial public prototype accompanying the paper.

### Tool Modules

ExpertsRS currently includes four tool kits:

| Module | Tools |
|---|---|
| `io_kit` | `list_available_data_files`, `read_raster_metadata`, `read_raster_band`, `read_raster_bands`, `save_raster` |
| `index_kit` | `calculate_ndvi`, `calculate_evi`, `calculate_ndwi`, `calculate_nbr`, `calculate_lst`, `calculate_msavi` |
| `analysis_kit` | `apply_threshold`, `calculate_area`, `apply_mask`, `zonal_statistics` |
| `viz_kit` | `plot_index_map`, `plot_thematic_map`, `plot_false_color_composite` |

---

## 📄 Citation

If you use URSA or ExpertsRS in your work, please cite:

> Sun, Z., Zhou, Y., & Yang, J. (2026). An LLM-based multi-agent system for remote sensing analysis. *Big Earth Data*. https://doi.org/10.1080/20964471.2025.2600178

