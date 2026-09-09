# 第一章收敛执行计划：冻结 v1 证据 → v2 最小工程闭环 → 开题文本

> **2026-09-09 已授权开发阶段：**研究者要求复用既有 runtime/tool 架构推进第三章准备并检查潜在问题。
> 独立分支 `codex/ch3-domain-toolchain` 的 [阶段目标](domain_toolchain_stage.md) 为同一入口的离线北京产品描述链；
> v0.5.3 基线/历史包保持，当前阶段不是 live 自主能力、知识方法效果或第三章系统比较。

> **2026-09-09 当前执行覆盖说明：**v0.5.3 已完成结构化计划接入和历史最终 5×3 pilot；
> 本轮正式副本回归为 121/121，M1、D2 与离线 CLI 均通过。§1–5 中“尚待 v2 接入”、
> 107/101 项测试及 WP 待执行文字属于 2026-08-18 的历史检查点，不应重新派发。
> §12 的 v0.5.3 完成记录及本轮 [系统检查](audits/20260909_repository_system_check.md) 优先。
> 当前第一项承担需求解析、规划与反馈调整/恢复的方法验证；第三项已转为领域系统构建与应用验证，
> 以总控决定为准（入口见下方链接）。
> [总控状态](../../../../research-harness/THESIS_STATE.md)与
> [09-07决定](../../../../research-harness/decisions/DEC-2026-0907-post-advisor-system-integration.md)
> 覆盖旧章节分工及日程。下一步优先定位历史运行包并按既有 checksum 核验，同时沿总控现有写作任务复用架构材料；
> 不重跑 live 来替代缺失历史证据，不自动启动 §13 的长期架构 backlog。新方法匹配实验仍待有界设计与研究者决定。

> 状态：active；v1 保持历史冻结证据，v0.5.3 审计缺口收口与最终 v2 5×3 已完成；后续转入架构表达与渐进升级
> 决策日期：2026-08-13；最近更新：2026-08-25
> 所属分支：`codex/ch1-v2-e1-structured-planning`
> 唯一实现入口：`ExpertsRSSystem.run()` / `.resume()` 与 `python -m ExpertsRS`

## 1. 本阶段只回答什么

第一章不再以“建设通用 Agent 平台”为目标。其研究问题固定为：开放的遥感需求能否通过
**可调整的分层规划、随执行更新的过程图、基于检查点的局部恢复**，在真实工具反馈出现后
更好地完成、改道、停止和留下可审计证据。

本阶段把两个不同目的明确分开，避免用“毕业时最好达到的完整度”阻塞当前开题：

1. **目标 A：开题/九月中旬前的最小闭环**。形成一套结构闭合、可演示、可追溯的系统架构；
   将已发表 ExpertsRS 的 20-request 人工评审结果作为历史可行性证据；保留 v1 真实模型 matched
   pilot，并完成一次针对审计缺口的 v2 最小工程收口；若成本允许，再用原 20 条请求形成一轮自动化
   轻量闭环。目标 A 不要求稳定统计效应、跨模型泛化、逐条新增人工评审或完整用户研究。
2. **目标 B：毕业论文或新论文级完整验证**。在 held-out 任务和多类故障上隔离结构化规划、
   observation-driven revision 和 checkpoint recovery 的增量，进行重复实验、外部评分校准、
   科学/空间结果核验和跨数据泛化。目标 B 是后续研究主线，不是当前开题阻塞项。

截至 2026-08-18，方法基线、真实模型 smoke、首轮 5×3 pilot 和运行包真实性审计已经完成，目标 A
的证据底座已经形成。审计同时确认：执行控制与审计底盘真实存在，但 live Scientist 目前主要生成
`operation + next_action`，尚未把完整 `TaskSpec/OperatorSpec/WorkflowGraph` 接入实际决策—执行链；
process graph 主要由事实事后重建。因此当前优先级不是继续横向扩平台，而是先完成一个有界的 v2
工程收口，再封存证据、制作图表并写文本。方法/架构文本现在即可起草，最终实验数字在 v2 冻结后落定。

## 2. 已冻结的架构决定

1. 新系统目标只有一条权威链：`RunRequest → Manager → Scientist → runtime → Engineer →
   Executor → observation → revise/continue/stop → Manager report → RunResult`。
2. Manager、Scientist、Engineer 是模型角色；Executor 是受权限和合同控制的确定性服务。
3. runtime 独占计划版本、预算、权限、产物、检查点、运行记录和终态；AutoGen 只管理角色
   对话与可移植 team state。
4. `ExpertsRS_notebook.ipynb` 与 AG2/StateFlow 保持为历史复现入口，不被新包导入，也不要求
   与新系统双向功能等价。
5. 第二章只能通过科学约束接口影响 `revise/add-validation/ask/reject/downgrade/escalate`
   等动作义务，不能另建调度器或直接执行工具。
6. 第三章只消费 `RunRequest/RunResult/trace/artifact`，gold、评分器和故障注入留在系统外部。
7. 第一章只承诺运行内的逻辑检查点恢复；进程崩溃后的通用 durable recovery 不进入第一章
   方法 claim，作为跨章节底盘加固另行验收。
8. v2 必须区分 **Scientist 提出的 planned workflow graph** 与 runtime 根据事件生成的
   **observed process graph**；前者约束可执行节点，后者只负责审计，二者不得再用同一“规划图”表述。
9. AI 用户代理只模拟用户 profile、澄清回答和对最终报告的可用性评价；它不生成科学 gold、不替代
   原论文领域评审，也不得接触 evaluator-private 预期答案。

## 3. 当前证据等级（2026-08-18）

| 项目 | 状态 | 可支持 | 不可支持 |
| --- | --- | --- | --- |
| 已发表 ExpertsRS | prior published evidence | 多智能体遥感分析的历史可行性和问题来源 | 新机制效果 |
| 统一 `run/resume` 链 | engineering support | 新系统已有唯一输入输出载体和模型—工具—反馈—报告闭环 | 方法效果 |
| 107 项完整测试、101 项 clean-venv、90% 控制面/evaluator coverage | engineering support | 软件合同、provider、工具和关键失败路径可复核 | 科学效果或外部有效性 |
| NDVI/澄清/停止/恢复离线场景 | diagnostic evidence | 机制能被真实本地工具贯通 | LLM 自主决策质量 |
| 5 任务 × 3 条件离线预飞行 | diagnostic evidence | evaluator 已经通过统一 API，三条件可控 | 条件间效果差异 |
| S1–S3 真实模型 smoke | completed integration evidence | 普通完成、故障恢复、模糊需求澄清三条 live 路径可运行 | 稳定性或一般化 |
| 5×3 真实模型 pilot | 15/15 protocol/evaluator closure | 冻结系统可在有界资源内形成可审计终态；task-11 出现自适应恢复信号 | 稳定机制效应、B3 相对 B2 的增量、科学/空间准确性 |
| v1 真实性审计 | completed | 15 个 trial 槽位、模型角色调用、工具调用、artifact、trace、plan version、checkpoint 和 observed graph 均有实体证据 | live 完整分层规划已经实现 |
| pilot outcome 分析 | completed-initial / claim-safe | 唯一故障任务中 B1 停止而 B2/B3 恢复；四个边界任务行为一致 | “规划总体提升”或“checkpoint 已证明更优” |
| v2 最小工程闭环 | completed (v0.5.3) | runtime-owned delivery obligations、专题图语义、报告闭合、隔离 UserAgent loop、新版 evaluator 与最终 5×3 live 复验 | 不支持规划优越性、行政区覆盖率、用户研究或 durable recovery |
| 科学适用性与主题精度 | open，转交 Ch2/Ch3 | — | 当前第一章不得借系统工件自动声称科学正确 |

因此，当前对外阶段名统一使用：

> **第一章已形成真实可复核的执行控制与审计底盘，并完成一次真实模型 5×3 集成 pilot。现有结果
> 提供自适应恢复的初步案例信号；完整结构化规划尚待 v2 接入，checkpoint 的独立收益和一般规划
> 效果也尚未识别。既有论文的人审证据、v1 工程事实和 v2 最小闭环共同支撑开题可行性，但不足以
> 升级为稳定效果结论。**

## 4. 当前检查点的验收标志

以下 v1 条件已经满足并冻结，不因 v2 修改而回写历史工件：

- `codex/ch1-unified-runtime` 明确从 `codex/ch1-baseline-20260811` 分出，历史 notebook 未改；
- 新系统只有一个 `run/resume` 权威入口；
- 完整测试 107 项通过，clean virtual environment 中 101 项 unittest 通过，控制面/evaluator
  branch-aware coverage 为 90%（门槛 85%）；
- CLI 可离线生成真实 NDVI 栅格、地图、报告、`state.json`、`trace.jsonl` 和 `result.json`；
- 澄清、科学前置条件停止、目录越界拒绝、故障后计划修订与检查点复用有显式测试；
- D3 evaluator 只注入条件和读取轨迹，不再替 Agent 预排角色或动作；
- S1–S3 live smoke 和 5×3 live pilot 已在冻结配置上运行并保留不可覆盖工件；
- 已明确记录科学正确性、稳定机制效应、耐久恢复和 18 工具完整 Agent 可达性等未通过项。

这些条件目前已经满足。当前可以称“方法基线 v1 + 真实模型集成 pilot + 真实性审计完成”，也可以
称“第一章开题级证据底座完成”；仍不能称“完整结构化规划已进入 live 链”“方法效果已充分证明”
或“系统整体通过”。v2 的停止条件另列在第 5 节，只修复影响架构叙事和轻量复验可信度的缺口。

## 5. Workhorse 执行看板

### 5.0 调度规则

WP1–WP4a、S1–S3、E1 5×3 和真实性审计已完成。第一章现在采用“v2 有界修复与文本并行”的节奏；
不等待新论文级实验才写作，也不把审计确认的架构缺口留到最终系统图之后。核心代码一次只允许一个
writer，任何新实验不得回写或覆盖冻结的 v1 pilot。

截至 2026-08-18 的执行状态：

| 工作包 | 状态 | 当前证据/决定 |
| --- | --- | --- |
| WP1 typed action contract | completed | 模型只提交符号动作，runtime 绑定参数、权限和真实工具 |
| WP2 live provider/identity | completed | offline/live 身份、provider 失败和用量记录显式化 |
| WP3 Manager report | completed | live/offline 共用结构化报告与 artifact 引用验证 |
| WP4a live gate | completed | 107 tests、clean-venv 101、90% coverage、泄漏与失败门槛通过 |
| S1–S3 live smoke | completed | Paratera `DeepSeek-V4-Flash` 三条固定路径通过；早期失败单独保留 |
| E1 5×3 live pilot | completed | 15/15 protocol/evaluator closure，166,400 tokens，346.7 s |
| E1 运行包人工检查 | completed（研究者确认） | 数据、产物和运行包已核验；不再安排笼统的重复人工复核 |
| E1 真实性与 claim 审计 | completed | 107 tests 重跑通过；真实 role/tool/artifact/trace/graph 已计数；live plan、report closure、state 脱敏缺口已定位 |
| V2-E1 live 规划闭环 | completed in v0.5.2; audited in v0.5.3 | 结构化多步计划接入 live；计划节点约束执行；失败回到 Scientist 修订；区分 planned/observed graph |
| V2-E2 报告与隐私闭环 | completed in v0.5.2; strengthened in v0.5.3 | 原始请求独立义务、task-11 专题图/比例语义、state 去除 ThoughtEvent、修正 revision actor attribution |
| V2-E3 验收与最终复验 | completed | 新离线 manifest、rule/live UserAgent smoke、最终 v2 5×3 已完成；20×1 取消 |
| 开题证据包与文本 | in progress | 架构/方法可立即写；最终结果表在 v2 复验后冻结；不需要 45-run 或完整用户研究 |
| WP4b / WP5 | deferred / optional | 非开题阻塞；只在不挤占写作或跨章接口确有需要时启动 |

当前推荐三条泳道：

| 泳道 | 当前工作 | 优先级 | 写入范围 |
| --- | --- | ---: | --- |
| A：v2 工程收口 | 完整计划接入、Scientist 修订、报告闭合、state 脱敏、强化 evaluator | P0 | 核心代码与测试；不覆盖 frozen runs |
| B：开题文本 | 架构/方法先写；既有成果映射、实验和限制随 v2 结果更新 | P0 | 论文/开题文档 |
| C：轻量复验 | v2 smoke 与 5×3 已冻结；原 20-request 只保留历史/admission benchmark，不启动 20×1 | completed / deferred | 现有新协议/新 run 目录；后续正式 benchmark 由 Chapter 3 另行立项 |

分支和合入规则：

1. 每个 workhorse 从 `codex/ch1-unified-runtime` 的最新已接受 commit 新建自己的 `codex/ch1-wpN-*`；
2. 每次只领取一个 WP，不顺手实现下一个 WP；
3. WP1–WP4a 按编号审查并合入，后一个 WP 必须基于前一个已接受 commit；
4. 禁止修改 `ExpertsRS_notebook.ipynb`、`legacy_requirements.txt`、原始 benchmark、
   `d3_light_panel_v1.json`、gold/expected outcome、`scope_gate.md` 和论文总控正式状态；
5. 若实现迫使改变 C1 claim、任务、条件、指标、预算或披露边界，停止编码并提交 proposal。

### 5.1 合入队列

| 顺序 | 包 | 阻塞关系 | 主要允许文件 | 合入产物 |
| ---: | --- | --- | --- | --- |
| 1 | WP1 动作合同 | completed | `models.py`、`decisions.py`、`system.py`、对应新测试 | typed decisions + runtime/tool binding |
| 2 | WP2 live provider | completed | provider/config、CLI、核心文件与测试 | 显式 offline/live 身份和失败语义 |
| 3 | WP3 Manager 报告 | completed | 核心文件、报告测试 | 同一报告合同和 artifact 引用校验 |
| 4 | WP4a live gate | completed | 测试、coverage、最小缺陷修复 | critical edge tests、clean venv、90% 控制面/evaluator coverage |
| 5 | S1–S3 live smoke | completed | 不可覆盖 run 目录 | 3 个真实模型 smoke 工件与 anomaly memo |
| 6 | E1 轻量 5×3 | completed | 不可覆盖实验目录 | 15 个 trial、程序化外部评分和批次汇总 |
| 7 | E1 truth/claim audit | completed | 文档、只读结果分析 | 真实运行计数、过度 claim 修正、v2 缺口清单 |
| 8 | V2-E1 structured live planning | current P0 | `models.py`、`decisions.py`、`system.py`、graph/validator 与测试 | planned graph 约束真实执行，失败由 Scientist 修订 |
| 9 | V2-E2 report/privacy hardening | P0 after V2-E1 | report/state persistence/trace 与测试 | 请求指标必须交付或显式 partial；持久化不含 ThoughtEvent |
| 10 | V2-E3 acceptance/replay | P0/P1 after V2-E2 | tests、evaluator、新 run 目录 | 离线全绿、3 smoke；按行为变化决定 5×3/20×1 |
| 11 | WP4b / WP5 / repeated study | deferred | 不改变 E1 冻结版本 | 毕业/论文级增强，不阻塞开题写作 |

下面保留 WP1–WP5 的验收合同作为实现历史和后续维护边界；WP1–WP4a 已完成，不按旧顺序重新执行。
下一位工程模型只领取 V2-E1，再顺序进入 V2-E2/V2-E3，不得把 WP4b/WP5 或跨章功能夹带进来。

### V2-E1：把结构化多步规划接入 live 链（当前 P0）

- Scientist 输出可验证的 `TaskSpec / OperatorSpec / WorkflowGraph`，而非仅保存
  `operation + next_action`；runtime 拒绝无依赖、类型、输入或可执行条件的非法计划；
- Engineer 只能执行 planned graph 中当前 eligible 的节点，工具 observation 必须回写对应节点状态；
- 工具失败或关键 observation 交回 Scientist 形成带原因、actor 和 patch 的 `PlanVersion + 1`；不得由
  runtime 把 Engineer 的 `revise` 自动记成 Scientist 决策；
- 分开导出 planned workflow graph 和 observed process graph，并建立 plan node ↔ action/event/artifact
  的稳定引用；
- 只扩充原 20-request 轻量复验所必需且已有安全参数绑定的工具；不以暴露全部 18 个工具为目标。

验收：新增多步计划 schema/validator、eligible-node enforcement、失败回到 Scientist、局部 patch、
planned/observed graph 对齐和 actor attribution 测试；现有 107 项回归继续通过。

### V2-E2：报告闭合与持久化隐私（P0）

- Manager 报告必须回答用户明确要求的数值、比率和 artifact；如果 denominator/AOI 语义未验证，必须
  报告限定口径或 `partial`，不能一边已有结果一边声称“未计算”，也不能无条件 `completed`；
- evaluator 增加 user-requested-output completeness、plan/action consistency、revision trigger、
  graph reference 和 false-success 检查；协议 PASS 与结果正确率分开；
- `trace.jsonl` 与可移植 `state.json` 均不得持久化 ThoughtEvent/chain-of-thought，只保留结构化决定、
  必要 observation、用量和可审计 provenance。

验收：task-11 比率/分母口径测试、缺请求输出时 partial/stop 测试、state/trace 泄漏测试和严格 evaluator
反例全部通过。

### V2-E3：无 API 验收与低成本复验（P0/P1）

1. 先运行全部单元/集成测试、clean environment、CLI、`compileall`、泄漏检查和 scripted 15-slot；
2. 通过后只授权 3 条 live smoke：普通多步完成、失败后 Scientist 修订、需要用户澄清；
3. 若 V2-E1/E2 改变规划、报告或终态语义，则 v1 结果继续标为历史 v1，并用新目录重跑 v2 5×3；
4. 若预算允许，再以**原论文 20 条精确请求 × v2 最终系统单条件**做 breadth closure；不把它包装为
   新 matched study，不要求每条件重复，也不追求发表级统计功效；
5. 20×1 默认程序评分 + AI 用户代理 + 风险抽样人工复核，细则见 6.4；不得让 AI 用户代理读取 gold。

### WP1：收紧模型动作合同（P0，阻塞 live）

目标：模型只能提出符号化动作，runtime 决定路径和真实参数。

- 增加有类型的 Manager、Scientist、Engineer、Report 决策模型；非法 JSON 必须形成可追踪失败；
- Engineer 动作为 `tool_name + artifact references + safe parameters`，禁止模型提交绝对路径；
- 模型可见工具集合必须与 runtime 实际存在的 `ToolBinding` 完全相等；不能继续“展示 18 个、
  实际只会拼 6 个参数”。本阶段采用**安全子集策略**：18 个注册工具继续作为 Tool 层资产，
  只有具备 runtime 参数解析和权限合同的工具才进入 agent-visible catalog；WP1 不以强行暴露
  全部 18 个工具为验收条件；
- 未知工具、未知参数、未知 artifact、重复失败必须有受控终态。

验收：新增非法 JSON、未知工具、参数越界、artifact 引用错误测试；相关 trace 不泄露本地路径。

交付约束：不得接 API，不改 CLI provider 选择，不改最终报告策略，不改 evaluator 条件。提交前运行
统一测试、`compileall` 和 `git diff --check`。

### WP2：建立显式 live provider 与实验身份（P0，阻塞 live）

目标：scripted 演示与真实 Agent 运行在结果中不可混淆。

- CLI/Python 配置显式选择 `scripted-offline` 或 `autogen-live`；
- 记录 provider、model、prompt hash、code commit、capability policy、预算和 execution mode；
- 实现 provider timeout、API 错误、非法响应、预算耗尽的明确终态，禁止静默换模型/样本；
- scripted 保持默认安全模式，但所有输出必须醒目标注，不能被描述为 live。

验收：无密钥时在网络请求前失败；超时/错误保留部分 trace；同一 scripted 输入可重复。

交付约束：不得真实调用 API；用 fake/scripted model client 覆盖所有 provider 分支。不得把密钥、
endpoint 或模型名写死在跟踪文件中。

### WP3：完成真正的 Manager 报告闭环（P1，阻塞“完整系统”演示）

目标：最终报告由 Manager 基于脱敏 observation 和 artifact manifest 生成，而不是 runtime 固定句。

- 增加结构化 `ReportDecision`；
- runtime 验证报告引用的 artifact 和终态；
- 报告失败时保留制品并返回明确的部分失败/失败终态；
- 离线 scripted provider 与 live provider 使用同一报告合同。

验收：成功、受控停止、报告生成失败、虚构 artifact 引用四条测试。

交付约束：报告只消费脱敏 observation、验证后的 artifact manifest 和明确终态；不得让报告角色
改写运行事实、补造产物或把 controlled stop 包装为成功。

### WP4a：live 实验前验证门槛（P1，阻塞 live）

- 控制面、状态转换、evaluator 分支覆盖率达到 85%；
- 补非法模型 JSON、未知工具、全局/角色预算耗尽、provider timeout/API 错误、工具异常、报告失败；
- 在新虚拟环境按 `pyproject.toml` 安装并执行统一测试、CLI 和 `compileall`；
- 运行脱敏/泄漏检查，确认模型上下文无绝对路径、raster、密钥、故障标记、gold 和评分合同；
- 生成带 git commit、provider/model、prompt hash、panel hash、预算与环境版本的候选 manifest。

验收：保存 coverage 报告和 clean-venv manifest；不以本机已有包代替依赖证明。

### WP4b：非实验阻塞的鲁棒性收尾（P2）

- 补损坏 state/result、多个输入、并发 run ID 和 artifact 被外部修改等测试；
- 修复当前 Matplotlib `get_cmap` 弃用告警，但不改变地图语义；
- 整理测试等级和“能证明/不能证明”的 README。

WP4b 不得在 E1 运行中修改被冻结的实验 commit。若 E1 已开始，只能在后续版本修复并另起实验。

### WP5：跨进程恢复与扩展接口（P2，不阻塞第一章 D3）

- 每次关键事件后原子保存 runtime state；损坏/不完整状态必须拒绝恢复；
- 保留 `.resume()` 处理用户澄清，另行定义清楚 crash recovery，不混淆两种语义；
- 冻结第二章 `ScientificConstraintPort` 与第三章 `EvalTask → TrialTrace → Outcome → Evaluation`
  接口版本。

验收：新进程恢复测试、状态版本迁移/拒绝测试、一个假科学约束 adapter、一个外部 evaluator。

非目标：Web/API 服务、UI、多租户、企业 IAM、分布式队列、自动下载数据、MCTS/LangGraph、
长期记忆、Agent RL、增加角色或扩大工具集合。

## 6. 真实模型实验状态、判读与双目标路线

### 6.1 已完成的运行

2026-08-14，Paratera `DeepSeek-V4-Flash` 在冻结 runtime/prompt commit `2aeecd3` 上完成一次
5 任务 × 3 条件的 live pilot；runner 审计基线为 `30c8075`。15/15 槽位完成并通过程序化外部
evaluator，总用量 166,400 tokens、总 wall time 346.7 s；API gate 随后关闭。此前 SiliconFlow
超时、Paratera 协议适配和早期 pilot 失败全部保留为 anomaly，不并入最终成功批次。

| 条件 | evaluator PASS | 真实终态 | tokens | wall time |
| --- | ---: | --- | ---: | ---: |
| C1-B1 static | 5/5 | 1 completed、3 controlled stop、1 clarification | 31,228 | 76.6 s |
| C1-B2 adaptive | 5/5 | 2 completed、2 controlled stop、1 clarification | 66,365 | 137.5 s |
| C1-B3 checkpoint | 5/5 | 2 completed、2 controlled stop、1 clarification | 68,807 | 132.7 s |

这里的 PASS 是**协议闭合**：运行到达该任务/条件允许的终态，留下要求的 artifact/trace/graph
证据。它不等于 15 个任务全部成功，更不等于主题精度或方法效应为 100%。

### 6.2 当前可以和不可以得出的结论

五个任务中，task-02 是正常 NDVI 完成，task-03 是缺工具停止，task-10 是缺热红外前置条件停止，
task-13 是指标定义澄清；这四个任务的三条件终态一致，主要验证系统边界和诚实闭合。只有 task-11
注入一次 threshold 写入失败并对恢复机制敏感：B1 在失败后受控停止，B2/B3 均形成 plan v2 并完成
后续 mask、map 和 area statistics。因此当前支持一个窄结论：

> 在一个受控的多步工具故障案例中，允许 observation-driven revision 的系统能够从失败后继续，
> 静态条件按合同停止；完整故障、修订和 artifact 轨迹可重建。

当前不能声称 checkpoint 已证明比普通自适应复用更优。task-11 的 B2/B3 都是 12 model turns、
7 tool calls、1 次 NDVI，实际工具序列相同；B3 增加了 checkpoint 和 `restart_from_checkpoint_id`
证据，但没有在本例中减少重算。B3 相比 B2 多 1,668 tokens，单次 wall time 反而短约 8 s，这些
单次描述量不能解释为稳定成本效应。

另一个必须显式保留的反例是：task-11 的 B2/B3 报告均说“green cover rate 未计算”，但 runtime
标为 `completed`，程序 evaluator 仍判 PASS。mask metadata 中存在相对有效像元的 40.76%，但当前
没有在第一章证明该分母严格等于行政区面积，也没有把该比率交付到最终报告。因此开题表格应把
这两例写为“运行/恢复闭合，用户目标闭合有保留”，而不是把它们宣传为无条件完整成功。

### 6.3 系统完善、实验与科学证据的关系

| 层次 | 回答的问题 | 当前状态 | 对开题的作用 | 对完整论文仍缺什么 |
| --- | --- | --- | --- | --- |
| 系统架构/工程证据 | 方法对象是否有唯一可运行载体、失败是否可见、证据是否可追溯 | 执行/审计较完整；完整 live 规划仍待 v2 | 支撑“研究可实施”和方法章节主体 | v2 planned graph 执行约束、Scientist 修订、报告/隐私闭合 |
| 第一章机制实验 | 新机制是否在匹配条件下改变规划/恢复行为 | 初步；一个自适应恢复信号，B3 独立增量未识别 | 作为 preliminary result 足够，必须限制 claim | held-out 多故障、真正能区分 B2/B3 的任务、重复与效应量 |
| 科学/空间结果证据 | 所选指标、阈值、区域和输出是否科学有效、空间准确 | 第一章刻意不评分；部分前置条件 fail closed | 通过边界说明避免过度主张 | Ch2 科学约束实验、Ch3 空间/任务结果 grader 和外部校准 |
| 已发表 ExpertsRS 证据 | 早期多智能体遥感系统是否可行、原问题从何而来 | 已有论文与 20-request 历史结果 | 可复用为 prior evidence 和演化起点 | 不能重标为当前机制的 matched effect |

系统成熟度是实验可信的必要底座，但不能替代机制效果；科学正确性又是另一层，不能由“工具成功”
自动推出。对开题，四层证据可以组合成“已有成果 → 明确问题 → 新架构 → 初步真实模型信号 →
后续可证伪计划”的完整故事。对新论文或毕业终稿，则必须补第二、三层的独立证据。

### 6.4 人工审核发生在哪一环，而不是“每次运行都人工盯着”

原论文的 20-request 实验已经包含领域研究者对规划过程和最终结果的人工评审，这部分继续作为已发表
历史证据，不需要为了扩充本章原样重做。当前应把三种容易混淆的人工工作分开：

| 环节 | 审核对象 | 本章默认做法 | 是否要求每条运行人工介入 |
| --- | --- | --- | --- |
| 运行前 gold/rubric 冻结 | 请求预期是执行、澄清还是停止；关键步骤、必需输出和科学边界 | 优先复用原 20 条请求及既有评审口径；新增/改变标签时由研究者一次性批准 | 否；这是数据集/评分合同审核，不是运行时操作 |
| 运行中用户交互 | 系统提出澄清问题后用户如何回答，以及不同用户 profile 的偏好 | 用隔离的 AI UserAgent 批量模拟；固定 profile、seed、预算和对话合同 | 否；只对少量异常交互抽查 |
| 运行后结果评价 | plan/result/report 是否正确、完整、可用 | 确定性 grader + AI judge 双轨；对失败、partial、grader 分歧和随机样本做人审 | 否；不要求研究者逐条看全部成功样本 |
| 学术结论与科学标签 | 指标/分母是否成立、claim 是否越界 | 研究者最终裁决 | 是，但只裁决少量有争议项，不参与每次工具调用 |

AI UserAgent 的 profile 至少冻结：遥感熟悉度、任务目的、可接受输出、澄清耐心、是否能提供缺失信息。
它只能看到与真实用户相同的请求、系统问题、报告和 artifact 摘要；不能看到 gold、故障注入 ledger、
隐藏 rubric 或系统内部计划答案。它可评价“是否回答了我、是否需要继续澄清、报告是否可理解”，但
不能裁定 NDVI/阈值/行政区分母的科学正确性。

目标 A 采用低成本风险抽样：程序与 AI judge 一致且明确成功的样本无需逐条人审；人工只看
`all failures + all partial/clarification + all grader disagreements + 至少 20% 的其余样本`。若 20×1
只有 20 条，这通常约为 4 条随机成功样本加全部异常项，而不是重新人工运行 20 次。只有当论文要把
该实验升级为新的独立效果证据时，才恢复盲评、双评审/一致性和逐条标签校准。

因此，当前所谓人工复核主要是**运行前评分口径的一次性批准和运行后的风险抽查**，不是数据制作、
不是让人替 Agent 点工具，也不是要求系统运行时每条都有人在环。研究者已经完成的 v1 运行包检查不
重复；task-11 按“恢复完成但用户结果交付有保留”冻结，v2 用报告校验修复该类问题。

### 6.5 目标 A：九月中旬前的开题级路线（当前 P0）

目标 A 不以 45-run、跨模型或完整用户研究为前置条件。文本工作现在开始；v2 只修复会影响“完整
系统架构”和轻量复验真实性的 P0 缺口，不扩展为新论文工程。

| 时间窗 | 工作 | 责任 | 完成标志 |
| --- | --- | --- | --- |
| 8 月 18–20 日 | 冻结 v1 真实性审计、claim-safe 口径和本计划 | AI 完成；研究者确认目标边界 | v1 事实表、反例、允许/禁止 claim、v2 工程任务书 |
| 8 月 20–27 日 | 顺序实施 V2-E1/E2；补测试与 evaluator；同时起草架构和方法文字 | 工程模型完成代码；研究者无需逐条参与 | live structured plan、Scientist revision、report/privacy tests 全绿 |
| 8 月 27–31 日 | V2-E3 无 API 验收和 3 条 live smoke；按行为变化决定是否重跑 v2 5×3 | AI 执行；新 API 仅需一次预算授权 | v2 acceptance manifest；必要时新 15-run 包 |
| 9 月 1–4 日 | 若成本允许，运行原 20-request × 1 最终条件；程序/AI 双评并做风险抽样 | AI 批跑与评分；研究者只看异常和抽样 | 轻量 planning/result/report closure 表；不宣称新论文级效应 |
| 9 月 1–10 日 | 制作图表、证据索引，写第一章系统、实验、结果和限制 | AI 起草；研究者按论文观点修改 | 第一章连续文本 v0.1 |
| 9 月 11–15 日 | 与总开题结构合并，压缩创新点，做全局一致性审查 | AI 整理；研究者最终定稿 | 开题级第一章包和答辩口径 |

20×1 是“有余力则做”的 breadth closure，不是开题写作 Gate。若 v2 工程或 smoke 延误，优先保住
系统闭环、3 条 smoke、v1 证据和文本；取消 20×1，而不是压缩写作或偷偷降低验收门槛。

### 6.6 目标 B：仅供毕业终稿参考的“漂亮实验”路线（当前 deferred）

当前最主要的论文级缺口确实不是系统架构，而是**增量机制对规划与恢复的帮助尚未被充分识别**。
用户当前不计划把本章另投一篇小论文，因此下列工作不进入九月前队列，也不交给下一位工程模型。
只有毕业终稿需要更强因果证据、或未来明确改变发表目标时，才按以下顺序做：

1. **重新建立可归因的基线。** 当前 B1 已包含结构化任务、validator 和 controlled stop，无法检验
   “结构化表示/验证相对自由规划”的增量。新协议应增加 direct/free-form 或旧系统 matched baseline，
   或恢复经审查的 P0–P3 累加式消融，同时保留当前 B1–B3 作为恢复机制子实验。
2. **扩大真正有区分度的 held-out 故障集。** 至少覆盖 3–5 类多步故障：下游瞬时失败、上游 artifact
   失效必须重算、checkpoint 前后不同故障、错误替代工具、预算临界和用户澄清后恢复。不能继续只靠
   task-11 一个 threshold fixture。
3. **让 B2/B3 产生可观察差异。** 设计只有 checkpoint 才能安全复用或恢复的场景，并报告重复工具数、
   受影响子图 edit size、恢复距离、无效 artifact 拒绝、tokens、wall time 和错误成功率。
4. **加强独立评分。** 将 plan/action consistency、revision trigger、subgraph locality、report closure 和
   graph semantics 变成可执行 rubric；程序 grader 与盲评人工/领域评审做抽样校准，报告分歧而非只报
   一个 PASS。
5. **先 held-out，再重复。** 面板和评分冻结后再做每条件 3 次或更多重复；45-run 只有在任务本身有
   区分度时才有意义。报告配对效应量、置信区间、失败类型和成本，不用温度 0 代替重复性。
6. **补外部有效性。** 增加至少一个新区域/影像、另一模型或 provider，并把科学指标/空间结果正确性
   放到 Ch2/Ch3 独立评价；必要时加入专家或目标用户校准。
7. **形成新论文叙事。** 从“又一个多 Agent 系统”提升为“遥感工作流中可验证的规划—反馈—局部恢复
   方法”，用旧 ExpertsRS 说明问题与历史基线，用新 matched study 证明增量，用跨章实验说明科学和
   系统外部效度。

这条路线只作为研究储备。开题可以说明其设计和可执行性，但不承诺完成 45-run、跨模型、完整人工
盲评或新用户研究；当前章节依靠已发表 20-request 人审证据、新系统架构和 v1/v2 初步运行闭合即可。

### 6.7 冻结命名与历史边界

现有冻结 JSON 保留 `B1_static/B2_adaptive/B3_checkpoint`，避免无审批重写历史工件；新汇报和新
manifest 一律加章节前缀写作 `C1-B1/C1-B2/C1-B3`，与第二章 B0–B5 区分。已发表/旧 StateFlow
只作历史参照，不伪装为相同条件下的 matched arm。若要增加 P0–P3 或 held-out panel，必须建立新
协议版本，不得修改、删除或覆盖本轮 15-run。

## 7. 当前停止规则与跨章移交

- 第一章目标 A 只允许新增隔离的 AI UserAgent 测试夹具，不新增常驻用户 Agent、平台、durable
  runtime 或 UI；
- V2-E1/E2、无 API 验收、3 条 smoke、claim-safe memo、图表、证据索引和章节初稿完成后，第一章
  进入 P1 维护；20×1 可因进度取消，不影响开题 Gate；
- 完成 v2 后，只有两类问题允许在写作期重开核心代码：影响已报告事实的可复现缺陷，或明确阻塞
  跨章接口的缺陷；
- 新 held-out/重复实验属于目标 B，必须使用新协议、保留当前 pilot、冻结评分后再授权 API；
- 第二章现在可以继续知识/contract admission；第三章可以继续外部 evaluator 准备，但不得用第一章
  15/15 protocol PASS 代替科学正确性、空间准确性或用户效果；
- 若时间与写作冲突，优先级固定为：**v2 P0 真实性缺陷 + 文本 > 3 条 smoke > 可选 20×1 > 新论文级
  实验 > 平台增强**。

## 8. 每个 workhorse 聊天的固定交付格式

每个实现或分析任务只领取一个有界工作包（`WPn` 或第 9 节 `Task n`），并在交付中写明：修改文件、
未触碰边界、测试/分析命令与结果、生成工件、尚未覆盖的反例、当前 commit。禁止根据聊天内容自行
升级 claim、改变冻结实验条件、覆盖 run 或修改 legacy notebook。

建议给每个 workhorse 的开头固定为：

> 读取 `docs/thesis/ch1_evidence_system/AGENT_HANDOFF.md`、`PLAN.md` 和
> `UNIFIED_RUNTIME_REVIEW_PACKET.md`。你只执行指定 WPn/Task；先核对最新基线和工作树，严格遵守允许
> 文件、非目标、验收和证据边界。不要未经批准调用真实 API，不修改 legacy notebook 或冻结的
> 实验 panel/gold/run。完成后运行规定检查；若产生代码/文档修改则提交独立 commit，并按 PLAN
> 第 8 节格式交接。

## 9. 给下一位工程模型的开工顺序

### Task 1：V2-E1 structured live planning（当前唯一代码 P0）

> 先只实现第 5 节 V2-E1：将已有 typed workflow kernel 接入 `ExpertsRSSystem.run()/resume()`，让
> Scientist 产生并修订完整多步计划，Engineer 只能执行 eligible node；分开 planned/observed graph，
> 修正 revision actor。不得扩平台、改 legacy notebook、覆盖 v1 runs、接真实 API 或顺手做跨章端口。
> 完成后提交测试、迁移影响和“旧 15-run 为何仍只能叫 v1”的说明，再领取 Task 2。

### Task 2：V2-E2 report/privacy/evaluator（Task 1 通过后）

> 修复用户请求输出闭合、partial/false-success 语义、`state.json` ThoughtEvent 脱敏和严格 evaluator。
> 用 task-11 的 40.76% 反例做回归：报告必须给出“有效影像像元范围内”限定，除非另有 AOI 证据；
> 不得把该数值直接重命名为行政区覆盖率。全部旧测试和新增反例必须通过。

### Task 3：V2-E3 offline acceptance（Task 2 通过后，无 API）

> 运行完整测试、clean environment、CLI/compile/leak checks 和 scripted 15-slot；生成 acceptance
> manifest、planned/observed graph 对齐表和允许/禁止 claim 更新。失败只修复 v2 范围内缺陷，不降低
> rubric，不修改 frozen v1 evaluator/gold。

### Task 4：live smoke 与必要重跑（需研究者一次性 API 授权）

> 先跑 3 条：普通多步、故障后 Scientist 修订、AI UserAgent 澄清。三条通过后，若 v2 改变了 v1 的
> 核心行为或报告终态，在新协议/目录重跑 v2 5×3；不得用新代码重新解释旧工件。记录模型、prompt、
> commit、预算、tokens、wall time 和全部失败。

### Task 5：原 20-request 轻量闭环（可选，不阻塞文本）

> 复用原论文精确请求和已有人审语义，冻结 v2 单一最终条件；运行 20×1，报告 planning correctness、
> result/terminal correctness、report completeness、false-success、trace/artifact completeness 和成本，
> 并按 6.4 做 AI UserAgent/AI judge 与风险抽样。不得宣称与原论文完全 matched，也不得把 AI judge
> 当作新的领域专家人审。

Task 1–3 可由工程模型独立完成；Task 4 只需研究者授权 API，不要求逐条操作；Task 5 中 AI 可完成
运行和初评，研究者只批准复用口径并审查异常/分歧/抽样。开题图表与章节文本和 Task 1–4 并行，
Task 5 若影响九月中旬写作则直接取消。目标 B held-out proposal 不在当前开工队列。

## 10. 第二章与第三章对接计划

### 10.1 对接目标与总原则

目标不是把三个仓库合并成一个应用，而是让它们围绕同一次运行形成稳定的生产者—消费者关系：

```text
Chapter 2: evidence ledger → admitted scientific contract
                                      ↓
User → ExpertsRS runtime → plan/action/observation/report → RunResult + TrialExport
                                      ↓
Chapter 3: EvalTask → external graders → Outcome → Evaluation
```

三个事实源必须始终分开：

1. **runtime facts（第一章）**：计划、动作、权限、工具 observation、artifact、checkpoint、终态；
2. **scientific obligations（第二章）**：知识来源、适用条件、禁止推断、证据义务和应采取的响应；
3. **evaluation facts（第三章）**：隐藏成功条件、故障注入、gold、grader 输出、人工评分和比较结论。

第二章不得直接执行工具或写 runtime state；第三章不得预排 Agent 行动或把 gold 放进上下文；
第一章不得自行声称科学正确，也不得读取 evaluator 的预期终态。

### 10.2 接口所有权

| 对象 | schema 所有者 | 生产者 | 消费者 | 稳定边界 |
| --- | --- | --- | --- | --- |
| `RunRequest/RunResult` | URSA | CLI/Python caller、runtime | 用户、Ch3 adapter | 当前主 API |
| `PlanVersion/ActionSpec/RuntimeEvent/ArtifactRecord` | URSA | runtime | Ch2 port、Ch3 exporter | WP1 后冻结 v1 |
| `ScientificContractBundle` | Chapter 2 | Ch2 compiler/admission pipeline | URSA constraint adapter | JSON + schema version + hash |
| `ConstraintDecision` | URSA/Ch2 联合语义，URSA transport | Ch2 adapter | runtime | 固定动作词汇和映射 |
| `EvalTask/Outcome/Evaluation` | Chapter 3 | Ch3 harness/graders | Ch3 analysis | agent-visible/private 双视图 |
| `TrialExport` | URSA | runtime exporter | Ch3 harness | portable relative refs，无本地绝对路径 |
| `CandidateUpdatePacket` | Chapter 2 | Ch2 episode adapter | Ch2 quarantine/review | 永远是 candidate，不在线改 ledger |

schema 由生产者仓库维护，消费者只实现带版本检查的 Pydantic mirror/adapter。不得用跨仓库
Python import、硬编码绝对路径或复制整个内部 state 建立耦合；跨仓库运输只使用版本化 JSON、
相对 artifact 引用、hash 和明确 provenance。

### 10.3 第二章端口：科学约束如何进入 runtime

首版只增加一个依赖注入端口，不新增 Agent 或第二套调度器：

```python
class ScientificConstraintPort(Protocol):
    async def prepare(self, context: TaskContext) -> ScientificContractBundle: ...
    async def assess(
        self,
        bundle: ScientificContractBundle,
        context: DecisionContext,
    ) -> ConstraintDecision: ...
```

`TaskContext` 只包含脱敏请求、任务族、可见数据语义、可用工具名和预算；`DecisionContext` 只包含
当前 plan/action/report 候选、精简 observation、artifact 类型和已有 contract refs。它们都不能包含
路径、raster、gold、评分合同、未公开环境内容或 chain-of-thought。

`ScientificContractBundle` 至少包含：

- `schema_version / contract_id / contract_version / ledger_version / task_id`；
- 1–3 个最小约束，每项含适用条件、禁止推断、所需证据、所需动作、风险和 residual uncertainty；
- `source_claim_ids / evidence locators / verification status / admission decision`；
- selector/compiler/prompt/source hashes 和 diagnostic/formal execution mode。

正式运行中，只有 `admit` 或经审查 `narrow` 的约束能强制改变动作。candidate/needs-review bundle
只能用于明确标记的 diagnostic run，不能生成 thesis-safe 科学结论。

`ConstraintDecision` 动作词汇固定为：

| Ch2 decision | runtime 确定性映射 |
| --- | --- |
| `pass` | 保持当前计划继续 |
| `revise` | 交回 Scientist，生成带原因和 contract refs 的 `PlanVersion + 1` |
| `add_validation` | 给计划加入必须完成的验证义务；未满足前不得报告成功 |
| `ask` | 转为 `needs_clarification`，问题引用触发约束但不泄露内部 gold |
| `reject` | `controlled_stop`，记录科学原因和被阻止的推断/动作 |
| `downgrade` | 允许有限继续，但限制报告结论范围并携带 residual risk |
| `escalate` | 首版映射为 `controlled_stop + human_review_required` 事件，不伪造自动解决 |

调用点只保留三个，避免形成任意 hook 平台：

1. Scientist 形成计划后、任何受影响动作执行前；
2. 新 observation 可能改变适用条件或证据充分性时；
3. Manager 最终报告提交前，用于结论校准和降级检查。

运行结束后，runtime 可以把结构化 episode 摘要交给 Chapter 2 生成
`CandidateUpdatePacket`；它必须进入 quarantine/admission review，不能在同一 run 中修改当前
ledger 或 contract。这与 Chapter 2 已冻结的 serving/learning state 分离规则一致。

### 10.4 第三章端口：runtime 如何进入独立系统验证

第三章保留 `EvalTask → TrialTrace → Outcome → Evaluation`，但通过 adapter 使用统一底盘：

1. Chapter 3 `EvalTaskAdapter` 只把 agent-visible 字段转换为 `RunRequest`；本地数据引用在 adapter/
   runtime 内解析，不进入模型消息；
2. `ExpertsRSSystem` 正常运行，不知道 expected outcome、rubric、fault seed 或 comparator label；
3. URSA `TrialExporter` 把 `RunResult + trace + artifact manifest + provenance` 转成版本化
   `TrialExport`；
4. Chapter 3 grader 使用 private evaluator view 生成 `Outcome` 和 `Evaluation`。

`EvalTask` 必须物理或结构化分成：

- **agent-visible**：用户请求、允许输入、交互条件、预算和公开 intended use；
- **evaluator-private**：成功断言、critical failure、gold/reference、fault plan、rubric 和评分权重。

`TrialExport` 至少包含：schema/version、run/environment/system variant、code/model/prompt/config hashes、
有序 runtime events、plan/contract/checkpoint refs、相对 artifact refs 与 hashes、终态、成本和
intervention events。它不包含绝对路径、raster 内容、密钥、隐藏评分字段或私有 chain-of-thought。

故障注入使用 evaluator 拥有的 `FaultInjectingExecutor` decorator：

- decorator 在工具边界注入一次可审计故障，系统只看到与真实故障同构的 observation；
- fault seed/预期响应只写 evaluator-private injection ledger；
- Agent context 不出现 “injected”、task ID 对应答案或预设后续动作；
- grader 通过 trial ID 关联 injection ledger 和 `TrialExport`，不要求 runtime 保存 gold。

第三章分层评分保持外部化：outcome validity、workflow correctness、scientific reliability、failure
behavior、user utility、efficiency 分别报告。`RunResult.validation` 仍只表示 runtime/contract/artifact
完整性；Ch2 科学判断写 trace contract events；Ch3 的 `Evaluation` 独立保存，三者不能合成一个
模糊的 `valid=True`。

### 10.5 最小贯通测试

| 层级 | 必须测试 | 证明范围 |
| --- | --- | --- |
| contract-unit | schema version、未知字段、缺证据、错误 hash、非法动作 | transport 和 fail-closed |
| port-integration | NoOp/Fake Ch2 port 对同一候选返回 pass/revise/ask/reject/downgrade | runtime 映射正确 |
| Ch2 diagnostic | 一个候选 contract 使计划增加验证，一个使报告降级 | 科学义务能改变可观察行为，不证明义务正确 |
| exporter-integration | 同一 run 可稳定导出 `TrialExport`，路径/gold 泄漏检查通过 | Ch3 可消费运行证据 |
| Ch3 deterministic MVP | artifact、终态、trace completeness、恢复范围 grader | 评估链闭合，不证明用户效用 |
| cross-chapter offline | 一个任务贯通 contract → runtime → artifact/trace → evaluation | 三章接口兼容 |
| live integration smoke | 固定模型运行一个 constrained task，外部 scorer 完成 | live 可用性，不是正式 Chapter 2/3 效果 |

同输入、同 fake port、同 fault seed 的离线运行必须产生相同决策序列和评分。版本不兼容、bundle
未 admission、artifact hash 不一致或 private 字段进入 agent view 时必须 fail closed。

### 10.6 实施顺序与版本里程碑

| 阶段 | 何时开始 | 工作 | 完成标志 |
| --- | --- | --- | --- |
| X0 接口冻结 | V2-E1/E2 验收后按写作优先级启动 | 审查 Ch2 bundle、Ch3 task/trace 资产；冻结上述 JSON 合同和两组例子 | proposal 获批，schema owner 明确 |
| X1 provider examples | deferred；不与 v2 争用第一章 writer | Ch2 导出一个 diagnostic bundle；Ch3 导出一个 agent/private 分离 EvalTask | examples 可独立 schema validate |
| X2 URSA ports | V2-E3 完成且 X0 批准后在独立分支启动 | `ScientificConstraintPort`、NoOp/Fake adapter、三调用点和 trace refs | port integration tests 通过 |
| X3 C1 实验冻结 | completed，2026-08-18 | 三次 smoke + 5×3 + truth/claim audit 已完成 | v1 事实与 claim 边界冻结，不回写 |
| X4 Ch2 接入 | 可在 C1 证据封存后合入 X2 | 消费 Ch2 bundle，跑 1–2 个 diagnostic 行为改变案例 | 无第二调度器；plan/report 可观察改变 |
| X5 Ch3 接入 | 可独立准备，开题写作后按优先级合入 | `TrialExporter` + EvalTask adapter + deterministic graders | offline evaluation MVP |
| X6 跨章 demo | X4+X5 | 同一任务贯通合同、runtime、工具、报告和外部评分 | `v0.7.0` integration demo |
| X7 正式研究 | 各章人工 Gate 后 | Ch2 matched mechanism study；Ch3 task/user/system study | 分章结果，不用 demo 代替 |

推荐版本语义：

- `v0.5.1`：第一章真实模型 pilot 冻结版；
- `v0.5.2`：v2 最小 live planning/report/privacy 闭环与验收版；
- `v0.6.0`：extension-ready，具有 Ch2 port 和 portable TrialExport；
- `v0.6.1`：一个 Chapter 2 diagnostic contract loop；
- `v0.7.0`：Chapter 3 deterministic evaluation MVP 与跨章演示。

X1 schema/example 包可以在下游独立准备，但当前不应挤占 V2-E1/E2/E3 和开题写作。
WP1、C1 15-run 与真实性审计均已完成；X2 仍须等待 v2 验收和 X0 的 schema/owner 裁决，并在单独
`codex/ch1-cross-chapter-ports` 分支开发。合入前基于冻结 commit rebase/cherry-pick 并重跑全部
回归，避免污染第一章 matched comparison 的历史证据。

### 10.7 第二章的实际推进顺序

1. 在 Chapter 2 先完成当前 human admission/claim boundary，不等待 URSA；
2. 从现有 `task-conditioned-epistemic-contract` 中导出一个最小 JSON schema 和一个 diagnostic
   example，保留 ledger/source/evidence/admission provenance；
3. 用 URSA Fake port 先验证七种动作映射，不调用真实知识库或模型；
4. 接一个真实导出 bundle，验证“增加验证步骤”和“报告降级”两个行为变化；
5. 只有 admitted contract、gold 隔离和 matched context 通过后，才把它用于 Chapter 2 B0–B5/
   四组正式实验；
6. task episode 只能生成 candidate update，人工准入后在下一 ledger version 生效。

这意味着第二章的知识核验、contract admission 和静态实验准备现在可以继续 P0 推进；它们不需要
等第一章 live 5×3。需要等待的是“把正式 contract 接入被冻结 runtime 做行为实验”。

### 10.8 第三章的实际推进顺序

1. 现在做 E0：从北京制图资产中整理候选 task、environment、artifact、failure registry，不修改
   冻结结果；
2. 现在做 E1/E2：冻结 `EvalTask/TrialTrace/Outcome/Evaluation` schema 和 agent/private 双视图；
3. 现在做 E3：实现只看现有 artifact/manifest/trace 的确定性 grader 和三个 replayable fault fixture；
4. WP2/WP3 稳定后实现 `TrialExport` consumer adapter；
5. C1 15-run 冻结后，比较 scripted/professional workflow、general tool Agent、structured URSA 的
   deterministic MVP；scientific-constraint URSA 只有在 X4 后加入；
6. Gate B 和伦理/数据边界通过后，才开展 6–10 个真实任务的专家/目标用户校准和重复 trial。

第三章现在可以开展 E0–E3，无需等待完整系统；但它们只能叫 evaluation preparation。`v0.7.0`
完成前不能称“稳定系统验证平台”，Gate B 前不能启动正式用户研究。

### 10.9 “较完整、成熟升级”的阶段定义

开题级完成与工程/毕业级成熟不是同一个 Gate。

开题级完成条件是：

- 已发表 ExpertsRS 的贡献、限制和当前升级问题有清晰映射；
- v2 的结构化 planned graph、validator、Scientist revision、observed process graph 和运行内
  checkpoint recovery 有统一系统载体和可复核软件证据；若 v2 未完成，只能降级描述为 v1 执行/
  审计底盘与初步恢复案例；
- 至少一次真实模型 pilot 完成，初步信号、失败、反例和不可支持结论被同时报告；
- Chapter 2/3 的科学约束和外部评价接口有明确后续方案；
- 不用系统集成 PASS 冒充稳定效果或科学准确性。

这些条件在 V2-E1/E2、无 API 验收、3 条 smoke、claim-safe memo、图表和章节初稿完成后即可满足，
不要求完成可选 20×1，更不要求先完成 X4–X7。

## 12. v0.5.3 审计补齐记录（2026-08-19）

本轮以 `112ed6f` 为工程基线，保留 v1 panel、gold、既有 v1 runs 和 20-request 人审证据不变。P0
仅包括：

1. 从原始用户请求以确定性规则生成 runtime-owned `DeliveryObligation`。task-11 强制要求
   `vegetation_coverage_map`（`plot_thematic_map(mask_raster)`）和 `green_cover_rate`（mask/area
   证据及“有效影像像元范围内”口径）；Scientist 不得通过 `requested_outputs` 漏列、改名或降级。
2. v2 evaluator 独立验证“原始请求义务 → 已验证 artifact/plan node → Manager deliverable → 报告”，
   并把 revision 图差异分类为 `local_reauthorization_only`、`structural_delta` 或
   `output_scope_delta`。task-11 的同图修订只允许前一种 claim：它证明 observation 后的局部重新授权，
   不证明更优规划路径。
3. 隔离的 `ProfiledUserAgent` 仅读取原始请求、Manager 问题和公开 artifact 摘要，固定回答一次
   “选择 NDVI 并要求地图”，再经 `.resume()` 完成。rule 与 live profile 均为测试夹具，不是常驻第四角色
   或用户研究；不得读取 panel gold、故障 ledger、私有 evaluator contract 或内部计划。
4. 统一 closeout manifest 记录 commit、环境、CLI/compile/diff、泄漏扫描、测试、scripted 15-slot、
   checksum、图对齐和 claim boundary。最终代码提交后才运行新的 `v2_authorized_pilot_<commit>` 5×3。
5. **20×1 取消且不构成开题 Gate**。最终 5×3 仍是本轮已授权的唯一大规模 live 重跑；任一槽失败保留目录、
   停止解释性 claim，修复后必须使用新目录重跑。

### v0.5.3 完成状态

- 最终代码：`0efd090`；scripted acceptance `v2_acceptance_0efd090` 为 15/15；CLI NDVI 闭环完成。
- 最终 live pilot：`v2_authorized_pilot_0efd090`，15/15 v2 closure。终态为 5 completed、7 controlled-stop、3 needs-clarification；v1 evaluator 仅保留并列历史记录。
- task-11 B2/B3 有两项 obligation、失败 observation、Scientist revision、checkpoint（B3）和两类图；graph diff 为 `local_reauthorization_only`。
- `v2_user_agent_smoke_bb7c8bf` 的 rule/live profile 均完成一次澄清—回答—`.resume()`；其证据范围是隔离夹具。
- 之前 14/15、13/15 的 live 目录保留为失败证据；同一 JSON 被 provider 重复拼接的传输现象已仅对完全相同对象规范化，异值第二决策仍 fail-closed。

工程演示完成条件（`v0.7.0`）是：

- 同一个用户请求进入唯一 runtime；
- 一个版本化、可追溯且不泄漏答案的 Ch2 contract 对计划或报告产生可见影响；
- Executor 产生真实 artifact 和 observation；
- runtime 记录 plan/contract/action/checkpoint/artifact/terminal events；
- Ch3 adapter 在系统外生成分层 `Outcome/Evaluation`；
- NoOp Ch2、constrained Ch2 和 fault condition 使用相同系统入口；
- 所有 schema/hash/权限/泄漏/失败分支测试通过。

这可以称为“跨章可扩展的完整研究系统演示”，但仍不能替代 Chapter 2 科学约束效果实验、
Chapter 3 grader 校准和真实用户研究。

### 10.10 可立即发出的对接任务

#### Cross-Chapter Chat X0（高阶模型，设计冻结）

> 审查 URSA `PLAN.md` 第 10 节与 Chapter 2 的 task-conditioned epistemic contract、Chapter 3 的
> EvalTask/TrialTrace 计划是否语义一致。只裁决 schema 所有权、动作词汇、agent/private 边界、
> 版本/失败策略和首批例子；不实现代码、不改 chapter claim 或实验 gold。输出一份 accept/narrow/
> reject 决策表和需要上游批准的最小问题。

#### Chapter 2 Chat X1-K（workhorse，导出合同样例）

> 在 Chapter 2 仓库只完成一个 `ScientificContractBundle` JSON Schema、一个 diagnostic example 和
> validator。它必须从现有 contract spec 派生，包含 ledger/source/evidence/admission provenance，
> 不含 gold 或完整参考答案，不调用 URSA、不升级 evidence status、不改变当前 S0 实验。

#### Chapter 3 Chat X1-E（workhorse，任务/评估样例）

> 在 Chapter 3 仓库只完成 `EvalTask` agent-visible/private schema、一个候选任务例子、最小
> `Outcome/Evaluation` schema 和 validator。保留北京资产 provenance，不改 frozen mapping result，
> 不启动用户研究，不把历史日志晋级为标准 trace 或 gold。

X1-K 与 X1-E 可以互相独立并行；URSA X2 writer 必须等 WP1 接口合入，并以获批 schema/example
为输入，不能自己重写第二、三章语义。

## 13. 开题后渐进升级路线与 Harness 采用决策（2026-08-21）

### 13.1 总体决定

ExpertsRS 保留 `Brain–Hands/Tools–Data` 作为面向遥感问题的功能架构；workflow 与多智能体属于
Brain 的规划/协作能力，runtime 是包围 Brain、Tools 和 Data 的共享控制外壳，evaluation 位于被测
系统之外。后续不得把 workflow、tools、multi-agent、evaluation 误画成四个同层级系统模块。

阶段叙事允许使用 **URSA Harness**，其完整含义固定为“domain-specific、evidence-first research
harness for remote-sensing workflows”。论文优先写“URSA 领域智能体运行时/研究型 Agent Harness”；
PPT 和面试可用短名，但不得省略其非通用、非生产级边界，也不因命名改变 Python package、公共 API
或既有 evidence path。

当前不整体迁移 DeepSeek Harness，也不因 AutoGen 进入 maintenance mode 而立即改写冻结基线。
DeepSeek Harness 作为现代 harness 的架构参照和潜在执行后端；优先吸收可替换能力边界，不复制其
通用平台范围。v0.5.3、`0efd090` 与既有 acceptance/live runs 保持不可变证据对象。

这一决定的依据是：

1. 第一章研究对象是 EO-specific typed workflow、plan-bound execution、observation-driven local
   revision、planned/observed graph 与 delivery closure；替换通用 harness 不直接增强这些 claim。
2. DeepSeek Harness 以 Node/TypeScript、Cordis plugin tree 和通用 shell/session/subagent 能力为主，
   不是 AutoGen Python adapter 的原位替换；全量迁移会重做消息、工具、artifact、state、trace、resume
   和 evaluator transport，并触发新的实验版本。
3. DeepSeek Harness 当前仍处 developer preview；兼容性风险与第一章的稳定证据需求不匹配。
4. ExpertsRS runtime 已掌握角色时序、计划验证、工具绑定、权限、终态和评测导出。AutoGen 当前承担
   model-facing AgentChat/team state，而不是领域控制面，因此可在未来通过 adapter 渐进替换。

### 13.2 有边界的插件化目标

DeepSeek Harness 底层框架名为 `Cordis`，其关键思想不是简单增加插件数量，而是让插件通过共享
context 提供 service、typed event 和可撤销的注册 effect，并把 service definition、provider 与
consumer 分离。ExpertsRS 借鉴这一 capability-seam 思想，但不采用“没有特权核心”的全部产品设计。

目标结构固定为 **stable domain kernel + replaceable capability ports + external evaluation**：

- 不可替换的 domain kernel：`RunRequest/RunResult`、typed workflow、validator、eligible-node、
  delivery obligations、actor attribution、budget/terminal semantics、planned/observed graph 和隐私不变量；
- 可替换的 capability ports：`DecisionProvider`、`ExecutionBackend`、`EventStore`、
  `ScientificConstraintProvider` 和 `TelemetrySink`；
- adapters/providers：AutoGen、direct model、local/subprocess/remote execution、JSONL/SQLite、Chapter 2
  knowledge provider；
- external evaluation：gold、fault ledger、grader 和 claim 判定始终不进入 plugin context 或 Agent 上下文。

P1 只使用 Python `Protocol + dependency injection + explicit registry/profile`，不建设动态发现、热加载、
任意插件卸载或通用 service locator。只有第三方能力、多产品 profile 或长周期服务真正出现后，才评估
plugin lifecycle manager。这样获得框架可替换性，同时避免配置顺序、隐式依赖、版本组合和安全面膨胀。

直接复用 DeepSeek Harness 代码分三级处理：

1. **优先复用思想和合同**：capability seam、append-only facts、context projection、guarded tool pipeline、
   profile composition、sandbox enforcement reporting；
2. **按需复用独立后端**：未来可通过 IPC/CLI/RPC 将其 sandbox/subprocess/remote execution 作为
   `ExecutionBackend`，先做 parity 原型，不把 Cordis 嵌入领域内核；
3. **默认不移植核心 TypeScript 包**：agent loop、session 和 tool registry 与 Cordis context/lifecycle
   深度绑定，移植到 Python 的胶水、重复类型和维护成本通常高于自建薄端口。若复制 MIT 代码，必须保留
   license/copyright、核查 third-party notices、记录来源与修改，并不得作为论文方法创新。

### 13.3 收益—风险矩阵

| 候选升级 | 对研究主线收益 | 工程收益 | 迁移/证据风险 | 当前决定 |
| --- | --- | --- | --- | --- |
| 整体替换为 DeepSeek Harness | 低；不自动产生新的方法证据 | 中高；可获得通用 plugin/session/shell 生态 | 高；跨语言桥接、语义漂移、重跑实验、preview 兼容性 | 不实施 |
| 借鉴 Cordis capability-seam 与 profile 思想 | 中；让方法内核与框架实现分离 | 高；便于替换、测试和分层演进 | 低；以显式 Python 端口落地 | 采用 bounded plugin architecture |
| 直接移植 Cordis/DeepSeek Harness 核心 TypeScript 包 | 低 | 低到中；仅在完整 Cordis 生态内明显 | 高；跨语言、生命周期和重复状态 | 默认不实施 |
| 将 DeepSeek sandbox/subprocess 作为外部 backend | 低到中 | 中高；可能补齐进程隔离 | 中；IPC、版本、Windows 与错误映射 | 需求触发后原型验证 |
| 抽取 `DecisionProvider` 并保留 AutoGen adapter | 中；降低框架对研究机制的干扰 | 高；可并存 direct/MAF/未来 Harness adapter | 低；用 parity tests 可控 | P1 实施 |
| 将 state/trace 收束为 append-only `EventStore` + projections | 高；加强 plan/fact/evidence 的统一来源 | 高；支持 replay、resume 和后续 telemetry | 中；需 schema/version 与兼容读取 | P1 设计，分步实施 |
| 抽取 `ExecutionBackend` | 中；保持 Executor 唯一入口 | 高；为独立进程、容器或远程执行留缝 | 低到中；当前 in-process backend 可保留 | P1 实施接口 |
| 进程级 sandbox/subprocess backend | 低到中；提升安全边界但非核心 novelty | 高；补齐当前应用层路径围栏的缺口 | 中；Windows/容器、资源限制与工具兼容性 | P2 独立升级，不绑定整套 Harness |
| approval escalation | 低 | 中；外部/不可逆工具启用后必要 | 中；涉及人机交互和策略语义 | 工具范围扩大时启动 |
| MCP、通用 plugin、tool search | 当前低 | 中高；大工具表时有价值 | 中高；扩大攻击面和验证范围 | deferred |
| dynamic subagent、background jobs、并发调度 | 当前低 | 长周期/通用任务时高 | 高；改变角色、状态和评测语义 | deferred，按任务需求触发 |
| OpenTelemetry/Web UI | 低 | 中；利于产品化和演示 | 低到中 | 求职/产品化支线，可选 |

### 13.4 Harness 试验的启动条件与停止 Gate

只有出现以下至少三项需求，才重新评估 DeepSeek Harness 或同类通用底座：

- 允许模型执行任意 shell/code，而不再只是六个安全绑定工具；
- 工具表扩大到需要动态搜索、MCP 或插件生命周期管理；
- 需要多 session、多用户、后台 job、cancel、durable resume 或远程 worker；
- 需要动态 subagent、父子 session 或跨产品 delegation；
- 自研 session/sandbox/plugin 维护成本持续超过领域研究成本；
- 候选 Harness 已进入稳定发布，并能给出明确的 Python/EO 工具集成路径。

若触发评估，只允许在独立分支做最小技术验证：一条普通 NDVI parity 和一条 task-11 故障恢复
parity。原型不得修改 v0.5.3 工件、panel 或 gold，也不自动进入论文证据。只有同时满足以下 Gate
才允许提出迁移计划：

1. `RunRequest/RunResult`、typed plan、delivery obligations 和两类图语义保持兼容；
2. 相同任务没有新增 false-success，且 v2 evaluator closure 不下降；
3. 获得可验证的进程隔离、持久化或维护成本收益，而不只是更换框架名称；
4. 自定义跨语言胶水和重复状态明显少于被替换代码；
5. 新依赖版本、回滚办法、预算和需重跑的证据范围得到单独批准。

任一 Gate 不满足即终止原型，继续使用自研 runtime 和现有 adapter。

### 13.5 Brain、Context、Memory 与 Knowledge 的升级边界

第一章不新增“长期记忆”创新 claim。当前 `state.json`、AutoGen team state、plan history、observation、
artifact、trace 和两类图属于单 run 工作记忆与可持久化 episodic record；因为它们尚未被跨 run 检索
并影响新决策，所以不得称为完整的长期经验记忆。

后续将旧图中的 `Knowledge & Memory` 分为两个语义面：

- `Context & Run Memory`：当前任务状态、计划、消息、observation、artifact 摘要、checkpoint；
- `Scientific Knowledge & Evidence`：文献、规范、传感器/方法适用条件、case bank、知识图谱和证据来源。

物理存储可以复用，但 schema、权限、更新与 provenance 必须分开。跨 run memory 只有在出现重复用户、
长周期任务或可检索历史经验的明确研究问题后才启动；“保存了 trace”本身不构成 memory effectiveness。

外部知识接入沿第 10.3 节已经冻结但尚未实现的 `ScientificConstraintPort` 推进。第一版只实现
版本化 contract/evidence adapter 和 NoOp/Fake/受审查 provider，不直接引入自主写回知识库；任何
历史 episode 产生的知识更新只能成为 `CandidateUpdatePacket`，进入 quarantine/review 后再 admission。

### 13.6 Benchmark 路线

评测分为四层，互不冒充：

1. **Regression suite**：维持 v0.5.3 的 121 项测试及 clean-environment/CLI/privacy gate，验证编码
   合同是否继续生效；
2. **Mechanism benchmark**：冻结当前 v2 5×3，作为规划约束、正确停止、局部修订、checkpoint、
   trace/graph 和 false-success 的初步 matched evidence；
3. **Historical/admission benchmark**：保留原论文 20 请求及 modern admission gold，用于支持/澄清/
   缺工具/科学拒绝分类，不启动当前六工具条件下的 20×1 live；
4. **Formal end-to-end benchmark**：由 Chapter 3 另行设计多任务、多数据、baseline、fault family、
   科学/空间结果、成本与人工校准。只有这一层用于稳定效果和外部有效性结论。

未来如对齐 ThinkGeo 等公开遥感 agent benchmark，只选择能明确映射当前数据与工具语义的子集，记录
适配差异；不得为了通用 leaderboard 扩大第一章工具范围或改变核心研究问题。

### 13.7 分阶段执行安排

#### P0：开题与面试表达（现在开始，尽量不改核心代码）

- 更新三张唯一 Mermaid 图：领域功能、角色责任、规划—执行—反馈—恢复；
- 增加一张仅用于面试/PPT 的“ExpertsRS 与现代 Harness 能力矩阵”；
- 统一 Brain、Hands/Tools、Data、Runtime、Evaluation、Context、Memory、Knowledge 术语；
- 修正文档中仍把 v0.5.3 写成未完成的旧状态，不重写历史审计事实；
- 形成一页系统说明、三分钟/十分钟项目陈述和 claim-safe 问答；
- Harness 采用 ADR 已完成；后续新增 Memory/Knowledge 边界 ADR，本节作为其决策来源。

#### P1：第一章后的低风险架构卫生（3–9 个月，Agent 主执行）

- 抽取 `DecisionProvider`，保留 AutoGen 0.7.5 adapter，并增加 direct OpenAI-compatible adapter；
- 抽取 `ExecutionBackend`，保留当前 `LocalInProcessBackend` 行为；
- 设计版本化 `EventStore`，先让 observed graph/evaluator export 从事件 projection 读取；
- 增加 schema migration/round-trip/parity tests；只有模型可见上下文或终态语义变化才重跑 live pilot；
- 不在此阶段增加角色、工具、长期记忆、MCP 或动态 subagent。

#### P2：Chapter 2 知识与科学约束（约 1 年）

- 实现 `ScientificConstraintPort`、contract bundle、evidence locator 和 constraint decision；
- 接入可引用的文献/规范/案例检索，评价 recall、rerank、evidence coverage、冲突和 freshness；
- 在计划 admission、observation 后复核和报告降级三个固定点接入，不创建第二套调度器；
- 保持 serving knowledge 与 candidate learning state 分离。

#### P3：Chapter 3 正式验证（约 1–2 年）

- 建立多任务、多场景、多故障 benchmark 和独立 gold/private evaluator；
- 加入旧对话流程、单 Agent、静态 graph、结构化 URSA 等 baseline/ablation；
- 评价完成/正确停止、恢复局部性、重算、证据闭合、科学精度、成本和人工结果质量；
- 只有任务设计确实需要时，才加入跨 run episodic memory 或用户 profile memory 条件。

#### P4：产品化/求职增强支线（不阻塞论文）

- 独立进程或容器 sandbox、资源配额、网络策略和 approval；
- durable session、jobs/cancel、OTel、Web UI、MCP 和可选 Harness/MAF adapter；
- 每项都以可演示收益和 parity test 为 Gate，不以“采用最新框架”本身作为完成标准。

### 13.8 人类与 Agent 的责任分配

| 责任 | 研究者主导 | Agent 主执行 |
| --- | --- | --- |
| 研究 | 问题、假设、novelty、baseline、claim boundary | 文献/代码事实核对、候选对照矩阵、草稿整理 |
| 科学 | EO 适用性、gold、主题/空间结果、专家校准 | 数据检查脚本、重复计算、provenance 与表格 |
| 架构 | 最终术语、边界和是否接受迁移 | ADR/接口草案、代码重构、parity/regression tests |
| 证据 | 决定哪些结果可进入论文与答辩 | runner、manifest、checksum、trace 分析和图表生成 |
| 表达 | 开题/PPT/面试主线与现场判断 | Mermaid、讲稿初稿、不同长度版本和一致性检查 |

默认工作方式是：研究者决定研究边界、科学判断和最终叙事；Agent 在已批准边界内完成小模块升级、
回归、文档、图表和证据整理。任何会改变模型上下文、工具可达性、终态语义或正式实验条件的升级，
必须先形成独立迁移计划并获得批准。
