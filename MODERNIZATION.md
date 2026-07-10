# Ch1 Modernization Plan — 从 AutoGen StateFlow 到现代化架构

> 参考: EurekAgent (arXiv:2606.13662, THU-Team-Eureka, 2026-06)
> 状态: 计划中 | 优先级: CH1-P1 | 不阻塞当前实验
> **本文件提供背景信息和参考方向，具体实现方案由接手 Agent 自行判断。**

## 当前架构（2024）

```
AutoGen GroupChat + 手写 speaker_selection + 17 遥感 tools
Agents: User → Manager → Scientist → Engineer → Executor
States: Clarify → Define → Solve → Report (via if-else routing)
Tool reg: function_map + OpenAI function_call schemas
```

## 参考：EurekAgent 的现代化做法

EurekAgent 采用了以下技术栈（与 Ch1 形成对比）：
- **LangGraph 显式状态图**: TypedDict state + 声明式 graph edges（[state.py](https://github.com/THU-Team-Eureka/EurekAgent/blob/main/src/state.py) + [graph.py](https://github.com/THU-Team-Eureka/EurekAgent/blob/main/src/graph.py)）
- **Docker 双容器隔离**: Agent 容器 + Grader 容器，文件系统层级隔离（论文 §3.1）
- **Git 制品追溯**: `artifacts.py`，每轮实验自动 commit（[artifacts.py](https://github.com/THU-Team-Eureka/EurekAgent/blob/main/src/artifacts.py)）
- **双轴预算控制**: wall-clock + token cost（论文 §3.3）
- **状态持久化**: crash 后从上次 state 恢复（论文 §3.3 resumability）

## 可参考的改进方向（供 Agent 评估）

以下方向来源于 EurekAgent 与 Ch1 的对比观察，**是否采纳、如何实现由 Agent 判断**：

### 方向 1: 显式 State

**观察**: EurekAgent 用 TypedDict + 序列化来管理状态，Ch1 用对话历史隐式推导。
**参考**: 可以在 `ExpertsRS/` 下增加一个 `state.py`，用 dataclass 显式定义工作流状态，同时保留现有 `speaker_selection` 以确保 notebook 兼容。
**位置**: `ch1-agent-workflow/ExpertsRS/`

### 方向 2: 基础元工具拆分

**观察**: EurekAgent 的 Agent 通过 CLI 直接调用 bash/read/write 等原子操作。
**参考**: 你已有 17 个遥感工具 + MCP。是否拆出 grep/write/read 等原子工具，对齐 `sheaf-ai/internal/MCP-V2-PLAN.md`。
**位置**: 可能涉及 `sheaf-ai/` 和 `ch1-agent-workflow/` 两个 repo

### 方向 3: Git 制品追溯

**观察**: EurekAgent 每轮实验自动 git commit results/ 目录。
**参考**: 可以在 Ch1 的 Executor 完成后加一个 hook 自动 commit。改动量小（~20 行）。
**位置**: `ch1-agent-workflow/ExpertsRS/` notebook 或新脚本

### 方向 4: Token 成本追踪

**观察**: EurekAgent 追踪每次运行的 wall-clock 和 API cost。
**参考**: 在 Agent chat 回调中累计 token 用量，写入 state。
**位置**: `ch1-agent-workflow/ExpertsRS/`

### 方向 5: 评估隔离（远期）

**观察**: EurekAgent 用 Docker 双容器隔离评估器和 Agent，防止作弊。
**参考**: Ch1 是否需要取决于实验设计要求。论文实验阶段可考虑。

---

## 叙事层面参考（非技术方向）

### 参考叙事 1: 递进分阶段论证

2026-06-12 元宝对话中提出"先 MVP 知识环境 → 回喂 Agent 升级"的分阶段叙事。此思路的非正式版本出现在该对话中；学术对应见于 KnowAgent (Zhu et al. 2025, Action KB) 的 "knowledge-infused decision pipeline" 和 EurekAgent (2026) 的 "environment-first" 范式。

**注意**: 元宝对话中具体提出的 K₁-K₅ 维度（本体层/数据目录/工具语义/规则先验/证据溯源）是 LLM 即兴框架，**不具有文献支撑**，不可作为论文框架使用。可参考的只有"分阶段论证"这一叙事结构。

### 参考叙事 2: 叙事倒置

元宝和卡兹克分享中均出现了"把叙事倒过来讲"的技巧：
- 元宝建议将"我们整理了很多知识"倒置为"我们把领域约束变成了 Agent 的第一类公民"
- 卡兹克将贬义词"眼高手低"重定义为正面能力

学术论文中，此技巧可用于 Introduction 的 hook 句和 Discussion 的贡献阐述，但不宜作为方法论的主叙事。
**学术对应**: EurekAgent 论文本身也有类似操作——"瓶颈不是 workflow，是 environment"。

---

> Updated: 2026-06-13 | 新增叙事层面参考（非技术方向，仅供 Narrative 启发）

---

## Claude Code 接手时的建议

- 先读 `ExpertsRS/` 下的 notebook 和 tools/，理解现有架构
- 方向 1+3 改动量最小（~150 行），可作为起步
- 方向 2 对齐 `sheaf-ai/internal/MCP-V2-PLAN.md`
- 所有改进在独立分支进行，确保 `ExpertsRS_notebook.ipynb` 保持可运行
- **本文件的建议不是指令**——结合代码实际状态自行判断优先级和实现方式

---

> Updated: 2026-06-12 | Refs: EurekAgent (arXiv:2606.13662), MCP-V2-PLAN.md, ch1-research.md
