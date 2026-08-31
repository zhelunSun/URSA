# ADR-001：广义 Runtime 探索与当前 Workflow Kernel 的关系

> 术语说明：本文件保留少量代码名用于追踪实现；论文和人工审批只使用“可调整的分层规划、
> 随执行更新的过程图、基于检查点的局部恢复”。代码代号不构成新的论文概念。

> Status: accepted with 2026-08-09 clarification. 研究者接受保留 User-centric RS 母体、
> 将静态图降为基线/中间资产，并冻结“可调整的分层规划、随执行更新的过程图、基于检查点的
> 局部恢复”三个对象。

> Implementation update（2026-08-29）：下方 `Consequences` 保留接受 ADR 时的历史状态；其中
> “typed workflow 与 live 尚未贯通”等缺口已由 v0.5.3 解决。当前事实以 `claim_registry.md`、
> `v053_evidence_index.md` 和 evolution ledger 的 S10 为准；本 ADR 的架构取舍本身仍有效。

## Context

`origin/codex/ch1-runtime-foundation` 已实现显式 RunState、artifacts、evaluator、orchestrator、backend provenance 等广义运行时能力。当前 `main` 工作树又形成了更小的 `workflow/` kernel 与 ReAct sidecar。两者在 contract、state、trace 和 orchestration 上部分重叠，但服务的研究目标不同。

## Proposed decision

1. 不把远端 runtime 分支整体合并为当前第一章方法；
2. 保留框架无关的 task/operator/artifact/event 接口，但不要求 Scientist 在执行前产生完整、
   固定的 `WorkflowGraph`；
3. 把远端分支标为 `engineering exploration / asset reservoir`；
4. 只有在 P0--P3 需要时，逐项抽取 manifest、environment provenance、checksum、checkpoint 或 evaluator 资产；
5. ReAct/AutoGen/LangGraph 都是可替换 adapter，不定义科学 claim；
6. 当前静态 `WorkflowGraph + validator + deterministic repair` 作为已实现内核和实验
   基线；最终候选方法以可调整的分层规划、随执行更新的过程图和基于检查点的局部恢复为
   三个研究对象；
7. 过程图连接计划与真实动作、工具反馈、产出、修改和替代路径，是运行中逐步形成的审计接口，
   不是先验硬剧本；Agent 只读取当前相关的简要信息；
8. runtime 是 Manager、Scientist、Engineer、Executor 共用的控制/证据环境，不新增审核
   Agent，不替代 Scientist 的科学方法选择。
9. validation 由角色责任、deterministic runtime gates、按需无执行权限 verifier 与独立
   evaluation plane 分层承担；不设置默认常驻 Validation Agent，也不允许 reviewer 自行调用
   有副作用工具；
10. 权限作为运行支撑预留最小检查接口，由唯一 Executor 执行允许、拒绝或要求确认；D1 只
    冻结责任和最低信息要求，完整企业权限、隔离与协议接入延期。

## Rationale

- 广义 runtime 功能多，但不能自动回答“validation/repair 是否改善 executable planning”；
- 先冻结可消融机制，能避免框架迁移、UI、durability 等因素混入主实验；
- 近期 ReAct、DS-STAR 与 AGENTFLOW 等工作支持 observation-driven iterative planning；
  Spatial-Agent 又说明硬工作流图已有直接强邻居，因此“图本身”既不是最佳自治接口，也
  不能承担独立 novelty；
- 保留旁支可以避免丢失已验证的 artifact/provenance/evaluator 代码；
- 逐项抽取比整体合并更容易保持 claim 与 implementation 对应。

## D1 extraction decision（2026-08-10）

- current main 的 `TaskSpec/OperatorSpec/ArtifactSpec`、semantic-band adapters、validator、
  `WorkflowTrace`、ReAct owner-return/budget/exclusive Executor 是权威基线；
- broad branch 只选择性复用 `RunState` 中的 ID/timestamp/serialization、artifact manifest 和
  backend provenance 字段，以及 evaluator 的 deterministic closure checks；
- broad branch 的 `HumanCheckpoint` 只是计划批准记录，不具恢复语义；不能直接升级成论文中的
  checkpoint recovery；
- 拒绝抽取固定 manager→scientist→approval→engineer→verifier→reporter 流程、Verifier/Reporter
  常驻角色、旧数字波段 contracts 与 LangGraph 占位 adapter；
- D2 按时间保存真实运行事实，再由纯函数自动整理成简要过程图；静态 `WorkflowGraph` 保留为
  B1 基线和局部依赖视图；
- 18 tools 暂分为 read 4、compute 2、write-local-artifact 12，external/irreversible 0；Agent
  只提出动作，Runtime 决定 allow/deny/confirm，Executor 产生真实 effect。

## Consequences

- 当前必须诚实承认 typed workflow 与 live ReAct 尚未贯通；
- 当前代码没有计划版本、过程图自动整理、检查点替代路径、路径选择或基于过程图的反思；
  接受本 ADR 只冻结方法方向，不把这些对象标成已经实现；
- deterministic repair 只保留为最小 baseline；后续由 Scientist/Engineer 根据 observation
  选择重规划，runtime 只保证状态、执行边界、provenance 和安全停止；
- 新增 verifier 不是默认集成路径；只有明确语义审核触发器和独立评测设计时才作为可替换
  service/ablation 引入；
- 权限检查接口属于安全边界而非方法创新，当前不得写成已有完整权限系统；
- 远端分支的 28 项 runtime tests 只能说明旁支工程资产可运行；
- 在 ADR 被正式接受前，论文不得写成“我们主动废弃/替换了旧 runtime”，只能写“发生了广义探索并在随后收窄研究范围”；
- 后续抽取必须带独立 commit、test 和 evidence role，禁止把旁支代码量计入当前 M1 完成度。
