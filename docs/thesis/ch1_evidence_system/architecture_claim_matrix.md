# 第一章架构—证据—Claim 矩阵

> 本文件是执行者使用的技术审计表，不是研究者审批界面。论文与人工沟通统一使用“可调整的
> 分层规划、随执行更新的过程图、基于检查点的局部恢复”。代码类名或字段名只在反引号中出现，
> 不自动成为论文术语。

## 内部架构映射

| 对象 | 当前实现 | 证据角色 | 客观缺口 | 允许表述 |
| --- | --- | --- | --- | --- |
| 角色分工 | Manager/Scientist/Engineer + User/Executor；notebook 与 ReAct sidecar | prior + engineering | 未证明角色数量或 multi-agent 本身带来增益 | 保留已发表原型的协作设计 |
| 18-tool layer | 四个 kit、registry、schema、结构化返回、semantic band resolver | engineering | 依赖只设下限、未冻结环境；多传感器语义覆盖有限 | 建立了带 fail-closed 科学前置条件的统一工具表面 |
| `TaskSpec` | goal、AOI/time、expected outputs、constraints 等 | engineering | 无 schema version/round-trip test；尚未由 LLM 稳定生成 | 实现了最小 typed task object |
| `OperatorSpec` | 18 adapters、typed input/output、required bands/config、precondition、failure/default | engineering | 类型仍粗；缺 graph-level CRS、resolution、extent 与完整 sensor ontology | 为现有工具建立 versioned minimal contracts |
| static `WorkflowGraph` | artifact dependency 与 ordered nodes | engineering | 是 upfront graph；未与 live observation loop 贯通 | 已实现静态数据依赖图；当前定位为 baseline/中间资产，不是最终中心 |
| validator | unknown/missing/type/order/file/output、required band/config 与 output contract 检查 | engineering + diagnostic | CRS/transform 当前在执行工具检查；缺 graph-level geometry/extent/resolution/QA 与系统化参数范围 | 实现 deterministic pre-execution structure + selected EO semantic checks |
| targeted repair | 单一 missing output 且唯一 candidate 时补一个 node | engineering + diagnostic | 不是 observation-driven replanning；candidate uniqueness 依赖粗类型 | 已实现 deterministic repair baseline，不升级为一般恢复能力 |
| controlled stop | blocking/ambiguous/unsupported 时停止并记录 | engineering + diagnostic | 没有 ask-user/replan 的 live integration | 对不支持情形显式停止，不隐藏改写 |
| `WorkflowTrace` | 旧事件 payload + 稳定事件编号、顺序、责任者、对象和类型化引用 | engineering + diagnostic | 缺 schema/model/tool/data version 与 replay runner | 已形成兼容旧路径的统一运行事实外壳 |
| ReAct routing | AG2/AutoGen GroupChat + 项目 selector/executor 分离、observation return、预算 | engineering | ReAct 是通用模式；尚未与 typed runtime 串成 live path | 改善原型交互语义与可观测性；不是独立创新 |
| 分层检查责任 | Manager 用户确认、Scientist/Engineer 责任、固定规则检查、独立评测已有部分资产 | design-frozen support | 尚无执行前/后/结束时的统一编排；无按需审核器约定 | 检查责任已分层定义；不声称已实现常驻审核 Agent 或验证一切结果 |
| 权限检查接口 | 18-tool effect 表、本地默认拒绝 policy、允许/拒绝记录；唯一 Executor 仍是执行入口 | implemented-interface | 尚未把 policy 强制接入所有 live ReAct 调用；无确认流、企业身份与隔离 | 已实现第一章最小接口，不称完整权限系统或创新点 |
| 可修改的计划 | 不可变计划版本记录总体目标、阶段、下一动作、父版本、触发反馈与恢复检查点 | implemented-no-api | 由 fixture 构造，尚未由真实 Scientist 稳定生成/修改 | 已实现最小表示和单一故障修订，不称规划效果提升 |
| 随执行更新的过程图 | 纯函数从运行事实确定性整理计划、权限、动作、反馈、产出、检查点与改道关系 | implemented-no-api | 当前是紧凑 JSON，无 live-Agent 查询/反思与 schema version | 已实现审计接口，不是先验硬剧本或图数据库 |
| 基于检查点的局部恢复 | 逻辑检查点引用恢复位置和有效产出；故障 fixture 保留失败路径并复用元数据 | implemented-fixture-narrow | 单一注入故障；不可逆动作不能撤销，无通用分支搜索 | 已实现最小局部恢复，不称自我学习 |
| broad runtime branch | state/checkpoint/artifact/evaluator/provenance | engineering exploration | side branch、deterministic nodes、未并入 current method | 作为设计探索和候选资产，不作为当前完成度 |
| P0--P3 | 文档设计 | design only | 尚无 matched tasks/runs/statistics/error analysis | 只能说“已设计”，不能说“有效” |
| D3 direct 模型调用适配器 | 手写 OpenAI-compatible REST + 单步 JSON 解析 | engineering preparation | 不是 AutoGen/AG2 调度，runner 仍以 task/phase 推进；不得作为 live multi-agent D3 执行器 | 只可称模型调用与脱敏边界准备；真实 D3 需 AG2–runtime bridge |

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

三个研究对象当前只是“设计已冻结”，不是“已经实现”；只有同任务对照证据才能进一步证明
有效。自然语言交互、角色分工、ReAct、图、运行记录、检查点和工具注册均不能单独作为创新点。

## 当前最强反对意见

1. **“这只是把普通类型检查搬到遥感工具上。”** 当前 band/nodata/grid/radiometry/LST admission 已形成 EO-specific 最小反例，但是否构成方法增量仍必须依赖 matched fault experiment。
2. **“Spatial-Agent/AoV 已经有图和约束。”** 属实；静态图必须作为基线。候选差异是过程图
   从先验剧本转为随执行更新的接口，并服务工具反馈后的计划修改和检查点局部恢复；仍需同任务
   对照实验来证明。
3. **“ReAct + 多 Agent 是标准拼装。”** 同意；ReAct 只作为系统支撑，不列为论文核心创新。
4. **“最初 pilot 不是正确 NDVI，如何谈可靠性？”** 保留原始降级记录，并展示问题如何被转为 semantic contracts 与 regression fixtures；新 pilot 只证明编码前置条件和链路，不声称 thematic accuracy。
5. **“typed workflow 与 live LLM 没有接通。”** 属实；当前是 method kernel 与 orchestration surface 两个通过测试的部件，不是 live-LLM end-to-end evidence。
6. **“这只是 ReAct + 日志 + checkpoint。”** 单项确实都是已有思想；只能通过遥感任务中的
   操作定义、失败家族、可恢复状态边界和 matched results 证明组合是否形成领域方法贡献。

## 禁止表述

- “首次提出 geospatial/remote-sensing workflow graph”；
- “证明多智能体优于单智能体”；
- “真实 LLM 规划可靠性已经提升”；
- “能够自动修复一般遥感工作流”；
- “现有 greenspace mask 已验证科学正确”；
- “已经实现 durable / distributed runtime”。
