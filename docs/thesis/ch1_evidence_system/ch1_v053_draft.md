# 第一章写作骨架（URSA Harness v0.5.3）

> 用途：大论文提纲、开题报告和后续章节正文的共同骨架。事实以 `v053_evidence_index.md`、
> `v053_results_table.md`、`claim_registry.md` 和冻结运行工件为准；这里不单独晋级 claim。

## 章节暂定题目

**基于多智能体的城市森林遥感工作流构建**

节级方法表述可使用：

> 面向开放用户需求的遥感工作流可靠形成与运行

工程副标题可用于 PPT/面试：

> From a conversation-oriented prototype to URSA Harness: a domain-specific,
> evidence-first agent runtime for remote-sensing workflows.

## 问题层级与一句话科学问题

第一章必须区分三个层级，不能把方法机制倒置为领域出发点：

1. **论文与 URSA 的领域出发点**：现有遥感能力长期围绕数据获取、方法开发和产品生产持续增强。
   生态学家、
   城市规划人员和政策制定者虽然频繁需要遥感信息，却未必具备数据发现、算法选择、软件操作和
   结果解释所需的遥感与计算背景。User-centric Remote Sensing Analysis 的根本目标，是让用户从
   实际问题出发，而不是先学习完整的遥感处理链；
2. **第一章的科学问题**：面向非遥感专业用户提出的开放式城市森林分析需求，如何构建能够保持
   用户意图、组织专业数据与工具并根据运行反馈可靠完成任务的多智能体遥感工作流？
3. **本轮升级的技术问题**：如何用结构化计划、运行约束、真实 observation、局部重新授权、
   checkpoint、过程证据和交付检查，使上述“可靠完成”成为可执行、可观察和可评测的系统性质？

因此正文优先使用上位词 **工作流可靠性**，并把它操作化为四个可检查维度：

- **需求保持性**：原始用户要求不会在规划或报告中被遗漏、替换或降级；
- **执行有效性**：依赖、类型、工具、权限和必需输出满足约束后才进入真实执行；
- **反馈适应性**：失败事实被保留，后续路径由有责任的角色调整，并能复用仍然有效的中间产物；
- **结果可核验性**：最终状态和自然语言报告能够回溯到真实动作、产物和限定口径。

“稳定性”暂不作为总术语，因为它通常需要更大规模重复实验来证明运行方差和一致性；“可靠性”
更适合统摄当前机制，并可由上述四个维度分别定义和验证。

## 章节主张与边界

本章研究对象不是通用 Agent 平台、Agent 数量或工作流图本身，而是面向用户需求的工作流可靠性，
以及支撑它的三个相互连接的机制：

1. **可调整的分层规划**：Scientist 提交类型化 planned workflow，真实 observation 触发有来源的
   局部修订；
2. **随执行更新的过程图**：系统区分 planned graph 与从 trace 重建的 observed graph，保留计划、
   动作、失败、产出和责任归属；
3. **基于检查点的局部恢复**：失败后复用已验证 artifact，并要求 Scientist 对受影响分支重新授权。

v0.5.3 已证明这些对象能在统一真实模型 runtime 中运行并形成协议闭合，但 task-11 的 graph diff 是
`local_reauthorization_only`。本章不能据此声称规划优越性、checkpoint 独立效应、主题精度、行政区
覆盖率或跨任务泛化。

---

## 1. Introduction

### 1.1 领域背景：遥感能力丰富与下游使用门槛并存

- 城市森林监测、规划与政策制定越来越依赖遥感数据，但目标用户通常从生态、规划或治理问题出发，
  并不以遥感建模、编程和地理数据处理为主要技能；
- 遥感领域已经形成丰富的数据、算法和产品，实际应用仍需经历数据发现、预处理、方法选择、参数
  配置、软件操作、质量控制和结果解释等专业流程；
- 因此，“数据或产品已经存在”并不等于“用户的问题已经得到支持”。数据供给与下游问题之间仍有
  明显的知识、工具和交互门槛。

### 1.2 范式动机：从数据与产品供给到面向用户需求

- 已发表 URSA 直接指出 data-centric 方法在遥感数据与专业能力有限的下游用户之间形成门槛；更
  稳妥的扩展表述是：数据、方法或标准产品的可获得，并不自动转化为对具体生态、规划和治理问题的
  可用支持；
- User-centric RS Analysis 把起点改为用户需求：用户用自然语言描述实际问题，智能系统协调知识、
  数据、算法和工具，返回地图、表格、图形和文字解释；
- 该范式不是否定数据与产品，而是重新组织它们与用户问题之间的关系，使遥感能力能够被非遥感
  专业用户更直接地调用。

此处应复用已发表 URSA 的范式转换图和框架图，并把它们明确标为既有研究基础，而不是 v0.5.3
新增贡献。

术语统一为 **URSA = User-centric Remote Sensing Analysis**。当前仓库、已发表论文信息和早期提交
均使用 URSA，未找到 EORSA 的可追溯定义；除非后续发现原始来源，正式材料不引入 EORSA。

### 1.3 从既有可行性到本章研究缺口

已发表 URSA/ExpertsRS 以自然语言连接用户需求与 Manager–Scientist–Engineer，并通过案例和轻量
任务测试证明了面向用户自动分析的初步可行性。但该原型主要依赖角色提示词、对话历史和隐式
StateFlow，适合回答“这种交互与自动分析是否可行”，尚不足以回答“开放需求能否被可靠地形成、
执行和交付为一条可检查的工作流”。围绕一次多步遥感任务，存在四类可检验缺口：

1. 用户要求可能在任务定义、计划或报告中被遗漏，系统内部自报的目标不能独立代表原始需求；
2. 计划是自然语言，不能确定性检查依赖、类型、工具和必需输出；
3. 模型计划与真实动作可能漂移，工具失败后的重试、改道和复用也缺少稳定责任归属；
4. 最终成功可能覆盖早期失败，报告还可能引用虚构 artifact 或扩大科学口径。

### 1.4 科学问题与研究问题

- **RQ1 — 需求保持与工作流形成**：开放用户需求能否被转化为具有明确目标、依赖、工具和交付义务
  的结构化工作流，并阻止需求遗漏或非法计划进入执行？
- **RQ2 — 运行反馈与故障处置**：真实工具反馈能否约束后续动作，使失败触发有责任归属的局部调整，
  同时复用仍然有效的中间产物？
- **RQ3 — 结果闭合与过程核验**：用户要求、计划、动作、产物、终态和报告能否形成一致证据链，
  并在交付不足时正确澄清或停止，而不是产生 false-success？

当前 5×3 是 RQ1–RQ3 的初步机制与集成证据，不是“自适应规划总体优于静态规划”的正式效果实验。

### 1.5 贡献表述

建议用三层贡献，避免把工程组件直接包装成科学创新：

1. **工作流可靠性表示**：建立原始需求义务、planned workflow、observed process 与最终交付之间的
   统一关系，使用户要求、未来计划、已发生事实和结果证据分别具有明确语义；
2. **领域运行时**：实现 plan-bound execution、observation-triggered Scientist revision、运行内
   checkpoint 和 EO-specific fail-closed contracts；
3. **证据协议**：将正确完成、正确停止、澄清、false-success、图对齐和报告证据纳入独立 evaluator，
   形成可复核 episode package。

### 1.6 章节结构

简要介绍 Related Work、Method、Experiment、Results、Discussion 和 Conclusion 的关系。

---

## 2. Related Work and Conceptual Positioning

相关工作不按框架名称堆砌，围绕本章缺口组织为四条线。

### 2.1 面向用户的遥感与地理空间智能体

- 已发表 URSA/ExpertsRS：自然语言需求、三角色、多工具和可解释结果；
- Spatial-Agent、constraint-aware geospatial workflow 等：可执行 DAG、空间/功能约束和工作流组合；
- ThinkGeo、GeoAgentBench、GISAgentBench 等：工具增强、多步空间任务和 trajectory/final outcome 评测。

定位：工作流图、工具调用和多智能体本身已有充分先例；URSA 的差异必须落在真实 observation 后的
计划约束、局部恢复和证据闭合，而不是“首次使用 graph/agent”。

### 2.2 规划、工具反馈与恢复

- ReAct：reasoning/action/observation 循环；
- Reflexion、LATS、DS-STAR 等：反馈、反思、搜索或迭代改进；
- 工作流/checkpoint 系统：持久状态、恢复与局部重算。

定位：本章不声称发明反馈或 checkpoint；关注这些机制如何在 EO typed contracts、角色责任和报告
证据约束下组合。

### 2.3 Agent Harness 与运行控制

- 现代 Harness 将模型之外的 context、tools、state、permissions、sandbox、observability 和
  intervention 视为共同研究对象；
- DeepSeek Harness/Cordis 展示 capability-as-plugin、append-only session log 和 profile composition；
- URSA 采用 bounded plugin architecture：稳定 domain kernel + 可替换 capability ports，而不是整体
  迁移通用 Harness。

定位：Harness 文献用于解释为什么模型能力不能等同系统能力，不承担 URSA 方法 novelty。DeepSeek
Harness 仍是 developer preview，应作为 SOTA 工程参照而非实验 baseline。

### 2.4 Agent 评测、provenance 与安全终态

- 只看最终答案会遗漏中途越权、错误工具、失败覆盖和信息泄漏；
- trajectory、artifact provenance、正确停止和成本需要分别报告；
- evaluator gold 与 fault ledger 必须隔离在系统外。

### 2.5 本章位置小结

用一段话明确：URSA 的根是面向用户的遥感分析，而不是 Harness 本身；本章借鉴现代 Harness 的
控制思想，把已发表原型推进为能够检查需求保持、执行有效、反馈适应和结果证据的领域工作流。

---

## 3. Method and System Design

### 3.1 问题形式化

定义最小对象：原始请求与 `DeliveryObligation`、`TaskSpec`、artifact/operator contract、
`WorkflowGraph`、plan version、node eligibility、action、observation、checkpoint、terminal status 和
structured deliverable。

### 3.2 总体系统架构

调用 `CH1-FIG-01`：Data–Tools–Brain 与共享 runtime/evidence 外壳。强调 runtime 不是第四个 Agent，
independent evaluator 位于系统之外，AutoGen 是 model-facing adapter 而非领域控制面。

### 3.3 多智能体责任与控制权

调用 `CH1-FIG-02`：Manager 负责澄清和报告；Scientist 负责完整计划与 revision；Engineer 只选择
eligible `node_id`；Executor/runtime 绑定输入、参数和权限并执行真实 effect。ProfiledUserAgent 是隔离
测试夹具，不是常驻第四角色。

### 3.4 规划—执行—反馈—恢复闭环

调用 `CH1-FIG-03`，依次解释：请求义务、path-free planned graph、fail-closed validator、eligible-node、
bound action、真实 observation、`revision_required`、Scientist revision、trace/observed graph 和报告闭合。

### 3.5 Planned graph 与 observed graph

- planned graph 面向未来并约束可执行节点；
- observed graph 面向已发生事实，由 trace 确定性重建；
- plan/action/observation/artifact/checkpoint 有稳定引用和 actor attribution；
- graph diff 分类不自动推出规划质量改善。

### 3.6 局部恢复与 checkpoint

- checkpoint 是已验证 artifact 的逻辑恢复引用；
- 不重新计算 unaffected artifacts；
- 不承诺撤销外部副作用或进程崩溃后的 durable recovery；
- task-11 只覆盖一次注入 threshold failure。

### 3.7 交付义务与诚实报告

- runtime 从原始请求独立提取 obligation；
- Scientist 可以补充但不能删改；
- Manager deliverables 必须引用真实 artifact/observation；
- task-11 区分 NDVI map 与 vegetation coverage thematic map；
- 无独立行政区分母时只允许“有效影像像元范围内”的比例。

### 3.8 实现与安全边界

- Python 3.10+、Pydantic 2、AutoGen AgentChat 0.7.5、rasterio/numpy/matplotlib；
- 六个 Agent-visible safe tool bindings，18 个注册工具作为更广工程资产；
- local path/effect permission、预算、provider gate、trace privacy；
- 当前是应用层权限围栏，不是进程级 sandbox；
- 后续采用 stable kernel + DecisionProvider/ExecutionBackend/EventStore 等显式 ports。

---

## 4. Experiment and Evaluation Protocol

### 4.1 证据层级

分开报告 published prior、engineering support、diagnostic/live integration evidence 和 formal effect evidence。

### 4.2 工程验收

主环境与 clean virtual environment、121 项回归、compile、CLI NDVI、privacy/leakage、diff check、
scripted 15-slot acceptance 和 checksum manifest。

### 4.3 v2 5×3 matched pilot

五类任务：普通 NDVI、缺失 NDSI 工具、Sentinel-2 不满足 LST B10 前置条件、task-11 threshold 故障/
恢复、task-13 模糊需求澄清。三条件的精确定义沿冻结 panel；模型、temperature、retry、预算、数据、
工具和 evaluator 固定，gold/fault/private contract 不进入 Agent 输入。

### 4.4 指标

- v2 evaluator closure 与 terminal status；
- false-success、plan/action/node/graph consistency；
- revision trigger、actor attribution、checkpoint/reused artifact；
- obligation—artifact—deliverable—report closure；
- token、wall time、tool/model turns 和 privacy leakage。

### 4.5 隔离 UserAgent smoke

task-13 matched pilot 保持 `needs_clarification`；rule/live ProfiledUserAgent 只在独立 smoke 中回答一次并
调用 `.resume()`，不混入 15-slot，也不解释为用户研究。

---

## 5. Results

### 5.1 工程验收结果

主环境 121/121，clean-venv 121/121；compile、CLI、privacy、scripted 15-slot 全部通过；acceptance
manifest 和证据 SHA-256 已保存。

### 5.2 最终 5×3

- v2 evaluator closure：15/15；
- terminal status：5 completed、7 controlled-stop、3 needs-clarification；
- token：215,500；wall time：391.582 s。

重点解释：15/15 不是“15 项都成功完成”，而是每个槽到达了与能力和证据相符的诚实终态。

### 5.3 task-11 恢复案例

- B1：failure 后 controlled stop；
- B2/B3：复用 NDVI，Scientist 引用 observation 重新授权 threshold 后续分支；
- B3 保存 checkpoint 引用；
- 专题图与两项独立 deliverable 均闭合；
- graph diff 为 `local_reauthorization_only`。

### 5.4 澄清与报告

matched task-13 三槽均保持 needs-clarification；独立 rule/live UserAgent smoke 均经 `.resume()`
completed。它只证明接口闭环，不构成用户效用证据。

### 5.5 失败运行的价值

保留早期 14/15、13/15 provider duplicate-JSON 运行；结合更早 band/nodata 审计，形成“发现—降级—
修复—有限晋级”的科研可信性案例。

---

## 6. Discussion

### 6.1 已经支持的结论

- 类型化计划可以约束 runtime action；
- observed graph 可从事实记录重建；
- failure 可以触发 Scientist 的有界局部重新授权；
- obligation 可以阻止漏交付和扩大报告口径；
- 正确停止与澄清可以作为有效终态被评价。

### 6.2 尚未支持的结论

- 规划质量或成功率普遍提升；
- checkpoint 相对 revision 的独立收益；
- 主题图科学准确性或行政区覆盖率；
- 多 Agent 优于单 Agent；
- 长期记忆、自学习、durable recovery 或生产级 sandbox；
- 跨模型、跨传感器和跨任务泛化。

### 6.3 与现代 Harness 的关系

URSA v0.5.3 可以称为 domain-specific、evidence-first research harness。它拥有现代 Harness 的主要
控制骨架，但保持 EO workflow/obligation/evidence semantics 为稳定内核。DeepSeek Harness/Cordis 的
能力插件化和 append-only session 思想用于长期工程对照，不触发当前整体迁移。

### 6.4 对后续章节的接口

- Chapter 2：ScientificConstraintPort、知识来源、方法适用条件、冲突和报告降级；
- Chapter 3：正式多任务 benchmark、baseline/ablation、科学结果、成本、专家与用户评测。

### 6.5 Threats to validity

单一主要数据场景、固定工具范围、task-11 单类故障、5×3 规模、有限 obligation 规则、固定模型，且
evaluator 主要验证过程和证据闭合而不验证专题精度。

---

## 7. Conclusion

结论只回答三件事：

1. URSA 从隐式对话原型演化为具有明确计划、执行和证据边界的研究型 Harness；
2. v0.5.3 在冻结任务中完成运行、停止、澄清、局部恢复和诚实交付闭环；
3. 下一阶段由 Chapter 2 补科学知识约束、Chapter 3 补正式效果与外部验证。

---

## 最小可视化与表格清单

### 一张既有范式图（Introduction，标注 prior published work）

- `assets/img/1Paradgim_trans_00.jpg`：从 data-centric RS analysis 到 User-centric RS Analysis；
  只承担领域动机与思想连续性，不作为 v0.5.3 当前架构或新增贡献。

### 三张唯一系统图（已有 Mermaid 源，需统一渲染）

1. `CH1-FIG-01`：Data–Tools–Brain 与共享 runtime/evaluation；
2. `CH1-FIG-02`：Manager–Scientist–Engineer–Executor 的角色责任；
3. `CH1-FIG-03`：规划—执行—反馈—恢复闭环。

### 两张结果图（待制作，不再增加总体架构图）

4. `CH1-EXP-FIG-01`：5 task × 3 condition 结果矩阵；颜色只表示 completed、controlled-stop、
   needs-clarification 和 evaluator closure，不把 stop 画成失败；
5. `CH1-EXP-FIG-02`：task-11 证据时间线/泳道图，显示 plan v1、NDVI、failure observation、Scientist
   revision、checkpoint/reuse、thematic map、area 和 report obligations。

### 三张核心表

1. 系统对象—责任—证据—限制表；
2. 五任务/三条件/预期终态与 evaluator 判据表；
3. 最终结果、token、wall time、允许/禁止 claim 表。

不再增加第四张总体架构图、单独工具大全图或框架 logo 墙。技术栈用一张简洁表或一页 PPT 表达；
相关工作用问题分类表，不用时间线堆论文。

## 明日提纲更新的最短路径

1. 复制本文件的 1–7 节标题到大论文提纲；
2. 从 Introduction 中确认一句话科学问题和 RQ1–RQ3；
3. 在 Method 对应位置插入三张现有 Mermaid 图的占位符；
4. 在 Results 填入 121/121、15/15、5/7/3、215,500 tokens 和 391.582 s；
5. 将 Discussion 的“支持/不支持”直接转为开题风险与后续工作；
6. 暂不扩写文献综述，只先按 2.1–2.4 建四个文献篮子。

## 下周面试材料映射

- 30 秒：问题、核心设计、15/15 closure 和诚实边界；
- 90 秒：prototype → runtime → URSA Harness 的演化；
- 3 分钟：三张系统图 + 一张结果矩阵；
- 10 分钟：加入 task-11 时间线、band/nodata 审计和 Harness 技术取舍；
- 追问准备：为什么多 Agent、为什么不用 LangGraph/DeepSeek Harness 重写、sandbox 到哪一级、
  checkpoint 是否 durable、15/15 是否表示全部成功、AutoGen 为什么暂不迁移。
