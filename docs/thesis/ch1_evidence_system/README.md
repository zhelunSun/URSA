# 第一章演化与证据系统

> **2026-09-09 操作入口校准：**正式工作副本为 `D:/Projects/phd-thesis/URSA`；
> `D:/Projects/phd-research/ch1-agent-workflow` 仅作恢复比较。冻结研究基线为 v0.5.3；
> `codex/ch3-domain-toolchain` 开发分支为 v0.5.4.dev0，阶段范围见 [领域工具链](domain_toolchain_stage.md)。
> 北京离线产品链的完成情况和可复核证据见 [阶段验收](audits/20260909_domain_toolchain_closeout.md)。
> 后续工作入口：[能力校准与下一里程碑](industrial_calibration_20260909.md)、[通用 Agent 比较准备](comparison_preparation_20260909.md)。
> 当前推进顺序以 [09-10 知识接线预留与验证设计](validation_design_20260910.md) 为准：知识模块暂不接入，先做公共任务包、对照设计和无 API 准备检查。
> 原型、升级与新领域链的实战证据分开定位，见 [实验谱系与当前 Flash 检查](experiment_lineage_20260909.md)。
> 本轮代码、环境、实验可用性与后续操作见 [系统检查](audits/20260909_repository_system_check.md)。
> 9 月 7 日会后分工以总控 `THESIS_STATE.md` 为准：第一项承担需求解析与工作流方法，
> 第二项承担知识表示与推理，第三项承担领域系统构建与应用验证；下方旧三章分工保留历史语境。
> 历史 5×3 数字目前可追溯到 Git 摘要，但索引中的原始运行包在本次检查的两个副本中缺失，尚未复核其 checksum。

研究者随后要求梳理第一章方法与第三章系统的概念分工，并先做必要准备：
见 [内容分工与系统接入准备](ch1_ch3_system_preparation.md)。保持代码可复用，第三章继续补齐领域能力；
该文是实施建议和只读检查回执，不替代正式提纲或总控日程。

> 稳定入口；用于开题报告、论文写作、答辩 PPT 和技术面试。这里管理的是“事实如何变成可防守叙事”，不是另一份项目计划。

## 人类快速面板

| 项目 | 当前结论（2026-08-27） |
| --- | --- |
| 一句话主线 | 面向非遥感专业用户的开放式城市森林需求，构建能够保持用户意图、组织专业数据与工具，并依据运行反馈可靠完成任务的多智能体遥感工作流 |
| 三个候选创新 | ① 可调整的分层规划；② 随执行更新的过程图；③ 基于检查点的局部恢复 |
| 最小架构图 | 只维护三张：系统模块概念图、多智能体责任图、规划—执行—反馈—恢复闭环图；唯一源见 `module_continuity_map.md` |
| 已经做成 | 唯一 run/resume、真实模型结构化 planned graph、plan-bound action、规则/权限/预算、真实工具 observation、Scientist 局部重新授权、planned/observed graph、运行内 checkpoint、交付义务与报告闭合 |
| 已有初步实验 | v0.5.3 主/clean 环境 121/121；最终 v2 5×3 为 15/15 evaluator closure；另有 rule/live UserAgent clarification-resume smoke |
| 还没有做成 | 规划优越性和 checkpoint 独立效应、科学/空间结果精度、跨任务/跨传感器泛化、进程沙箱、durable recovery 与生产级通用 Harness |
| D1 结论 | 主线代码继续使用；旧运行时旁支只借少量编号、清单和调用统计；不合并固定六步流程，不增加审核/报告 Agent，不采用旧波段规则 |
| 当前决定 | v0.5.3/`0efd090` 作为冻结研究基线；当前转入章节写作、三张图、结果可视化和面试表达，不整体迁移 DeepSeek Harness |
| 明确延期 | 新 Agent、完整企业权限、容器/云部署、遥感服务标准接入、跨系统 Agent 通信、分布式运行时 |

三章边界：第一章保证工作流能够安全、完整、可追溯地运行；第二章判断方法与结论是否有科学
知识和证据依据；第三章独立评价完整系统在真实任务和用户层面是否可靠、有用。

人类阅读顺序只需：本面板 → `ch1_v053_draft.md` → `module_continuity_map.md` → `narrative_cards.md`。需要审计某个 claim 时，
再进入 architecture/claim/evolution/audits；不要求日常通读全部文件。

## 总 Idea 仓库对接清单

`research-harness` 只保存跨仓指针和人工接受后的证据状态，不复制本目录内容。总库访问第一章时
按用途读取以下稳定文件：

| 用途 | 首选文件 | 状态与边界 |
| --- | --- | --- |
| 更新中文大论文提纲 | [`ch1_v053_draft.md`](ch1_v053_draft.md) | 写作骨架；不单独晋级 claim |
| 理解领域动机与系统演化 | 本文件、[`module_continuity_map.md`](module_continuity_map.md) | User-centric RS → URSA Harness；三张图语义主源 |
| 制作 PPT/面试陈述 | [`narrative_cards.md`](narrative_cards.md) | 30 秒、90 秒、五页骨架与常见追问 |
| 引用实验数字 | [`v053_results_table.md`](v053_results_table.md) | 只报告冻结 5×3 的终态、token、wall time 与 claim boundary |
| 定位运行与 checksum | [`v053_evidence_index.md`](v053_evidence_index.md) | v0.5.3 evidence package 的权威指针 |
| 审核允许/禁止表述 | [`claim_registry.md`](claim_registry.md) | 使用稳定 claim ID；先看当前状态和限制 |
| 审核架构—代码—证据关系 | [`architecture_claim_matrix.md`](architecture_claim_matrix.md) | 顶部为当前状态；D1/D2 长表为历史 provenance |
| 获取图源与渲染件 | [`figures/README.md`](figures/README.md)、[`figures/out/`](figures/out/) | 三张系统图；当前为开题/PPT 可用草案，终稿仍需版面检查 |
| 查看完整开发边界 | [`PLAN.md`](PLAN.md) | 工程计划与长期 backlog；不是明日写作入口 |

从总 Idea 仓库进入时只需要
`research-harness/thesis/README.md → 本清单 → 对应材料`。若只准备开题，默认读取前六行，不扫描
raw runs、历史 audit 或 `PLAN.md` 全文。

`D1/D2/D3` 只是执行阶段编号，不是研究概念：D1 是资产盘点，D2 是无 API 最小贯通，D3 是
真实模型对照。以后人工汇报首次出现这些编号时必须同时写出中文含义。

### 三个候选创新的白话定义

1. **可调整的分层规划**：Scientist 先提出总体方向和当前阶段计划，不要求一开始把全部步骤
   写死；看到真实数据和工具结果后，可以有理由地修改后续计划。
2. **随执行更新的过程图**：系统把“原计划、实际做了什么、得到了什么、哪里失败、为什么
   改道”逐步画成一张图。这张图主要用于检查、解释和继续思考，不是预先限制 Agent 的剧本。
3. **基于检查点的局部恢复**：某一步失败时，保留此前已经确认有效的数据和结果，从最近的
   安全位置换一条路继续，而不是全部重做；也不假装能撤销已经发生的外部不可逆操作。

三者不能混为一张“万能图”：分层规划面向未来，回答“接下来准备怎样做”；过程图面向已经
发生的事实，回答“实际做了什么、为何改道”；检查点回答“失败后从哪里安全继续”。过程图可以
把计划版本也画进去，并把当前相关信息反馈给 Scientist，但它不替 Scientist 规划。

分层规划默认只包含“总体目标—当前阶段—下一动作”三个尺度，不等于蒙特卡洛树搜索。只有
真实反馈表明当前路径失败时，D2 才生成一条替代路径；MCTS/LATS 等多候选搜索只保留为未来
对照，不进入当前实现。

### 术语使用规则

- 论文、计划、PPT 和人工审批一律先使用上述中文名称；英文只在首次出现时放入括号；
- `ReAct`、`checkpoint` 是已有领域术语，可以保留，但必须解释其在本项目中的具体含义；
- `EventLedger`、`RunGraph`、`materializer`、`policy hook` 是本轮讨论中形成的**项目内部实现
  代号，不是公认的论文概念**。它们不得出现在人工审批和核心贡献表述中；
- 技术文档分别把这些代号写成“按时间追加的运行记录”“随执行更新的过程图”“把记录自动
  整理成图的程序”“权限检查接口”；
- 如果一个新词不能用一句普通中文解释清楚，就不能进入方法主线，只能留在代码注释或技术附录。

### D2 已获认可的三条原则

1. 运行中发生过的事实按时间保存，后来的成功不能覆盖前面的失败；
2. 给人和 Agent 看的过程图由这些事实自动整理出来，不反过来成为一开始就写死的流程；
3. D2 先做一个无 API 小样：一次工具反馈引起计划修改、一次失败从安全位置换路、一次越权
   动作被拦下；成功后才讨论真实 LLM。

研究者不需要审批具体类名、JSON 字段、图数据库或云框架。

研究者已于 2026-08-10 表示三条原则没有实质问题。2026-08-11 的 closeout 已证明三个机制在
无 API、真实工具故障小样中可以运行；这仍不等于真实模型效果已经证明。

## 为什么需要这个系统

第一章经历的不是简单代码累加，而是三种变化同时发生：原型工程逐步规范化、系统设计从隐式对话升级为由真实观测驱动的可调整执行、论文 claim 从“能运行”收窄为“过程可检查、失败可恢复、结论有证据边界”。原有的面向用户自然语言遥感分析主线不变；新增 runtime 只为 Manager、Scientist、Engineer/Executor 提供共享控制与证据环境。如果只保存最终代码，会丢失研究问题如何形成；如果只保存故事，又容易把 pilot 或设计意图当成效果证据。

本目录固定使用以下链路：

```text
Git / notebook / tests / raw traces / primary literature
                    ↓
       machine-generated repository snapshot
                    ↓
              evolution ledger
                    ↓
          architecture & claim matrix
                    ↓
    proposal / thesis / PPT / interview narrative cards
                    ↑
          independent audit and counter-evidence
```

## 文件职责

| 文件 | 唯一职责 | 更新时机 |
| --- | --- | --- |
| [`snapshots/current_repository_snapshot.md`](snapshots/current_repository_snapshot.md) | 自动记录 HEAD、工作树、notebook 哈希、实现表面和数据语义检查 | 每次准备写作或重要演示前 |
| [`evolution_ledger.md`](evolution_ledger.md) | 保存接受后的历史阶段、设计转折和证据等级 | 新里程碑被接受后 |
| [`module_continuity_map.md`](module_continuity_map.md) | 固定 Data–Tools–Brain 与 runtime/evaluation 的继承关系 | 章节模块或图示变化前 |
| [`validation_ladder.md`](validation_ladder.md) | 区分系统 validator、工程测试、历史 benchmark 和正式实验 | 使用“验证/可靠性”措辞前 |
| [`scope_gate.md`](scope_gate.md) | 第一章唯一科学问题、准入规则、停止扩张和人工门禁 | 接受任何新功能或实验前 |
| [`architecture_claim_matrix.md`](architecture_claim_matrix.md) | 把架构对象映射到代码、测试、外部重叠和允许/禁止 claim | 方法或实验边界变化后 |
| [`claim_registry.md`](claim_registry.md) | 为可复用句子分配稳定 claim ID，并记录支持、反证和晋级门槛 | 任何对外表述变化前 |
| [`narrative_cards.md`](narrative_cards.md) | 从同一事实源派生不同长度的开题、论文、PPT、面试表述 | 上游矩阵变化后 |
| `audits/` | 保存独立审计、反对意见、证据降级与处理状态 | 每个里程碑 Gate 前 |
| `architecture_decisions/` | 记录会改变系统边界的取舍，避免只凭聊天回忆 | 架构分叉或合并前 |
| `templates/` | 六格升级卡与 evidence manifest 的可复制空白模板 | 新功能、实验或叙事节点开始时 |

## 统一证据词汇

所有材料只使用四种 evidence role：

1. `prior_published_evidence`：已发表 ExpertsRS 的历史可行性证据；
2. `engineering_support`：代码、单测、接口和可复现运行；
3. `diagnostic_evidence`：scripted pilot、smoke run、错误注入和 trace；
4. `formal_effect_evidence`：匹配条件、预注册指标或等价严格设计下的 P0--P3 结果。

资产状态必须单独记录为 `tracked-main`、`untracked-worktree`、`side-branch` 或 `generated-ignored`。实现存在不等于证据有效，证据有效也不等于具有科学增量。

## 使用方法

### 写开题或论文

先读 evolution ledger 确定历史事实，再从 claim matrix 选择允许表述，最后使用 narrative card。不要直接从 README、代码量或一次成功运行推导创新点。

### 做 PPT

使用 narrative cards 中的“五页骨架”，每页页脚保留 evidence role。方法页可以画完整 pipeline；结果页只能展示该次证据实际覆盖的部分。

### 准备面试

使用 30 秒和 90 秒卡片，并优先讲一次真实的设计纠偏：例如独立审计发现“物理波段编号与栈内位置混淆”，因此把 pilot 从科学正确性证据降级为集成 smoke。这个例子比泛泛声称“做了多智能体系统”更能证明工程判断和科研诚实。

## 刷新流程

从仓库根目录运行：

```powershell
python scripts/ch1_materials_snapshot.py
```

然后依次执行：

1. 检查 snapshot 中的工作树、notebook 和 semantic check；
2. 只有在新事实可复现后才更新 evolution ledger；
3. 只有在证据角色升级后才修改 claim matrix 和 registry；
4. 让独立审计检查最强反例；
5. 最后更新 narrative cards。

## 文档维护协议

为了避免每次研究路线调整都新建一批 `latest`、`roadmap` 或 `handoff` 文档，本目录采用“稳定文件、原位更新、历史入账”的规则：

1. 科学问题和停止扩张只改 `scope_gate.md`；架构关系只改 `module_continuity_map.md`；
2. 可辩护 claim 依次落入 `architecture_claim_matrix.md`、`claim_registry.md` 和 `narrative_cards.md`；
3. 只有已经接受且能明确区分“实现、诊断、效果”的阶段，才追加到 `evolution_ledger.md`；
4. 只有真正改变系统边界的选择才新建 ADR；审计与运行结果保持追加式，不覆盖反证；
5. 第一章相关文献统一进入 `architecture_claim_matrix.md` 的外部重叠表，不另建文献清单，也不把论文元数据堆入 claim registry；
6. machine-readable JSON 是执行资产，不是研究者审批界面；需要人工决策时，先提供忠实的中文摘要、建议批复和影响范围。

除模板规定的审计或 ADR 外，不再为同一主题新增并行方法文档。跨仓库同步必须先在这里完成一致性检查，再更新总库的当前执行计划和正式 idea 版本。

## 当前人工门槛

截至 2026-08-27，v0.5.3 已把 typed planned graph 与真实模型决策、plan-bound action、真实工具
observation、Scientist revision、observed graph、运行内 checkpoint 和 delivery closure 接入统一
runtime。最终代码基线为 `0efd090`；主环境与 clean-venv 均为 121/121，最终 v2 5×3 为 15/15
evaluator closure。这个结果证明冻结条件下的运行、正确停止、澄清和局部恢复证据可以闭合，不能
推导规划优越性、checkpoint 独立效应、行政区绿地覆盖率、主题精度或跨任务泛化。

当前状态统一写成：

> **URSA 已从 conversation-oriented prototype 演化为 domain-specific、evidence-first research
> harness；第一章工程与初步集成证据已收口，下一步重点是科学问题、章节文本、三张图、结果图和
> 面试叙事，而不是继续扩建通用平台。**

当前人工 Gate 是确认章节主问题、贡献层级和可视化草案。任何新增 live 实验、工具、角色、长期
记忆、通用插件、进程沙箱或框架迁移都不自动启动；只有其能回答新的研究问题，并形成独立计划、
预算、版本和证据 Gate 后才实施。
