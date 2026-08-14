# 第一章收敛执行计划：方法基线 v1 → 最小真实模型证据

> 状态：active
> 决策日期：2026-08-13
> 所属分支：`codex/ch1-unified-runtime`
> 唯一实现入口：`ExpertsRSSystem.run()` / `.resume()` 与 `python -m ExpertsRS`

## 1. 本阶段只回答什么

第一章不再以“建设通用 Agent 平台”为目标。其研究问题固定为：开放的遥感需求能否通过
**可调整的分层规划、随执行更新的过程图、基于检查点的局部恢复**，在真实工具反馈出现后
更好地完成、改道、停止和留下可审计证据。

本阶段采用两层完成定义：

1. **方法基线 v1**：新增机制已经有唯一运行载体，能够离线演示、检查和重复运行；
2. **第一章最小实证闭环**：同模型、同工具、同预算下完成小型真实模型对照，并形成结果与
   失败分析。

第一层是当前检查点，第二层才允许讨论方法效果。系统能运行不等于方法有效。

## 2. 已冻结的架构决定

1. 新系统只有一条权威链：`RunRequest → Manager → Scientist → runtime → Engineer →
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

## 3. 当前证据等级（2026-08-13）

| 项目 | 状态 | 可支持 | 不可支持 |
| --- | --- | --- | --- |
| 已发表 ExpertsRS | prior published evidence | 多智能体遥感分析的历史可行性和问题来源 | 新机制效果 |
| 统一 `run/resume` 链 | engineering support | 新系统已有唯一输入输出载体 | 真实模型可靠性 |
| 75 项统一测试 | engineering support | 当前软件合同、工具和离线系统路径可复核 | 科学效果或外部有效性 |
| NDVI/澄清/停止/恢复离线场景 | diagnostic evidence | 机制能被真实本地工具贯通 | LLM 自主决策质量 |
| 5 任务 × 3 条件离线预飞行 | diagnostic evidence | evaluator 已经通过统一 API，三条件可控 | 条件间效果差异 |
| 真实模型对照 | open | — | 当前禁止声称已通过 |

因此，当前对外阶段名统一使用：

> **第一章方法基线 v1 已形成，系统达到离线可演示和真实模型实验准备状态；正式效果证据仍开放。**

## 4. 当前检查点的验收标志

以下条件同时满足时，本轮架构整合结束，不再继续横向扩建：

- `codex/ch1-unified-runtime` 明确从 `codex/ch1-baseline-20260811` 分出，历史 notebook 未改；
- 新系统只有一个 `run/resume` 权威入口；
- 标准命令 `python -m unittest discover -s ExpertsRS -v` 返回 0（当前 75 项）；
- CLI 可离线生成真实 NDVI 栅格、地图、报告、`state.json`、`trace.jsonl` 和 `result.json`；
- 澄清、科学前置条件停止、目录越界拒绝、故障后计划修订与检查点复用有显式测试；
- D3 evaluator 只注入条件和读取轨迹，不再替 Agent 预排角色或动作；
- 已明确记录 live、科学正确性、耐久恢复和 18 工具完整 Agent 可达性等未通过项。

这些条件目前已经满足。该检查点叫“方法基线 v1”，不叫“第一章实验完成”或“系统整体通过”。

## 5. Workhorse 执行看板

### 5.0 调度规则

当前可以与“大版本和科学故事冻结”并行启动工程修复，但**核心代码一次只允许一个 writer**。
`models.py / decisions.py / system.py` 是高冲突文件；让多个 workhorse 同时修改它们，节省的时间
会被接口漂移和合并返工抵消。

推荐两条并行泳道：

| 泳道 | 当前工作 | 可否立即开始 | 写入范围 |
| --- | --- | --- | --- |
| A：研究冻结 | 大版本、C1 claim、实验条件和披露边界的人类/Sol 审查 | 是 | 论文总控 proposal、研究文档；不改 runtime |
| B：系统修复 | `WP1 → WP2 → WP3 → WP4a` 严格串行合入 | 是，从 WP1 开始 | ExpertsRS 新主线；不改科学故事和 evaluator gold |
| C：预备分析 | WP4a 测试矩阵/coverage 缺口只读审查 | 可与 WP1 并行 | 只交报告，不提交代码；WP1 合入后再实现 |
| D：后续底盘 | WP4b、WP5 | live 轻量实验后或空档进行 | 不得反向改变已冻结实验 commit |

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
| 1 | WP1 动作合同 | 无；现在开始 | `models.py`、`decisions.py`、`system.py`、对应新测试 | typed decisions + runtime/tool binding |
| 2 | WP2 live provider | WP1 | 新 `provider`/config 模块、`__main__.py`、必要的上述核心文件、对应测试 | 显式 offline/live 身份和失败语义 |
| 3 | WP3 Manager 报告 | WP2 | 核心文件、报告测试 | 同一报告合同和 artifact 引用校验 |
| 4 | WP4a live gate | WP3 | 测试、coverage 配置、最小缺陷修复 | critical edge tests、clean venv、≥85% 控制面覆盖 |
| 5 | S1–S3 live smoke | WP4a + 人类开门 | 只写不可覆盖 run 目录 | 3 个真实模型 smoke 工件 |
| 6 | E1 轻量 5×3 | S1–S3 全通过 + 协议冻结 | 只写不可覆盖实验目录 | 15 个 trial + 外部评分 + anomaly memo |
| 7 | WP4b / WP5 | 不改变 E1 冻结版本 | 非实验主线加固 | 跨进程恢复、更多鲁棒性与跨章端口 |

下面的每个包都是一个独立 workhorse 聊天的最大范围。

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

## 6. 真实模型实验何时可以开始

### 6.1 现在可以做什么

- 15 槽 scripted/offline 预飞行现在已经可以重复运行；它只用于检查协议和 evaluator；
- 可以立即开始 WP1，同时由高阶模型继续冻结大版本、C1 claim 和跨章边界；
- 不应现在直接运行 live 5×3，因为当前 CLI 仍默认 scripted，模型动作尚未完整类型化，最终报告
  仍是 runtime 固定句，provider 异常和关键预算分支也未形成完整实验级证据。

### 6.2 Gate L0：允许三次 live smoke

只有以下检查全部为 PASS，研究者才打开 API 双门禁：

- [x] WP1、WP2、WP3、WP4a 已按顺序合入，L0 冻结提交前工作树已核对；
- [x] 统一测试、`compileall`、`git diff --check` 和控制面/evaluator ≥85% coverage 通过；
- [x] clean venv 安装和同一 CLI/Python API 离线运行通过；
- [x] `execution_mode=autogen-live`、provider、model、prompt/panel/code hash 和预算进入 manifest；
- [x] temperature=0、cache off、provider/tool retry=0、timeout 和 token/turn/tool 上限已冻结；
- [x] agent view 泄漏测试通过；API key 仅存在于未跟踪环境变量；
- [x] live runner 调用统一 `ExpertsRSSystem`，代码中不再保留主动阻断；
- [x] 研究者批准模型、15-run 保守支出上限、文本外发边界和三次 smoke 双门禁（2026-08-14）。

达到 L0 后只运行三次固定 smoke，不自动续跑：

| Smoke | 场景 | 必须观察到 |
| --- | --- | --- |
| S1 | 普通 NDVI | completed、真实 raster/map、有效报告、完整 trace |
| S2 | 绿地覆盖故障恢复 | 失败可见、计划 v2、有效 checkpoint 复用、无重复 NDVI |
| S3 | “植被健康情况” | needs_clarification，同 run ID 恢复后继续 |

### 6.3 Gate L1：允许轻量 5 任务 × 3 条件

三次 smoke 全部达到预期终态后，先人工/Sol 检查一次运行包。以下任一项失败即 NO-GO：静默重试、
换模型/换样本、路径或 gold 泄漏、成本记录缺失、虚假成功、产物不可打开、trace 无法重建、条件
除了 capability policy 之外存在差异。

L1 通过后可以开始 15 个 live trial。**不需要等待 WP5、第二章知识库完成或第三章评测框架完成**；
但必须在一个冻结 commit 上一次性运行，途中不得修代码。遇到异常保留原 run，停止批次，形成
anomaly memo，决定修复后整批重跑还是把失败作为结果；不得删除失败并补样本。

### 6.4 现实的最早启动点

从依赖而不是日历判断，live smoke 最早位于 `WP1 → WP2 → WP3 → WP4a` 四个合入检查点之后；
轻量 5×3 最早位于三次 smoke 的人工审查之后。若每个包边界稳定，通常可压缩为 **4 个顺序
workhorse 实现/验收聊天 + 1 个高阶审查聊天**。大版本与科学故事冻结可以全程并行，不需要等其
所有文字定稿；只需在 L0 前冻结 C1 claim、条件、指标和披露边界。

以 2026-08-13 为计划起点，若 provider 兼容性没有产生新 P0 问题，建议把 **2026-08-16 至
2026-08-18** 作为三次 live smoke 和随后 15-run 的最早目标窗口，而不是承诺日期。若 L0/L1
任一门槛未通过，日期自动后移，不通过删测试、减披露检查或跳过 smoke 来追日期。

### 6.5 实验步骤

1. 冻结模型、prompt/hash、代码 commit、数据、预算、披露边界和失败策略；
2. 只跑三次 smoke：普通 NDVI、故障恢复、模糊需求澄清；任一失败先分析，不替换样本；
3. smoke 通过后运行 5 任务 × 3 条件的最小对照；
4. 分开报告任务闭合、正确改道、错误成功报告、恢复范围、轨迹完整性和成本；
5. 形成 claim-safe 结果备忘：支持什么、反例是什么、是否保留/收窄/拒绝 C1。

首轮 15-run 是单次 matched pilot，用于获得最小机制信号和发现失败模式，不承担稳定统计效应
声明。首轮结束前不授权 45-run 重复；只有运行完整、评分有区分度、成本可接受且未发现泄漏或
系统性 provider 失败时，才另行决定是否重复。

现有冻结 JSON 保留 `B1_static/B2_adaptive/B3_checkpoint`，避免无审批重写历史工件；新汇报和新
manifest 一律加章节前缀写作 `C1-B1/C1-B2/C1-B3`，与第二章 B0–B5 区分。已发表/旧 StateFlow
只作历史参照，不伪装为相同条件下的 matched arm。若要正式改 ID，须由研究者批准并新建协议版本。

## 7. 停止规则与跨章移交

- WP1–WP4a 只完成 live 所需最小加固；出现新平台需求一律进入 backlog；
- 5×3 最小对照完成并形成 claim-safe 备忘后，第一章回到 P1 维护，主投入恢复到第二章 P0；
- 第二章可以现在开始设计 adapter，但在 WP1/WP2 冻结前不进行依赖该底盘的正式实验；
- 第三章可以复用任务/轨迹草案，但在 WP4a、三次 live smoke 和接口版本冻结前，不把本底盘称为
  “真实环境稳定评测平台”。

## 8. 每个 workhorse 聊天的固定交付格式

每个任务只领取一个 `WPn`，并在交付中写明：修改文件、未触碰边界、测试命令与结果、生成工件、
尚未覆盖的反例、当前 commit。禁止根据聊天内容自行升级 claim、改变实验条件或修改 legacy notebook。

建议给每个 workhorse 的开头固定为：

> 读取 `docs/thesis/ch1_evidence_system/AGENT_HANDOFF.md`、`PLAN.md` 和
> `UNIFIED_RUNTIME_REVIEW_PACKET.md`。你只执行 WPn；先核对最新基线和工作树，严格遵守允许文件、
> 非目标、验收和证据边界。不要调用真实 API，不修改 legacy notebook、实验 panel/gold 或论文 claim。
> 完成后运行规定检查，提交独立 commit，并按 PLAN 第 8 节格式交接。

## 9. 现在就可以发出的三个聊天任务

### Chat A：高阶模型 / 科学冻结

> 审查第一章 C1 的问题—方法对象—条件—指标—允许 claim 是否闭合。重点裁决
> `C1-B1/C1-B2/C1-B3` 条件命名、15-run 作为最小 pilot 是否足够，以及 live 披露边界。
> 只形成 proposal/批复，不改 runtime、panel、gold 或历史 notebook。

### Chat B：workhorse / WP1（唯一核心代码 writer）

> 读取 `AGENT_HANDOFF.md`、`PLAN.md`、`UNIFIED_RUNTIME_REVIEW_PACKET.md`，只执行 WP1。
> 建立 typed role decisions 和 agent-visible ToolBinding 安全子集，runtime 独占路径解析、权限和
> 执行。解决非法 JSON、未知工具/参数/artifact 和重复失败终态；不接 API、不做报告闭环、不改
> evaluator、panel/gold、论文 claim 或 legacy notebook。完成统一测试、compileall、diff check，
> 提交独立 commit 并给出证据边界。

### Chat C：workhorse / WP4a 只读测试审计

> 在 WP1 开发期间只读审计当前控制面、状态转换、provider、报告和 evaluator 测试覆盖；输出一张
> “分支—现有测试—缺口—建议测试名—预期断言—所属 WP”的矩阵。不得修改核心代码和实验合同，
> 不得用当前 coverage 数字替代 WP1–WP3 合入后的最终测量。

Chat B 合入并经高阶审查后再启动 WP2；不要提前让 WP2 writer 基于旧接口并行编码。

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
| X0 接口冻结 | 现在，与 WP1 并行 | 审查 Ch2 bundle、Ch3 task/trace 资产；冻结上述 JSON 合同和两组例子 | proposal 获批，schema owner 明确 |
| X1 provider examples | 现在，可由下游仓库并行 | Ch2 导出一个 diagnostic bundle；Ch3 导出一个 agent/private 分离 EvalTask | examples 可独立 schema validate |
| X2 URSA ports | WP1 合入后，在独立分支 | `ScientificConstraintPort`、NoOp/Fake adapter、三调用点和 trace refs | port integration tests 通过 |
| X3 C1 实验冻结 | WP1–WP4a 后 | 三次 smoke + 5×3；冻结 `v0.5.1` experiment commit | C1 claim-safe memo |
| X4 Ch2 接入 | C1 15-run 后合入 X2 | 消费 Ch2 bundle，跑 1–2 个 diagnostic 行为改变案例 | 无第二调度器；plan/report 可观察改变 |
| X5 Ch3 接入 | WP2/WP3 字段稳定后开发，C1 15-run 后合入 | `TrialExporter` + EvalTask adapter + deterministic graders | offline evaluation MVP |
| X6 跨章 demo | X4+X5 | 同一任务贯通合同、runtime、工具、报告和外部评分 | `v0.7.0` integration demo |
| X7 正式研究 | 各章人工 Gate 后 | Ch2 matched mechanism study；Ch3 task/user/system study | 分章结果，不用 demo 代替 |

推荐版本语义：

- `v0.5.1`：第一章真实模型 pilot 冻结版；
- `v0.6.0`：extension-ready，具有 Ch2 port 和 portable TrialExport；
- `v0.6.1`：一个 Chapter 2 diagnostic contract loop；
- `v0.7.0`：Chapter 3 deterministic evaluation MVP 与跨章演示。

X0 和两个 X1 schema/example 包可以现在并行；X2 只能在 WP1 合入后开始实现。X2 不得合入或
改变正在冻结的 C1 5×3 experiment commit。最安全做法是单独
`codex/ch1-cross-chapter-ports` 分支开发，C1 15-run 结束后再基于冻结 commit rebase/cherry-pick
并重跑全部回归。这样既不阻塞接口工作，也不污染第一章 matched comparison。

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
