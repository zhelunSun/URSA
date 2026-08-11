# 第一章 Claim Registry

> 稳定 ID 用于论文段落、PPT 页脚、答辩稿和实验 manifest。引用 claim 时同时写 evidence role。

| Claim ID | 当前状态 | 允许使用的句子 | 支持证据 | 主要反证/限制 | 晋级门槛 |
| --- | --- | --- | --- | --- | --- |
| `C1-ARCH-01` | accepted-framing | 第一章继承 User-centric RS 与 Data–Tools–Brain；runtime 是三类角色共用、连接 Brain 计划、Tools effect 与 Data/observation/artifact 的控制与证据外壳，不是新 Agent 或第四概念模块。 | published framework、module continuity map、ADR-001、D2 fixture | 当前只贯通无 API 小样，尚未统一接入 live LLM | 作为架构叙事，不升级为效果 claim |
| `C1-HIST-01` | supported-prior | 已发表 ExpertsRS 证明了多智能体辅助非专家完成遥感分析的初步可行性。 | paper、两案例、20-request benchmark | 小样本、单场景、不能证明新机制 | 不升级；始终作为 prior evidence |
| `C1-ENG-01` | supported-local | 已将现有遥感能力收束为 18 个注册工具和统一调用表面，并用 callable-signature test 防止 adapter 漂移。 | `tools/`、registry、13 tool checks、signature contract test、Chapter 1 baseline commits | 依赖未完全锁定；尚无公开 release tag | 完整环境锁定 + release provenance |
| `C1-METH-01` | implemented-baseline | 已实现最小 `TaskSpec`、`OperatorSpec`、产出与静态工作流图表示。 | `workflow/specs.py`、`graph.py`、tests | 静态预先规划；真实模型尚未生成/消费；不再作为最终方法中心 | 保留为静态基线和未来过程图的输入资产 |
| `C1-METH-02` | implemented-narrow | validator 能确定性发现当前编码的结构/类型/顺序/文件/输出、required-band、required-config 与 output-contract violation。 | `validator.py`、33-test closeout 中的 workflow/scientific fixtures | CRS/transform 在执行工具中检查，尚未形成完整 graph-level extent/resolution/QA semantics；部分 violation family 未穷尽 | fault-family coverage + task-driven EO contracts |
| `C1-METH-03` | implemented-narrow | 对一个唯一安全的缺失输出，prototype 可只补受影响步骤；不安全时显式停止。 | `repair.py`、repair/stop traces | 不是一般 repair；unaffected graph test 不完整 | real ambiguity、graph diff invariant、LLM failures |
| `C1-OBS-01` | implemented-diagnostic | prototype 能以稳定事件编号、顺序、责任者和引用记录计划版本、权限、动作、反馈、产出、检查点与结局，并从同一记录确定性重建简要过程图；旧 ReAct payload 保持兼容。 | `trace.py`、`runtime.py`、D2 trace/graph、tests | 缺 schema version/checksum/replay runner；live ReAct 尚未生成全部语义关系 | D3 前只补实验必需 manifest/version，不扩建平台 |
| `C1-SYS-01` | implemented-no-api | 带明确类型的静态内核、ReAct 路由和 D2 自适应接口均已通过回归；真实工具故障能触发计划修订并从检查点复用有效产出。 | 43 tests、D2 closeout、adaptive trace/graph/summary | 脚本化故障注入；尚无 live-LLM matched run | D3-light 接真实模型并做同任务对照 |
| `C1-SCI-01` | diagnostic-supported | scripted pilot 已按 metadata 把 B8/B4 解析到栈内 7/3，并保持 nodata/class count 不变量，可作为真实工具科学语义前置条件的诊断证据。 | 10 scientific tests、pilot trace、ADR-002 | threshold=0.3 未校准；无 thematic gold；仅单场景 scripted run | independent gold + task-level scientific review；效果 claim 仍需 P0--P3 |
| `C1-DESIGN-01` | implemented-no-api | 第一章候选方法只保留三个研究对象：可调整的分层规划、随执行更新的过程图、基于检查点的局部恢复；三者已在一个无 API 小样中贯通。 | researcher decision、scope gate、ADR-001、D2 trace/graph | 只证明接口和机制可运行，不证明真实模型效果 | D3 静态—自适应同任务对照 |
| `C1-DESIGN-02` | implemented-no-api | 规划表示系统接下来准备怎样做，执行表示实际做了什么；真实动作、反馈、产出和失败按时间保留，过程图由这些事实确定性整理，而不是预先限制 Agent 的硬剧本。 | `PlanVersion`、stable event envelope、`build_process_graph`、determinism tests、D2 graph | 当前过程图是紧凑 JSON 视图，尚无 live-Agent 查询/反思 | D3 验证真实模型是否正确消费该视图 |
| `C1-DESIGN-03` | implemented-fixture-narrow | 局部恢复只表示从明确检查点复用已验证产出并形成替代路径；D2 故障小样复用了元数据产出并保留失败路径。 | `Checkpoint`、`restarts_from`/`reuses_valid_artifact` edges、D2 trace | 单一故障注入；不撤销不可逆操作，也不称学习或自我进化 | D3 增加少量自然发生故障与恢复范围对照 |
| `C1-CTRL-01` | design-frozen-support | 检查由角色责任、运行时固定规则、按需且无执行权限的临时审核器与系统外独立评测分层承担，不默认增加常驻审核 Agent。 | scope gate、module map、validation ladder、D1 asset map | 执行前/后/结束时的检查尚未统一；临时审核触发条件未实现 | D2 检查记录 + 标准答案不泄露测试；若比较审核器，单列对照 |
| `C1-CTRL-02` | implemented-interface | 角色分工不等于权限；Agent 提出动作，运行时以版本化规则记录允许或拒绝，唯一 Executor 才真实执行。 | selector/executor split、18-tool effect table、`LocalPermissionPolicy`、D2 deny fixture | 当前 policy 只覆盖本地路径与 18 工具；无企业身份、确认流程或隔离 | D3 验证 Executor 接口调用；生产权限延后 |
| `C1-BOUNDARY-01` | accepted-framing | 第一章保证工作流安全、完整、可追溯地运行并承担检查点恢复；第二章判断方法与结论为何需要修改并输出有依据的行动义务；第三章在系统外独立评价结果、过程和用户效用。 | module continuity map、validation ladder、thesis state、researcher clarification 2026-08-11 | 通用工具底线与任务特定科学判断仍需在实现和实验中按此边界审计 | D2 只实现运行边界；第二章约束复用第一章恢复接口；第三章保持标准答案隔离 |
| `C1-EFF-01` | pending | 不得使用“adaptive trace-native execution 提高了真实 LLM 任务可靠性”。 | matched design only | 没有 static-vs-adaptive live run | 固定角色/模型/工具/预算的 matched experiment + error analysis |
| `C1-EFF-02` | prohibited | 不得使用“多智能体普遍优于单智能体”。 | 无当前新证据 | agent count 与 method factor 混杂 | 独立 matched factor study，若确有必要 |

## 引用格式示例

PPT 页脚：`Claim C1-METH-03 | engineering_support + diagnostic_evidence | scope: unique missing output only`

论文工作稿批注：`[C1-EFF-01: pending — do not promote before P0–P3]`

面试口头表达不必念 ID，但准备稿应保留 ID，确保长短版本来自同一事实源。
