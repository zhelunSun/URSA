# 第一章系统与仓库检查（2026-09-09）

本轮用途：为研究者后续操作建立代码、版本、证据可用性与计划入口的核查基础。
这是仓库检查回执，不是科学效果验收，也不是新的论文总计划。

## 1. 仓库身份与版本

| 项目 | 实查结果 |
| --- | --- |
| 所属 | 第一项研究的 URSA/ExpertsRS 方法系统、工作流实验与证据仓库 |
| 正式可写目录 | `D:/Projects/phd-thesis/URSA` |
| 本任务最初目录 | `D:/Projects/phd-research/ch1-agent-workflow`；恢复比较用，不在此写入 |
| GitHub | `zhelunSun/URSA`；正式副本使用 `github-big` SSH alias |
| 活动分支 | `codex/ch1-v2-e1-structured-planning` |
| 检查起点 | `0ccc3fcc10f90527ef9b71aa76dba2c96c24251f`；两个副本起点相同 |
| 软件版本 | `pyproject.toml` 为 `0.5.3` |
| 历史最终实验代码 | `0efd090`；与检查起点之间 `ExpertsRS/` 无代码差异 |
| 后续提交性质 | 文档、图源、同步与开发环境维护；不代表 v0.6/v0.7 已实现 |
| 保护点 | `prototype-notebook-v0-20250307`、`ch1-v053-closeout-20260819` 保留 |

“第一章”是仓库约定的第一项核心研究内容，不能据此推断学位论文目录中的最终章号或标题。
2026-09-07 总控决定已将职责更新为：第一项需求解析与工作流方法，第二项知识表示与推理，
第三项领域系统构建与应用验证。仓库所有权暂未迁移；第一项的方法原型仍在 URSA。
来源：`../../../../research-harness/THESIS_STATE.md` 与
`../../../../research-harness/decisions/DEC-2026-0907-post-advisor-system-integration.md`
（此处为从 evidence-system 目录出发的工作区定位说明）。

## 2. 系统架构与实现边界

权威链为 `RunRequest → Manager → Scientist → runtime → Engineer → Executor → observation → 修订/继续/停止 → Manager → RunResult`。

| 责任 | 当前代码位置（相对仓库根） | 核查结论 |
| --- | --- | --- |
| 唯一入口 | `ExpertsRS/__main__.py`、`ExpertsRS/system.py` | `run/resume` 已实现；CLI 默认 scripted-offline，不代表调用真实模型 |
| 角色决策 | `ExpertsRS/decisions.py`、`ExpertsRS/provider.py` | scripted 与 AutoGen live provider；`DecisionProvider` Protocol 已存在，不应作为全新接口重建 |
| 结构化计划 | `ExpertsRS/workflow/specs.py`、`graph.py`、`planning.py`，`system.py::_accept_plan` | Scientist 的 task/workflow 被实际验证、版本化并用于节点准入，已超出纯对话日志 |
| 动作执行 | `system.py::TOOL_BINDINGS/_execute_action`、`LocalToolExecutor` | Engineer 提议，Executor 唯一执行；18 个注册工具中仅 6 个进入主链 |
| 控制与证据 | `workflow/runtime.py`、`trace.py`、`obligations.py` | 权限/预算、交付义务、计划版本、真实 observation、产物、检查点与终态由 runtime 管理 |
| 外部评测 | `ExpertsRS/evaluation/ch1/` | panel、条件和 evaluator 在系统外；不能当作科学 gold 或常驻审核 Agent |

6 个绑定工具为：`read_raster_metadata`、`calculate_ndvi`、`plot_index_map`、
`apply_threshold`、`plot_thematic_map`、`calculate_area`。NDVI/阈值小样不等于完整城市森林分类系统。

planned graph 表示准备执行的计划；observed graph 从运行事实重建。局部修订须引用已有计划和
受影响节点，运行内检查点引用有效产物。它们尚未证明规划更优、检查点独立收益或进程崩溃后的耐久恢复。
权限控制是应用层围栏，执行仍在本地进程中。`ExecutionBackend`、版本化 `EventStore`、
`ScientificConstraintPort` 等长期计划不得整体当成当前交付；第二章服务尚未因此接入。
历史 notebook/StateFlow 是已发表原型复现面，与统一运行时分开解释。

## 3. 实验：历史结果与当前复核分开

冻结 panel 为 5 任务 × 3 条件，不是 15 次成功完成。C1-B1 为静态计划，C1-B2 加反馈修订，
C1-B3 再加运行内检查点。历史最终摘要报告如下：

| 任务 | 三条件终态 | 历史 v2 evaluator closure |
| --- | --- | --- |
| task-02 NDVI | 均 completed | 3/3 |
| task-03 缺 NDSI | 均 controlled_stop | 3/3 |
| task-10 LST 前置条件 | 均 controlled_stop | 3/3 |
| task-11 故障恢复 | B1 stop，B2/B3 completed | 3/3 |
| task-13 模糊需求 | 均 needs_clarification | 3/3 |

合计为 5 completed、7 controlled_stop、3 needs_clarification；15/15 是协议闭合，不是准确率。
历史摘要记录 DeepSeek-V4-Flash、215,500 token、391.582 秒。本轮未调用该模型、未复测这些数字。
task-11 的变化为 `local_reauthorization_only`；B2/B3 未识别出 checkpoint 的独立增量。
原论文 20 请求只作历史基础；历史与现代栅格不同，不可直接称同条件前后比较。

**原始证据可用性缺口：**`v053_evidence_index.md` 的四个 JSON 路径在正式与恢复副本中均未找到。
`70abb92` 的 archive 提交仅包含七份文档变更，没有原始运行包；因此本轮只能核对已提交摘要，
不能重新评价历史 trial 或核验索引 checksum。未据此断言其他机器/备份也不存在。
不得用重跑、新造 manifest 或空文件补作历史证据。下一步定位原运行环境/备份并验 hash。

## 4. 本轮实际检查

| 检查 | 实际结果 | 范围 |
| --- | --- | --- |
| 正式仓库 fresh-fetch 同步检查 | 起点 ahead=0、behind=0、dirty=0 | Git 可恢复检查 |
| 工作区导航 | 0 issues | 正式所有权/路径一致 |
| 四库同步门 | 第一/三章干净；总控 31、第二章 38 个未提交路径 | 其他任务内容保留，不纳入本轮提交 |
| `.venv/Scripts/python.exe -m pytest -q` | 121 passed，40.84 s；12 条 rasterio 待弃用警告 | 现有环境工程回归；未新建 clean venv |
| `ExpertsRS/run_m1_closeout.py` | PASS；39 unittest、18 工具 smoke 与本地工具诊断 | no-API |
| `ExpertsRS/run_d2_closeout.py` | PASS；49 unittest 与局部恢复/权限诊断 | no-API，与完整测试有重叠，不相加 |
| `python -m compileall -q ExpertsRS` | PASS | 可编译 |
| 统一 NDVI CLI | completed，3 工具调用、3 产物、1 计划版本 | scripted-offline；真实本地栅格工具 |
| `git lfs fsck --objects` | PASS | 当前本地 LFS 对象完整；本轮未做 clean-clone LFS 恢复 |

CLI 新诊断位于 `ExpertsRS/results/audit_20260909/audit-20260909-ndvi/`；
M1/D2 为 ignored 本地诊断。它们不是 2026-08-19 live 包，不进入 Git，不提升科学证据等级。
未运行付费 API、新 live pilot、模型升级或核心算法改写。

## 5. 后续操作基础

1. 后续开发打开正式 `D:/Projects/phd-thesis/URSA`，先读 evidence-system README 顶部与本回执。
2. 优先找回最终 live、scripted acceptance、UserAgent smoke、CLI closeout 的历史运行包，逐项验 hash；
   在恢复完成前，汇报明确数字来自冻结摘要。
3. 当前写作复用 `module_continuity_map.md` 三图、`ch1_v053_draft.md` 与结果表；
   章节分工/日期以总控现有计划为准，不重新启动旧 WP 或取消的 20×1。
4. 新方法实验的价值在于隔离需求解析、计划调整和 checkpoint 的作用；须先确定匹配基线、
   可区分条件的任务/故障及评分规则。现有 121 项工程测试不能替代这一研究工作。
5. 长期插件化、durable session、sandbox 与更多工具按原有后续门禁处理，不阻塞当前材料。

本轮维护仅新增检查回执并修正 README、PLAN、AGENT_HANDOFF 与 evidence index 的现时入口。
历史失败、实验数值、冻结 JSON、核心代码与保护标签未修改；软件版本维持 v0.5.3。
