# 第一章架构—证据—Claim 矩阵

> 本文件是执行者使用的技术审计表，不是研究者审批界面。论文与人工沟通统一使用“可调整的
> 分层规划、随执行更新的过程图、基于检查点的局部恢复”。代码类名或字段名只在反引号中出现，
> 不自动成为论文术语。

> 2026-08-29 current-state note：下方 D1/D2 资产映射保留为历史设计 provenance；当前实现与证据
> 状态以本节“内部架构映射”、`claim_registry.md` 和 `v053_evidence_index.md` 为准。v0.5.3 已完成
> 统一 live runtime、121/121 回归和一次 15/15 v2 evaluator closure 的 5×3 pilot，但正式机制效果
> 与科学准确性仍未得到证明。

## 内部架构映射

| 对象 | 当前实现 | 证据角色 | 客观缺口 | 允许表述 |
| --- | --- | --- | --- | --- |
| 角色分工 | Manager/Scientist/Engineer + User/Executor；notebook 与 ReAct sidecar | prior + engineering | 未证明角色数量或 multi-agent 本身带来增益 | 保留已发表原型的协作设计 |
| v2 交付闭合 | runtime-owned `DeliveryObligation`、Manager structured deliverables、v2 evaluator | live engineering evidence | 仅受支持规则与单场景 | 原始请求不能被 Scientist 的 requested_outputs 静默删减 |
| ProfiledUserAgent | 一次性规则/live clarification fixture | isolated integration evidence | 非常驻角色、非用户研究 | 证明 `.resume()` 闭环，不证明用户效用 |
| 18-tool layer | 四个 kit、registry、schema、结构化返回、semantic band resolver | engineering | 依赖只设下限、未冻结环境；多传感器语义覆盖有限 | 建立了带 fail-closed 科学前置条件的统一工具表面 |
| `TaskSpec` | goal、AOI/time、expected outputs、constraints；真实 Scientist 输出完整 typed task/plan | live engineering | 只覆盖冻结请求与 schema；不证明任务理解普遍正确 | 实现并在 v0.5.3 live runtime 使用最小 typed task object |
| `OperatorSpec` | 18 adapters、typed input/output、required bands/config、precondition、failure/default | engineering | 类型仍粗；缺 graph-level CRS、resolution、extent 与完整 sensor ontology | 为现有工具建立 versioned minimal contracts |
| static `WorkflowGraph` | artifact dependency 与 ordered nodes | engineering | 是 upfront graph；未与 live observation loop 贯通 | 已实现静态数据依赖图；当前定位为 baseline/中间资产，不是最终中心 |
| validator | unknown/missing/type/order/file/output、required band/config 与 output contract 检查 | engineering + diagnostic | CRS/transform 当前在执行工具检查；缺 graph-level geometry/extent/resolution/QA 与系统化参数范围 | 实现 deterministic pre-execution structure + selected EO semantic checks |
| targeted repair | 单一 missing output 且唯一 candidate 时补一个 node | engineering + diagnostic | 不是 observation-driven replanning；candidate uniqueness 依赖粗类型 | 已实现 deterministic repair baseline，不升级为一般恢复能力 |
| controlled stop | blocking/ambiguous/unsupported 时停止并记录 | engineering + diagnostic | 没有 ask-user/replan 的 live integration | 对不支持情形显式停止，不隐藏改写 |
| `WorkflowTrace` | 旧事件 payload + 稳定事件编号、顺序、责任者、对象和类型化引用 | engineering + diagnostic | 缺 schema/model/tool/data version 与 replay runner | 已形成兼容旧路径的统一运行事实外壳 |
| ReAct routing | AutoGen AgentChat 角色会话 + 项目 runtime 的计划/动作/observation 路径 | live engineering | ReAct 是通用模式；角色会话与运行事实的组合不是独立创新 | 保留角色语义与真实反馈，不把框架或 ReAct 包装为贡献 |
| 分层检查责任 | Manager/Scientist/Engineer 责任、runtime 固定规则、外部 v2 evaluator | implemented support | 规则不能判断完整科学适用性；无通用语义审核器 | 已实现执行前/后/结束闭合和标准答案隔离，不称验证一切结果 |
| 权限检查接口 | 允许工具、eligible node、默认拒绝 policy、唯一 Executor | live implemented-interface | 只覆盖本地路径/冻结工具；无企业身份、容器和多租户隔离 | 已接入 v0.5.3 live runtime，不称完整权限或进程沙箱 |
| 可修改的计划 | 真实 Scientist 维护完整版本图、父版本、触发 observation、影响范围和 checkpoint 引用 | supported-live-narrow | task-11 为 `local_reauthorization_only`；不证明生成更优路径 | 已证明 observation 后局部重新授权，不称规划效果提升 |
| 随执行更新的过程图 | planned graph 按版本保存，observed graph 从 trace 重建并带稳定引用 | supported-live | 图主要用于审计与评测；未证明反馈图提高模型决策 | 已形成事实型过程图，不是先验硬剧本或图数据库 |
| 基于检查点的局部恢复 | 运行检查点引用有效产物；task-11 复用 NDVI 后完成受影响分支 | supported-live-narrow | 单一批准故障；不可逆动作不能撤销；无 durable recovery | 已证明运行内局部复用与重新授权，不称通用恢复 |
| broad runtime branch | state/checkpoint/artifact/evaluator/provenance | engineering exploration | side branch、deterministic nodes、未并入 current method | 作为设计探索和候选资产，不作为当前完成度 |
| v2 5×3 pilot | 冻结 5 任务 × 3 条件、真实模型、外部 v2 evaluator、独立 run artifacts | live integration evidence | 单轮、小面板，不是正式效果或外部效度实验 | 15/15 closure 与 5/7/3 终态可报告；不能称成功率或规划提升 |
| live model adapter | AutoGen AgentChat 0.7.5 / OpenAI-compatible provider，经统一 runtime 生成结构化角色决策 | live engineering | 框架生命周期与模型变化不构成论文因变量 | 说明当前技术实现；不把 AutoGen 或 provider 当方法创新 |

## D1 资产映射（2026-08-10）

> 状态：`completed-design-audit`。本节只决定复用、改造与拒绝，不把任何目标标成 implemented，
> 不合并分支、不修改运行代码、不消费 LLM API。

### 主线工作树资产

| 资产与位置 | 已验证事实 | D1 归属 | D2 处理决定 |
| --- | --- | --- | --- |
| `workflow/specs.py::TaskSpec` | 用户目标、期望输出、约束、未决问题可序列化 | Plan 的稳定用户边界 | 原样复用；不继续增加科学风险字段 |
| `workflow/specs.py::OperatorSpec/ArtifactSpec` + `adapters.py` | 18 tools、语义波段、输入/输出和部分前置条件；有 signature drift tests | Action contract、Artifact 基础 | 以 main 为权威；不抽取旁支旧数字波段 contracts |
| `workflow/graph.py::WorkflowGraph` | 静态 nodes/artifacts 依赖与顺序 | B1 静态基线；未来过程图的数据依赖局部视图 | 不改造成全局动态图；保留为基线和自动整理程序可消费的输入 |
| `workflow/validator.py` | pre-execution 类型、顺序、文件、band/config/output violations | pre-action/plan-closure deterministic gate | 拆分调用时机，不重写规则；未来对候选 action/阶段闭合分别调用 |
| `workflow/repair.py::RepairDecision` | 只补唯一缺失输出，否则 stop；保持已有节点 | B1 repair baseline；recovery 的保守反例 | 不冒充 checkpoint recovery；保留作 comparator 和 stop policy 输入 |
| `workflow/trace.py::WorkflowTrace` | 按时间追加事件 + `run_id`，可写 JSON | 按时间保存运行事实的直接起点 | 扩展事件编号和引用；保持旧事件可读，不把完整记录回填 Agent 上下文 |
| `react_orchestration.py::ReActRoutingState` | decision/tool/observation/handoff、owner return、预算、exclusive Executor | Observation-driven execution adapter | 保留路由；注入框架无关 run ledger，不把状态继续堆在 AutoGen selector 内 |
| current tests/closeout | 11 workflow、8 ReAct、10 scientific checks、4 benchmark checks；2026-08-11 M1 重跑 33 项，D2 重跑 43 项通过，另有 13 项工具检查 | regression baseline | D2 新增记录结构、过程图重建、权限和替代路径测试，不改写旧预期；当前 import 依赖 `ExpertsRS/` working directory，作为 packaging 风险保留 |

### broad runtime branch 选择性抽取

| 旁支资产 | 客观含义 | 决定 | 原因/限制 |
| --- | --- | --- | --- |
| `runtime/state.py::RunState` 的 run/tool/artifact/backend IDs 与 timestamps | 可序列化运行台账 | **selective reuse** | 只抽字段/序列化模式；不抽固定 phase/role 枚举和宽状态容器 |
| `runtime/artifacts.py::RunArtifactStore` manifest 模式 | per-run state/artifact manifest | **selective reuse** | 复用 manifest/version 思路；补 checksum/validity/version，避免直接复制副作用实现 |
| `runtime/backends.py::BackendCallRecord` | provider/model/token/cost/latency provenance | **selective reuse** | D2 只保留 model/config/cost provenance；不引入 backend planner |
| `runtime/evaluator.py::RuntimeEvaluator` | deterministic trace/artifact closure checks | **extract checks, reject role** | 规则可进入 post-action/final gates；`AgentRole.VERIFIER` 命名不构成独立 Agent |
| `runtime/state.py::HumanCheckpoint` | 计划批准的 pending/approved record | **do not reuse as recovery checkpoint** | 没有 artifact snapshot、resume point、branch lineage 或失败恢复语义 |
| `runtime/orchestration.py` 六节点固定流程 | manager→scientist→approval→engineer→verifier→reporter | **reject** | deterministic vegetation template；重新引入硬 workflow 与额外角色 |
| `runtime/contracts.py` | 旧 Parameter/Artifact/Tool contracts | **reject as authority** | 使用旧数字 band position 约定，落后于 main 的 semantic-band 修复 |
| `runtime/langgraph_adapter.py` | graph 描述/依赖占位 | **defer** | 没有 durable LangGraph execution；框架不定义方法 claim |

### 三个研究对象与支撑能力对照

| 目标对象 | 直接复用 | 必须新增的最小语义 | 明确不做 |
| --- | --- | --- | --- |
| 可修改的计划 | `TaskSpec`、Scientist 决定/交接 | 计划编号、版本、父版本、责任者、范围、状态、修改原因；总体—阶段—下一动作引用 | 首次生成完整工作流图、保存长推理文本、构建计划搜索树 |
| 按时间保存运行事实 → 随执行更新的过程图 | `WorkflowTrace`、ReAct 事件、静态图/产出 | 全局事件编号、顺序、责任者和引用；把计划/动作/反馈/产出/检查/路径自动整理成简要视图 | 把图当执行剧本、把全部 JSON 塞回模型、先建图数据库 |
| 基于检查点的局部恢复 | `RepairDecision` 停止信号、产出编号、旁支清单模式 | 检查点、替代路径、恢复位置、有效产出和原因；形成/选择/放弃路径的关系 | 撤销任意不可逆动作、分布式持久化、MCTS、学习/自进化 |
| 分层检查责任 | 当前规则检查、科学前置条件、旁支闭合检查 | 执行前/后/结束时的检查记录；语义审核触发条件和只读建议 | 常驻审核 Agent、审核器执行工具、评测标准答案回流 |
| 权限检查接口 | 唯一 Executor、Scientist/Engineer 工具注册、工具预算 | 谁、对什么资源、做什么、允许/拒绝/确认、限制、理由和规则版本 | 企业身份、密钥、多租户、沙箱和外部协议实现 |

### 当前 18-tool 最小权限分类

| effect class | 工具 | 当前 policy |
| --- | --- | --- |
| `read`（4） | list files、read metadata、read band、read bands | Scientist 只可选择前两项；Engineer 可提出；Executor 执行；资源限 `ExpertsRS/data` |
| `compute`（2） | area、zonal statistics | Engineer 提出；Executor 执行；输入必须是已登记 artifact |
| `write_local_artifact`（12） | save raster、6 indices、threshold、mask、3 visualization tools | Engineer 提出；Executor 执行；输出必须限 `ExpertsRS/results`/run dir 并登记 artifact |
| `external` / `irreversible`（0） | 当前无 | 默认 deny；未来新增必须经过 Manager/user confirm 与新 policy version |

角色分工不是授权机制：Agent 只能提出 action，Runtime 产生 authorization decision，Executor
才产生 effect。当前代码只有 selector/executor split 与预算，故本表仍是 `design-frozen support`。

### D2 最小对象关系（技术附录）

```text
任务说明
  └─ 计划 v1 ──提出──> 工具动作
        │               ├─ 权限决定
        │               ├─ 执行前检查
        │               └─ Executor 真实执行
        │                       └─ 工具反馈 + 产出
        │                              └─ 执行后检查
        └─ 计划 v2（父版本=v1，修改原因=反馈或违规）
                 └─ 检查点 ──形成──> 替代路径 B

按时间保存的运行事实 ──自动整理──> 简要过程图
```

冻结不变量：真实运行事实按时间保留；过程图由事实逐步整理；计划可以修改，但历史版本、
修改原因和失败路径不可覆盖；静态 `WorkflowGraph` 只保留为 B1 基线和局部依赖视图。

### D2 唯一允许的代码表面

1. 新增一个不依赖特定框架的运行记录/状态模块，承载最小记录；
2. 向 `WorkflowTrace` 增加事件编号、顺序、责任者与引用，同时兼容旧事件；
3. 新增把运行记录自动整理成简要过程图的纯函数，不引入图数据库；
4. 新增默认拒绝的权限检查与当前 18 个工具动作分类，由唯一 Executor 调用；
5. 用适配器将 ReAct 的决定、调用、反馈和交接写入同一组运行记录；
6. 只实现一个失败分支 fixture，不接 UI、云服务、完整 IAM、STAC service 或 durable runtime。

除这六项外的代码变化必须重新过 Scope Gate。

### D2 实现复核（2026-08-11）

上述六项已经按原边界完成：`runtime.py` 提供不可变计划版本、逻辑检查点、18-tool 动作分类、
本地默认拒绝权限策略，以及由记录确定性整理过程图的纯函数；`WorkflowTrace` 保留旧 payload，
新增稳定事件编号、顺序、责任者、对象和引用；ReAct sidecar 写入同一事件外壳。43 项 workflow、
ReAct、科学前置条件、benchmark 与新增接口测试通过。

唯一真实工具故障小样明确注入不存在的 `B99`，工具按失败关闭返回，随后计划 v2 引用失败反馈和
最近元数据检查点，复用 `artifact-metadata`，改用 metadata 已验证的 `B8/B4` 后成功；过程图仅由
17 条运行事实重建，保留原计划、失败动作、替代路径、两个检查点和一次目录外写入拒绝。该证据
只支持“D2 最小机制已贯通”，不支持真实模型可靠性、主题精度、通用恢复或权限系统完备性。

## 外部直接重叠与差异

| 工作 | 关系 | 已覆盖的相邻能力 | 对第一章的约束 |
| --- | --- | --- | --- |
| [Spatial-Agent (ACL 2026)](https://aclanthology.org/2026.acl-long.679/) | 直接竞争 | GeoFlow DAG、concept/functional-role constraints、IO-port composition、可执行 workflow、ReAct/Reflexion 对照 | 不能把 graph、空间 grounding 或结构有效性本身写成新颖性；static hard graph 应作为强 baseline |
| [Constraint-aware AoV planning (GeoAI 2026)](https://research.utwente.nl/en/publications/constraint-aware-aov-planning-for-orchestrating-autonomous-geospa/) | 直接近邻 | JSON AoV workflow、CRS/geometry/extent edge validation、50-task evaluation | 当前 validator 空间语义更弱；差异不能只落在更多 edge checks |
| [Earth-Agent (ICLR 2026)](https://openreview.net/forum?id=dkIXAbWuxO) | 领域系统基线 | MCP tool ecosystem、248 expert-curated tasks、trajectory 与 final outcome 评估 | 工具调用和 trajectory evaluation 已是强基线；需机制消融而非 end-to-end 展示 |
| [OpenEarthAgent (2026)](https://arxiv.org/abs/2602.17665) | 领域系统基线 | verified multi-step trajectories、structured trace 与大规模训练/评测实例 | ReAct trace 不具独立 novelty；可作为 adaptive execution 的评测载体 |
| [ReAct (ICLR 2023)](https://arxiv.org/abs/2210.03629) | 方法借鉴；非 novelty | reasoning–action–observation 交替，并随反馈维护/更新 action plan | 本章必须说明新增对象超出普通 ReAct routing |
| [DS-STAR (2025)](https://arxiv.org/abs/2509.21825) | 近邻方法 | 从简单可执行计划开始，以逐阶段 verification feedback 迭代细化 | iterative planning/verification 不能作为单独新颖性；应作为 static-vs-adaptive comparator |
| [LATS (ICLR 2024)](https://openreview.net/forum?id=njwv9BsGHF) | 方法借鉴；非 novelty | 将 reasoning、acting、planning 与蒙特卡洛树搜索/反思结合，主动探索多个候选路径 | 多候选搜索已有成熟路线；本章分层规划不等于树搜索，D2 不实现 MCTS |
| [Reflexion (NeurIPS 2023)](https://papers.nips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html) | 方法借鉴；非 novelty | 用反馈与 episodic verbal memory 改进后续尝试 | 当前仅研究 within-run revision/recovery，不称 verbal RL 或学习 |
| [In-the-Flow Agentic System Optimization (ICLR 2026)](https://openreview.net/forum?id=Mf5AleTUVK) | 方法借鉴；非 novelty | planner–executor–verifier–generator、evolving memory 与多轮优化 | 当前无 planner training/Flow-GRPO；不能把角色循环或 verifier 视为新颖性 |
| [PROV-AGENT (2025)](https://arxiv.org/abs/2508.02866) | 工程/表示借鉴；非 novelty | 扩展 W3C PROV 关联 Agent 决策、上下文与下游 workflow provenance | 过程追踪图本身不是贡献；本章过程图必须服务计划修改和局部恢复的可检验机制 |
| [Google Agent Executor (AX)](https://github.com/google/ax) | 工程借鉴；非论文 comparator | event log、single writer、隔离执行、resume 与 distributed actor | 说明 runtime 是共享运行基础层；当前项目不声称 durable/distributed runtime，且 AX 仍 early development |
| [Agentic AI for Remote Sensing: challenges](https://arxiv.org/abs/2604.24919) | 研究议程 | structured geospatial state、tool-aware reasoning、verifier-guided execution、trajectory evaluation | 支持问题重要性，但议程不能被当成我们的独占创新 |

## 生产控制面对照（非 novelty）

| 一手规范/实践 | 当前可映射资产 | D1 只记录的接口 | 明确延期 |
| --- | --- | --- | --- |
| [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/specs/semconv/) 与 [Google ADK observability](https://adk.dev/observability/) | `WorkflowTrace`、ReAct events、未来过程图 | 运行/计划/事件/工具/产出编号，模型/工具/数据/规则版本 | OTel 导出、后端、采样、在线面板 |
| [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | 轨迹、停止信号、产出引用 | 借鉴“每步状态快照、从最近成功步骤恢复、重放和形成替代路径”的语义 | 不迁移 LangGraph，不接数据库，不把框架检查点写成论文创新 |
| [AutoGen state management](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html) | 现有 AutoGen 角色与 ReAct 状态 | 借鉴 Agent/Team 状态可序列化、停止后再加载的接口边界 | 不直接复制团队状态，不假设加载状态能撤销已产生的遥感文件 |
| [OpenAI Agents SDK sessions and tracing](https://openai.github.io/openai-agents-python/) | 对话历史与运行记录的分离设计 | 借鉴会话状态、工具执行边界和过程追踪是不同支撑能力 | 不迁移 SDK，不把会话记忆或 tracing 当作局部恢复本身 |
| [Google ADK evaluation](https://adk.dev/evaluate/) | validation ladder、20-task lineage、fault fixtures | trajectory、final outcome 与 cost 分离；gold isolation | managed eval service、online evaluation、user simulation |
| [MCP security best practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices) | exclusive Executor、tool registry、budget | principal/capability/resource/effect/decision/limits/policy version | OAuth、企业 IAM、secret、多租户与外部 MCP server |
| [OGC STAC](https://www.ogc.org/standards/stac/) 与 [EO Application Package](https://docs.ogc.org/bp/20-089r1.html) | `ArtifactSpec`、manifest、operator I/O | artifact lineage/checksum 与 STAC/Process 字段 crosswalk | STAC service、OGC API Processes、container stage-in/out |
| [Google A2A](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/) | 当前无跨组织 Agent 边界 | 仅记录未来 interoperability seam | A2A server/client、capability discovery、远程 Agent federation |

这些条目约束“怎样工程化”，不定义“论文创新是什么”。D1 不选择云厂商或 Agent 框架，
只保证当前对象未来可映射，避免生产考虑反向驱动方法扩张。

## 推荐科学定位

当前最可防守的候选不是“提出遥感工作流图”，而是：

> 在已发表 User-centric RS 多智能体流程基础上，把 Scientist 的可调整分层规划、真实工具反馈、
> 随执行更新的过程图和检查点局部恢复组织成一个闭环，并研究它相比旧对话流程和静态预先
> 规划，是否让开放遥感任务更容易执行完成、从失败中恢复并接受追溯检查。

三个研究对象已经在统一 live runtime 中形成小规模集成证据，但只有正式 baseline/ablation 才能
进一步证明效果。自然语言交互、角色分工、ReAct、图、运行记录、检查点和工具注册均不能单独
作为创新点。

## 当前最强反对意见

1. **“这只是把普通类型检查搬到遥感工具上。”** 当前 band/nodata/grid/radiometry/LST admission 已形成 EO-specific 最小反例，但是否构成方法增量仍必须依赖 matched fault experiment。
2. **“Spatial-Agent/AoV 已经有图和约束。”** 属实；静态图必须作为基线。候选差异是过程图
   从先验剧本转为随执行更新的接口，并服务工具反馈后的计划修改和检查点局部恢复；仍需同任务
   对照实验来证明。
3. **“ReAct + 多 Agent 是标准拼装。”** 同意；ReAct 只作为系统支撑，不列为论文核心创新。
4. **“最初 pilot 不是正确 NDVI，如何谈可靠性？”** 保留原始降级记录，并展示问题如何被转为 semantic contracts 与 regression fixtures；新 pilot 只证明编码前置条件和链路，不声称 thematic accuracy。
5. **“typed workflow 与 live LLM 没有接通。”** 该问题已由 v0.5.3 解决：真实 Scientist 计划、
   plan-bound action、工具反馈和报告闭合进入统一 runtime；剩余反对意见是小面板集成通过不能证明
   方法效果或跨任务泛化。
6. **“这只是 ReAct + 日志 + checkpoint。”** 单项确实都是已有思想；只能通过遥感任务中的
   操作定义、失败家族、可恢复状态边界和 matched results 证明组合是否形成领域方法贡献。

## 禁止表述

- “首次提出 geospatial/remote-sensing workflow graph”；
- “证明多智能体优于单智能体”；
- “真实 LLM 规划可靠性已经提升”；
- “能够自动修复一般遥感工作流”；
- “现有 greenspace mask 已验证科学正确”；
- “已经实现 durable / distributed runtime”。
