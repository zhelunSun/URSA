# 第一章 Claim Registry

> 稳定 ID 用于论文段落、PPT 页脚、答辩稿和实验 manifest。引用 claim 时同时写 evidence role。

| Claim ID | 当前状态 | 允许使用的句子 | 支持证据 | 主要反证/限制 | 晋级门槛 |
| --- | --- | --- | --- | --- | --- |
| `C1-ARCH-01` | accepted-framing | 第一章继承 User-centric RS 与 Data–Tools–Brain；runtime 是三类角色共用、连接 Brain 计划、Tools effect 与 Data/observation/artifact 的控制与证据外壳，不是新 Agent 或第四概念模块。 | published framework、module continuity map、ADR-001、v0.5.3 live pilot | 已接入统一 live runtime，但不等于通用/生产级 Harness | 作为架构叙事，不升级为效果 claim |
| `C1-HIST-01` | supported-prior | 已发表 ExpertsRS 证明了多智能体辅助非专家完成遥感分析的初步可行性。 | paper、两案例、20-request benchmark | 小样本、单场景、不能证明新机制 | 不升级；始终作为 prior evidence |
| `C1-ENG-01` | supported-local | 已将现有遥感能力收束为 18 个注册工具和统一调用表面，并用 callable-signature test 防止 adapter 漂移。 | `tools/`、registry、13 tool checks、signature contract test、Chapter 1 baseline commits | 依赖未完全锁定；尚无公开 release tag | 完整环境锁定 + release provenance |
| `C1-METH-01` | supported-live-structure | 已实现 `TaskSpec`、`OperatorSpec`、artifact contract 与版本化工作流图；v0.5.3 中真实 Scientist 能生成完整 planned graph，runtime 独立验证后执行。 | `workflow/specs.py`、`planning.py`、`graph.py`、0efd090 live runs、tests | 只覆盖冻结工具与任务；不证明模型规划质量更优 | 扩展任务族前先完成正式 baseline/ablation |
| `C1-METH-02` | implemented-narrow | validator 能确定性发现当前编码的结构/类型/顺序/文件/输出、required-band、required-config、交付义务与 output-contract violation。 | `validator.py`、v2 evaluator、121-test closeout | CRS/transform 仍有部分在工具层检查；graph-level extent/resolution/QA 与参数范围未系统覆盖 | 按正式任务的 failure family 增补，不追求穷举规则 |
| `C1-METH-03` | implemented-narrow | 对一个唯一安全的缺失输出，prototype 可只补受影响步骤；不安全时显式停止。 | `repair.py`、repair/stop traces | 不是一般 repair；unaffected graph test 不完整 | real ambiguity、graph diff invariant、LLM failures |
| `C1-OBS-01` | supported-live | 系统以稳定引用记录计划版本、权限、动作、反馈、产出、检查点与结局，并分别持久化 planned graph 与从 trace 重建的 observed graph。 | `trace.py`、`runtime.py`、0efd090 trace/graphs、v2 evaluator、tests | append-style JSONL 不是 durable event store；没有跨进程 replay/recovery | 仅在 Chapter 3 需要时增加 portable trial export |
| `C1-SYS-01` | supported-live-integration | 统一 `run()/resume()` runtime 已贯通真实模型结构化计划、plan-bound action、真实工具反馈、Scientist revision、检查点复用、交付闭合与诚实终态。 | 121/121 regression、0efd090 v2 5×3、v2 evidence index | 5×3 是单轮小规模集成 pilot；不证明机制效应、科学准确性或跨任务泛化 | 正式 baseline/ablation 与 Chapter 3 外部验证 |
| `C1-SCI-01` | diagnostic-supported | scripted pilot 已按 metadata 把 B8/B4 解析到栈内 7/3，并保持 nodata/class count 不变量，可作为真实工具科学语义前置条件的诊断证据。 | 10 scientific tests、pilot trace、ADR-002 | threshold=0.3 未校准；无 thematic gold；仅单场景 scripted run | independent gold + task-level scientific review；效果 claim 仍需 P0--P3 |
| `C1-DESIGN-01` | supported-live-mechanism | 第一章只保留三个研究对象：可调整的分层规划、随执行更新的过程图、基于检查点的局部恢复；三者已进入统一 live runtime。 | researcher decision、scope gate、ADR-001、0efd090 trace/graphs | 只证明机制在冻结小样中贯通，不证明优于静态或旧对话流程 | 正式机制对照 |
| `C1-DESIGN-02` | supported-live-mechanism | 规划表示接下来准备怎样做，执行表示实际做了什么；历史计划和失败事实不被后续成功覆盖，observed graph 由 trace 重建。 | plan versions、trace、planned/observed graphs、alignment checks | 当前图主要服务审计；没有证明图反馈提高模型决策质量 | 过程图可用性或规划质量对照 |
| `C1-DESIGN-03` | supported-live-narrow | 局部恢复只表示从运行检查点复用已验证产出并对受影响分支重新授权；task-11 保留失败 observation 并复用 NDVI 产物。 | 0efd090 task-11 B2/B3、checkpoint refs、graph diff | 单一批准故障；`local_reauthorization_only`；不撤销不可逆操作 | 增加故障家族并隔离 checkpoint 独立效应 |
| `C1-CTRL-01` | implemented-support | 检查由角色责任、运行时固定规则和系统外独立评测分层承担，不默认增加常驻审核 Agent；执行前、执行后和结束闭合已有统一记录。 | scope gate、module map、runtime、v2 evaluator、leakage tests | 未实现通用语义审核器；系统规则不能替代科学判断 | 若研究审核器，作为独立实验条件而非默认角色 |
| `C1-CTRL-02` | implemented-interface | 角色分工不等于权限；Agent 提出动作，运行时以版本化规则记录允许或拒绝，唯一 Executor 才真实执行。 | selector/executor split、18-tool effect table、`LocalPermissionPolicy`、D2 deny fixture | 当前 policy 只覆盖本地路径与 18 工具；无企业身份、确认流程或隔离 | D3 验证 Executor 接口调用；生产权限延后 |
| `C1-BOUNDARY-01` | accepted-framing | 第一章保证工作流安全、完整、可追溯地运行并承担检查点恢复；第二章判断方法与结论为何需要修改并输出有依据的行动义务；第三章在系统外独立评价结果、过程和用户效用。 | module continuity map、validation ladder、thesis state、researcher clarification 2026-08-11 | 通用工具底线与任务特定科学判断仍需在实现和实验中按此边界审计 | D2 只实现运行边界；第二章约束复用第一章恢复接口；第三章保持标准答案隔离 |
| `C1-EFF-01` | live-integration-supported-effect-prohibited | 可以说真实模型 5×3 pilot 的 15 个槽均达到 v2 evaluator closure；不得据此说“自适应执行提高了任务可靠性”。 | 0efd090 15-slot pilot、v053 results/evidence index、5/7/3 终态、cost table | 单轮、小任务集、非独立机制效应设计；不同终态的 closure 不是成功率 | 正式 baseline/ablation、多重复与 error analysis 后再判断效应 |
| `C1-EFF-02` | prohibited | 不得使用“多智能体普遍优于单智能体”。 | 无当前新证据 | agent count 与 method factor 混杂 | 独立 matched factor study，若确有必要 |
| `C1-V2-01` | supported-live | runtime-owned obligation 将 task-11 的专题图与受限比例独立闭合，NDVI 图不能替代专题图。 | `v053_evidence_index.md`、0efd090 pilot、v2 evaluator | 单场景、固定阈值；不验证行政区分母或主题精度 | 独立 AOI/行政区与科学验证 |
| `C1-V2-02` | supported-live-narrow | task-11 在 observation 后由 Scientist 局部重新授权执行。 | 0efd090 B2/B3 trace、graph diff | diff 为 `local_reauthorization_only`，不支持规划优越性 | matched planning-quality study |
| `C1-V2-03` | supported-fixture | 一次澄清可由隔离 profile 回答并经 `.resume()` 完成。 | `v2_user_agent_smoke_bb7c8bf` | 不是用户研究、不是第四角色 | 伦理批准的用户研究 |
| `C1-V2-04` | supported-live-integration | v0.5.3 在主环境和 clean venv 完成 121/121 回归；最终 v2 5×3 为 15/15 evaluator closure，终态分布为 5 completed、7 controlled-stop、3 needs-clarification。 | closeout manifest、`v053_results_table.md`、`v053_evidence_index.md` | closure 衡量协议与证据闭合，不是科学正确率、用户效用或规划优越性 | Chapter 3 独立任务、grader 与用户层验证 |

## 引用格式示例

PPT 页脚：`Claim C1-METH-03 | engineering_support + diagnostic_evidence | scope: unique missing output only`

论文工作稿批注：`[C1-EFF-01: live integration only — do not promote before formal baseline/ablation]`

面试口头表达不必念 ID，但准备稿应保留 ID，确保长短版本来自同一事实源。
