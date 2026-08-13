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

## 5. 后续任务包（可直接交给 workhorse 模型）

### W1：收紧模型动作合同（P0，阻塞 live）

目标：模型只能提出符号化动作，runtime 决定路径和真实参数。

- 增加有类型的 Manager、Scientist、Engineer、Report 决策模型；非法 JSON 必须形成可追踪失败；
- Engineer 动作为 `tool_name + artifact references + safe parameters`，禁止模型提交绝对路径；
- 模型可见工具集合必须与 runtime 实际存在的 `ToolBinding` 完全相等；不能继续“展示 18 个、
  实际只会拼 6 个参数”；
- 未知工具、未知参数、未知 artifact、重复失败必须有受控终态。

验收：新增非法 JSON、未知工具、参数越界、artifact 引用错误测试；相关 trace 不泄露本地路径。

### W2：建立显式 live provider 与实验身份（P0，阻塞 live）

目标：scripted 演示与真实 Agent 运行在结果中不可混淆。

- CLI/Python 配置显式选择 `scripted-offline` 或 `autogen-live`；
- 记录 provider、model、prompt hash、code commit、capability policy、预算和 execution mode；
- 实现 provider timeout、API 错误、非法响应、预算耗尽的明确终态，禁止静默换模型/样本；
- scripted 保持默认安全模式，但所有输出必须醒目标注，不能被描述为 live。

验收：无密钥时在网络请求前失败；超时/错误保留部分 trace；同一 scripted 输入可重复。

### W3：完成真正的 Manager 报告闭环（P1，阻塞“完整系统”演示）

目标：最终报告由 Manager 基于脱敏 observation 和 artifact manifest 生成，而不是 runtime 固定句。

- 增加结构化 `ReportDecision`；
- runtime 验证报告引用的 artifact 和终态；
- 报告失败时保留制品并返回明确的部分失败/失败终态；
- 离线 scripted provider 与 live provider 使用同一报告合同。

验收：成功、受控停止、报告生成失败、虚构 artifact 引用四条测试。

### W4：补齐控制面测试与干净环境验收（P1，阻塞冻结）

- 控制面、状态转换、evaluator 分支覆盖率达到 85%；
- 补预算耗尽、角色预算、provider timeout、损坏 state/result、多个输入、并发 run ID、工具异常；
- 在新虚拟环境按 `pyproject.toml` 安装并执行统一测试、CLI 和 `compileall`；
- 修复当前 Matplotlib `get_cmap` 弃用告警，但不改变地图语义。

验收：保存 coverage 报告和 clean-venv manifest；不以本机已有包代替依赖证明。

### W5：跨进程恢复与扩展接口（P2，不阻塞第一章 D3）

- 每次关键事件后原子保存 runtime state；损坏/不完整状态必须拒绝恢复；
- 保留 `.resume()` 处理用户澄清，另行定义清楚 crash recovery，不混淆两种语义；
- 冻结第二章 `ScientificConstraintPort` 与第三章 `EvalTask → TrialTrace → Outcome → Evaluation`
  接口版本。

验收：新进程恢复测试、状态版本迁移/拒绝测试、一个假科学约束 adapter、一个外部 evaluator。

非目标：Web/API 服务、UI、多租户、企业 IAM、分布式队列、自动下载数据、MCTS/LangGraph、
长期记忆、Agent RL、增加角色或扩大工具集合。

## 6. 最小真实模型路线（W1–W4 后）

1. 冻结模型、prompt/hash、代码 commit、数据、预算、披露边界和失败策略；
2. 只跑三次 smoke：普通 NDVI、故障恢复、模糊需求澄清；任一失败先分析，不替换样本；
3. smoke 通过后运行 5 任务 × 3 条件的最小对照；
4. 分开报告任务闭合、正确改道、错误成功报告、恢复范围、轨迹完整性和成本；
5. 形成 claim-safe 结果备忘：支持什么、反例是什么、是否保留/收窄/拒绝 C1。

条件命名当前存在 `P0–P3`、`B0–B3` 与第二章 `B0–B5` 冲突。推荐第一章改用
`W1=静态计划、W2=观察驱动修订、W3=检查点局部恢复`；已发表/旧 StateFlow 只作历史参照，
不伪装为相同条件下的 matched arm。该命名和基线定义须由研究者批准后才能改正式协议。

## 7. 停止规则与跨章移交

- W1–W4 只完成 live 所需最小加固；出现新平台需求一律进入 backlog；
- 5×3 最小对照完成并形成 claim-safe 备忘后，第一章回到 P1 维护，主投入恢复到第二章 P0；
- 第二章可以现在开始设计 adapter，但在 W1/W2 冻结前不进行依赖该底盘的正式实验；
- 第三章可以复用任务/轨迹草案，但在 W4、三次 live smoke 和接口版本冻结前，不把本底盘称为
  “真实环境稳定评测平台”。

## 8. 每个 workhorse 聊天的固定交付格式

每个任务只领取一个 `Wn`，并在交付中写明：修改文件、未触碰边界、测试命令与结果、生成工件、
尚未覆盖的反例、当前 commit。禁止根据聊天内容自行升级 claim、改变实验条件或修改 legacy notebook。
