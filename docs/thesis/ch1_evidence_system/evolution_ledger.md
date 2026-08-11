# 第一章升级轨迹账本

> 事实优先。每个阶段同时记录“解决了什么”和“仍未证明什么”，避免把线性版本号写成线性科学进步。

## S0：论文原型（2025）

| 字段 | 记录 |
| --- | --- |
| 基线 | AutoGen GroupChat；Manager、Scientist、Engineer 三个 LLM 角色，外加 User 与 Executor；手写 `speaker_selection` |
| 状态 | 对话历史隐式承载；`Approve`/`End` 与 error keyword 驱动转换 |
| 工具方式 | Engineer 生成代码，Executor 本地执行；无统一 typed operator contract |
| 已有证据 | 论文两案例与 20-request benchmark，属于 `prior_published_evidence` |
| 关键版本 | 最早 notebook 在 `19db55b`，对象 `2b65c65c...`；May case 在 `878e84b` 完成重命名，对象 `89133a6e...`；均为 11 cells |
| 科学边界 | 证明早期多智能体遥感分析可行性；不证明 typed executability、repair 或 trace 机制 |

这个“草台班子”并没有消失：当前仍保留 `ExpertsRS/ExpertsRS_notebook.ipynb` 和原来的角色/路由骨架；精确的 2025 原版可从 Git 对象恢复。但当前 notebook 不是原版哈希，因为 2026 工具化阶段曾加入工具注册与配置清理。

## S1：工具层标准化（2026-04）

| 字段 | 记录 |
| --- | --- |
| 问题 | Engineer 重复生成遥感处理代码，工具接口、输出和错误缺少统一约定 |
| 决策 | 建立 `io/index/analysis/viz` 四类工具 kit、registry、OpenAI-style schema 和结构化返回 |
| 主要版本 | `ba1248c` 增加工具模块；`1cb829c` 稳定配置和 band-index API；`5128b24` 补文档 |
| notebook 变化 | 从 11 cells 变为 13 cells；增加标准工具加载、`function_map` 与 tool-first Engineer |
| 证据 | 18 个注册工具；当前 13 项脚本检查，属于 `engineering_support` |
| 未解决 | 工具“可调用”不等于物理语义正确；sensor band ID 与 raster stack position 被混用 |

这一步的叙事价值不是“工具更多”，而是把自由代码生成收束成可以签 contract、做测试和记录 provenance 的操作表面。

## S2：广义 runtime 探索旁支（2026-06）

`origin/codex/ch1-runtime-foundation` 上的 7 个未合并提交实现了显式 `RunState`、artifact manifest、ToolRuntime、18-tool contracts、deterministic evaluator、framework-neutral orchestrator、backend/evidence provenance 和 LangGraph adapter 占位面。

独立隔离运行 `test_runtime.py` 时 28 项检查通过。它是有效的工程探索，但必须标成 `side-branch`：

- orchestrator node 仍是确定性函数，live LLM backend 尚未接入；
- LangGraph 文件主要描述/依赖检查，不等于 durable LangGraph runtime；
- 功能范围很宽，未形成针对一个清晰科学问题的 matched experiment；
- 它先于 7 月的 claim freeze，不能自动并入当前 M1 结论。

这一阶段最重要的研究转折是：**“更完整 runtime”不必然等于“更清晰论文贡献”。**

## S3：从平台化转向可检验方法（2026-07）

7 月 17、29、30 日的文档逐步冻结了新的问题链：

```text
TaskSpec -> typed OperatorSpec -> WorkflowGraph
         -> deterministic validation
         -> targeted repair or controlled stop
         -> inspectable WorkflowTrace
```

同时明确 P0--P3 matched design、故障家族和章节边界，并主动排除 UI、框架迁移、分布式 runtime、更多角色和“多智能体普遍更优”等扩张。这不是降级，而是把工程资产压缩为可证伪的研究对象。

## S4：最小 workflow 与 ReAct sidecar（2026-08）

当前工作树新增但尚未提交的资产包括：

- `workflow/`：Task/Operator/Artifact/Graph、7 类 validator violation、唯一安全 missing-output repair、controlled stop、JSON trace；
- ReAct sidecar：Scientist/Engineer selector 与 Executor execution 分离；observation 回到请求者；每 Agent 工具预算；decision/tool/observation/handoff trace；
- no-API closeout：14 项 workflow/ReAct tests、18-tool 检查、repair/stop trace、scripted real-tool pilot。

设计上应把这两条线分开理解：typed workflow 是论文方法候选；ReAct 是让已有角色编排获得真实 observation loop 的支撑机制。当前 live ReAct path 尚未消费 `WorkflowGraph` validator/repair，因此还不是一个完全贯通的 live-LLM 方法运行。

## S5：审计触发的证据降级（2026-08-07）

独立审计确认：样例栅格的栈内描述为 `B2,B3,B4,B5,B6,B7,B8,B8A,B11,B12`，而工具默认 `nir_band=8, red_band=4` 被 rasterio 解释为第 8/4 个 band，实际是 `B8A/B5`。mask 路径又把 NaN 转成 class 0，导致 trace 的 `total_pixels=419839` 与 class counts 总和 `773120` 不一致。

因此证据状态修正为：

- tool execution、artifact creation、event routing 和计数：仍是有效 `diagnostic_evidence`；
- 当前 NDVI/mask 的科学语义正确性：`blocked`；
- M1 软件机制：可继续称最小原型；
- 真实案例与任何效果 claim：不得由该 pilot 支撑。

这次降级本身应保留为论文方法论素材：trace 的价值不只是展示成功，也用于发现接口语义和统计不变量问题。

## S6：科学前置条件修复与重新准入（2026-08-07）

审计后的修复没有增加 Agent、UI 或 runtime 平台功能，而是把已有工具链的科学准入规则写入
tool、operator contract、validator、prompt 和测试：

- 光谱默认参数从物理编号样式改为按 metadata 精确解析的 `B8/B4/...`；
- 数字仅作为有 provenance 的栈内位置 override，缺语义 metadata 时不再猜测；
- threshold 保留 255 nodata，并满足类别/有效/总像元不变量；
- area、mask 与 zonal statistics 加入 CRS、grid alignment 和 nodata 规则；
- EVI/MSAVI 显式处理缩放反射率；Sentinel-2 LST 在执行前停止；
- adapter callable signature、required bands/config 和真实 tool arguments 进入 regression tests。

2026-08-07 20:10 CST 的 closeout 通过 10 scientific + 4 benchmark + 11 workflow +
8 ReAct tests、13 tool checks、repair/controlled-stop 和 scripted pilot。新 pilot 将 B8/B4
解析到栈内 7/3，`248703 + 171136 = 419839` 个有效像元，另有 353281 nodata。

证据因此从“错误语义下的 integration smoke”重新准入为“单 fixture、scripted、带科学前置条件
provenance 的 diagnostic run”。它仍不是 vegetation thematic accuracy，也没有证明 live LLM 或
P0--P3 方法增益。审计—降级—规则化—复测—有限晋级的完整轨迹本身，是第一章可复用的
研究方法材料。

## S7：从静态工作流内核到自适应执行方法的设计冻结（2026-08-09）

研究者确认第一章仍以原论文的 User-centric RS 为根：用户用自然语言提出开放式遥感请求，Manager 管理用户交互与必要澄清，Scientist 负责方法判断与规划，Engineer/Executor 负责实现、工具调用和结果生成。此次升级不新增第四个 Agent，也不把 runtime 提升为新的 Data–Tools–Brain 模块；runtime 是所有角色共享的控制、状态与证据环境。

在此连续性上，最终方法候选只保留三个研究对象：

1. **可调整的分层规划**：Plan 是当前可修订的意图与假设，不要求首次生成完整、正确的全局图；
2. **随执行更新的过程图**：真实动作、工具反馈、产出、违规和计划修改在运行中逐步进入过程图；这张图用于检查和查询，而不是预先锁死执行的硬模板；
3. **基于检查点的局部恢复**：失败后保留已经确认有效的部分，从受影响位置修改计划或形成替代路径，并记录路径选择；当前只讨论逻辑状态与证据关系，不扩展到分布式持久化平台。

因此 S3--S6 形成的 `TaskSpec -> WorkflowGraph -> validator -> repair/stop -> trace` 不被否定，而被重新定位为“静态预先规划基线 + 可复用工程构件”。ReAct 工具反馈循环是动态形成执行过程的基础，也不是单独的新颖性。当前实现仍缺少统一的计划版本、过程图自动整理、检查点替代路径和基于过程图的反思，故本阶段只能写成“设计已冻结”，不能写成“已经实现”或“效果已经证明”。

外部方法边界也同时冻结：ReAct、Reflexion、LATS 与 In-the-Flow 属于方法借鉴，PROV-AGENT 与 Google AX 属于 provenance/runtime 工程借鉴，DS-STAR 是近邻，Spatial-Agent 是直接比较对象。规划、反思、图、trace、checkpoint 各自都不是新颖性；可检验增量只能来自它们如何在面向用户的遥感分析中被组织为“观测驱动的计划调整—过程图物化—局部恢复”，并通过匹配实验与静态基线区分。

2026-08-10 的生产对标没有改变三个研究对象，而是补充了控制边界：检查由角色责任、运行时
固定规则、按需且无执行权限的临时审核器与独立评测分层承担，不新增常驻审核 Agent；权限由
运行时预留最小检查接口并由唯一 Executor 使用。OpenTelemetry、STAC/OGC、容器隔离、
持久化编排、企业权限与 MCP/A2A 被记录为分期生产待办，
不在 D1 并行实施，也不升级为论文创新点。

同日完成的 D1 只读资产审计进一步确认：主线中的语义波段约定、规则检查、运行记录和 ReAct
选择/执行分离是权威基线；旧运行时旁支的编号、产出清单、调用来源与闭合检查可以选择性借用。
旁支 `HumanCheckpoint` 只记录人工计划批准，不是失败恢复；固定六节点流程、常驻审核/报告角色、
旧数字波段约定与 LangGraph 占位不进入 D2。真实运行事实按时间保留，过程图由这些事实逐步
整理；此结论属于设计审计，不是代码完成。

同日进一步修正了表达方式：`EventLedger`、`RunGraph`、`materializer` 等均降为技术实现代号，
不得进入论文贡献、PPT 主线或人工审批。对外只使用“按时间保留运行事实”“随执行更新的过程图”
和“把记录自动整理成图的程序”等普通中文；D1/D2/D3 首次出现时必须同时解释为资产盘点、
无 API 最小贯通和真实模型对照。这个修正不改变方法，只解决文档可读性和决策责任错位。

研究者随后认可 D2 的三条原则，并要求进一步澄清规划与过程图。最终边界是：分层规划是面向
未来的“总体目标—当前阶段—下一动作”，不默认展开搜索树；过程图是面向已发生事实、可由运行
记录确定性重建的结果；检查点只建立在工具动作完成、执行后检查通过、有效产出已登记的安全
边界。LATS/MCTS 可作为规划搜索的相关工作或未来对照，但不进入 D2；检查点实现直接借鉴成熟
框架的保存/恢复语义，不作为独立科学创新。

2026-08-11 进一步冻结了写作接口和章节边界。第一章架构只维护三张图：系统模块概念图、
多智能体角色责任图、规划—执行—反馈—恢复闭环图；它们在 `module_continuity_map.md` 中使用
稳定编号 `CH1-FIG-01/02/03`，作为论文和 PPT 的唯一来源。第三张图在叙事上承接原四状态
StateFlow，但 StateFlow 在代码与证据上仍保留为已发表基线，D2 前不声称已经完全替换。

同次澄清把三章的“验证”拆开：第一章负责可执行性、完整性、底线工具不变量和检查点恢复；
第二章负责方法适用性、证据充分性、验证义务、冲突与结论降级，并输出修改/补验证/询问/拒绝/
降级等行动义务；第三章在系统外独立评价结果、过程、故障和用户效用。第二章可以触发第一章的
恢复接口，但不重复实现检查点和分支管理。D2 足以形成 M1 最小方法原型闭环；真实模型效果只
由随后压缩的 D3-light 少量同任务对照承担。

## S8：D2 无 API 最小自适应闭环（2026-08-11）

D2 严格沿 D1 冻结的六个代码表面实现，没有新增 Agent、工具、知识库、图数据库或云服务：

- `PlanVersion` 保留计划 v1/v2、父版本、触发反馈和恢复检查点，历史不被覆盖；
- `WorkflowTrace` 在兼容旧 payload 的前提下增加稳定事件编号、顺序、责任者、对象与引用；
- 纯函数从同一组运行事实确定性整理简要过程图；
- `Checkpoint` 只引用恢复位置和已验证产出，不复制文件、不声称撤销外部 effect；
- 18 个工具被分为 read 4、compute 2、write-local-artifact 12，目录外写入默认拒绝；
- ReAct 决定、调用、反馈和交接继续写入同一记录外壳。

无 API 小样对真实 Sentinel-2 文件先读取元数据并建立检查点，再明确注入不存在的 `B99`。真实
工具按科学前置条件失败，计划 v2 保留该失败记录、引用元数据检查点并形成替代路径，复用
`artifact-metadata` 后以语义波段 `B8/B4` 成功生成 NDVI；另一个结果目录外写入请求被 policy
拒绝。17 条事实确定性重建为 17 个节点和 37 条时序/语义边（重新运行时数量保持一致），43 项
workflow、ReAct、科学前置条件、benchmark 与新增接口测试通过。

该阶段只晋级为 `implemented-no-api`/`mechanism evidence`：它证明接口关系和失败路径能够运行，
不证明真实 Scientist 会正确调整计划、方法优于静态工作流、NDVI 阈值有效、一般恢复能力或
企业权限完备性。生成的结果仍被 Git 忽略，源码与重建入口由本次 baseline 提交固定；正式实验前
仍须另行冻结真实模型、调用预算和完整实验环境。

## 下一次允许升级状态的条件

1. 将当前未跟踪的 workflow/ReAct/tests/docs 与环境信息纳入可重建 baseline；
2. 保持三个研究对象、分层检查责任和权限接口的现有边界，不继续扩张任务说明、科学风险标签、角色或工具本体；
3. 为 D3-light 固定 4--6 个代表任务、同模型/工具/预算和最小评分口径，再接真实 Scientist 生成/修改计划；
4. 先比较静态预先规划、反馈后调整计划、增加检查点恢复三种条件，再决定是否扩大；
5. 只有在可复现的 live-LLM 匹配实验后，才讨论规划可靠性、恢复收益或成本；第二章科学约束与第三章完整评测保持隔离。
