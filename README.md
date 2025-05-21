# User-centric Remote Sensing Analysis (URSA) based on Large Language Models

> Towards the Future of Remote Sensing Analysis with state-of-the-art AI technology.

---

## 🗞️ News
- **May 20, 2025** — Our paper entitled [Achieving user-centric remote sensing analysis through an LLM-based multi-agent system](https://github.com/zhelunSun/URSA) is under review
- **Nov 30, 2024** — Our early work was presented at [The 1st International Workshop on Remote Sensing Intelligent Mapping (RSIM)](https://www.geog-event.hku.hk/rsim)

---

## ✨ Highlights

Remote sensing analysis transforms remotely sensed data into actionable information across various domains. Nonetheless, conventional data-centric methodologies establish barriers between remote sensing data and downstream users possessing limited expertise in the field. *User-Centric Remote Sensing Analysis (URSA)* framework aims to explore a new paradigm of remote sensing analysis leveraging state-of-the-art Large Language Models (LLMs). It enables human users to directly express their needs in natural language without technical barriers, while LLM-powered AI agents can understand the needs and perform according RS analysis pipeline fully automatically and return interpretable results.
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


