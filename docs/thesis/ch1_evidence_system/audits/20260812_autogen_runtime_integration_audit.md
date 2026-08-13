# 2026-08-12 AutoGen、运行时与 D3-light 接通审计

> 范围：只读审计当前工作树；不调用模型 API。目的不是否定现有升级，而是明确哪些组件已经
> 接通、哪些只是并列资产，避免把本地机制预飞行误写为真实多智能体实验。

## 一页结论

`ModelDecisionAdapter`（此前不够清楚地被称为 live provider）不是调度器。它是本项目手写的、
OpenAI-compatible HTTP **模型调用适配器**：向一个模型端点发送经脱敏的文本，并严格要求返回一条
JSON“下一步决定”。真正的调度器是 `D3LightRunner`；它目前按任务 ID 和内部阶段选择角色、推进后续
动作。它没有创建 AutoGen/AG2 的 Agent、GroupChat 或 GroupChatManager。

因此 D3-light 当前的真实模型入口不能作为“AutoGen 多智能体 + 运行时”的 live 对照执行。它只可
作为接口和隐私边界的工程准备。D3 的五任务选择、B1/B2/B3 评分合同和本地真实工具预飞行仍有效；
但必须先让原有 AG2 多角色路由实际产生、修改和消费计划，才能进行真实模型 smoke。

## 事实来源：谁提供了什么

| 层次 | 当前资产 | 来源与实际作用 | 是否已接到 D3 真模型路径 |
| --- | --- | --- | --- |
| 多角色会话与发言调度 | `react_demo.py`、`react_orchestration.py` | **AG2/AutoGen 0.9.9** 提供 `AssistantAgent`、`UserProxyAgent`、`GroupChat`、`GroupChatManager` 和工具注册 API；项目的 `speaker_selection`/ReAct 回送规则是手写扩展 | 否 |
| 角色、工具与真实工具调用 | `prompts.py`、`tools/registry.py`、18 个工具 | 角色提示词和遥感工具为项目资产；AG2 负责把“模型选择工具”与“Executor 执行函数”分开注册 | 在既有 ReAct path 中是；D3 中仅工具执行器接入 |
| 运行记录、过程图、计划版本、检查点、权限 | `workflow/` | 项目手写、框架无关的最小运行时；采用事件溯源、可恢复工作流、可观测性等成熟思想，但没有直接使用 LangGraph/Temporal/OTel runtime | 是，但目前由 D3 runner 驱动 |
| D3 模型调用适配器 | `d3_light_model_connector.py` | 项目手写 REST 适配器；不是 AutoGen agent、不是群聊管理器、也不维护团队状态 | 是，但不应单独用于真实 D3 |
| D3 外部评分 | loader + `evaluate_dry_run` | 项目手写的独立评测投影；隐藏合同不进入 Agent | 是 |

## 高优先级发现

### F-01：当前 D3 调度不是多智能体调度（阻断真实 D3 API）

`D3LightRunner` 以 task ID 与 `phase` 选择 Manager/Scientist/Engineer，且在成功或失败后按预置映射
推进 phase。即使接入真实模型，它仍是“受限的逐步模型决策器”，而不是原有的 AG2 GroupChat。
任务 11 的 revision/checkpoint 也由 runner 的条件规则建立，尚非真实 Scientist 从观测中自主形成。

**影响：** 不能用它证明“多 Agent 规划”或“模型根据反馈重规划”；只能证明人为限定的运行时路径可
记录、可恢复、可评分。

**处置：** 禁止当前 `run_d3_light_model_smoke.py` 发送网络请求。后续 D3 需要一个很小的
`AG2–runtime bridge`：保留既有 Manager→Scientist→Engineer→Executor ReAct 路由，让 Agent 的实际
决定产生计划版本，让 Executor 的真实反馈进入记录，并由运行时在其外部记录权限、检查点和过程图。

### F-02：实验协议有未执行的 AutoGen 字段（高）

面板里的 `max_groupchat_rounds`、Scientist/Engineer 分项工具上限来自 AutoGen 设计，但直接 D3 runner
没有使用它们；它只实际限制总模型轮次与总工具调用。这会使声明的相同预算与实际执行预算不一致。

**处置：** 面板保留为任务/评分冻结件，不把其当前 model-run 字段当作可执行协议。桥接设计确定后，
一次性冻结真正被 AG2 与运行时共同强制的预算。

### F-03：AutoGen 仍重要，但它与运行时尚未合流（高）

AutoGen/AG2 并非形同虚设：既有 live path 使用其角色对象、群聊、GroupChatManager、函数选择/执行分离
和人类输入边界；项目 ReAct 选择函数在该框架内部运行。当前运行时也并非“框架替代品”，而是新增的
可审计控制与证据层。问题仅在于两者目前以 sidecar 方式并列，尚未组成一条真实模型端到端路径。

### F-04：图与检查点为项目实现，不能单独包装为技术新颖性（中）

`WorkflowGraph`（静态依赖图）与 `build_process_graph`（从事件确定性整理的过程图）都由项目手写；前者
不是 LangGraph graph，后者也不是图数据库或 durable executor。`Checkpoint` 是逻辑恢复引用，并不复制
文件、回滚 effect 或提供分布式持久化。

**允许的贡献表述：** 在面向用户的遥感分析中，将可调整计划、真实工具反馈的过程记录和基于有效
产出的局部恢复组织为一个轻量、可审计的闭环；单项技术均借鉴成熟模式，创新性必须落在这一定域集成
和其受控验证上，而不是声称发明了 graph、ReAct、checkpoint 或 agent framework。

## 成熟借鉴与项目自建的边界

- **直接使用：** AG2/AutoGen 0.9.9 的多 Agent/群聊/工具注册能力；Rasterio 与 Python 工具链。
- **按成熟思想自建：** typed tool contracts、validator、事件记录、过程图投影、计划版本、逻辑检查点、
  本地默认拒绝权限策略，以及 D3 evaluator。它们不是“从零创造概念”，而是针对现有遥感工具和
  论文边界的最小实现。
- **未使用但可作为对照/工程参考：** LangGraph/Temporal 式 durable execution、OpenTelemetry 导出、
  企业 IAM、图数据库、MCTS。不得暗示已经采用。

官方 AutoGen 文档也把 GroupChat 的 next-speaker manager 看作独立控制角色，并区分预置 team 与自定义
group-chat logic；这支持“保留 AG2 调度、在其外增加运行时记录”的小型桥接，而非重新手搓整套框架。

- [AutoGen Group Chat](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/group-chat.html)
- [AutoGen SelectorGroupChat](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/selector-group-chat.html)
- [AutoGen v0.2→v0.4 migration guide](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/migration-guide.html)

## 允许继续的最小下一步

1. 不扩展角色、不引入新图框架、不重写 notebook。
2. 设计并无 API 测试一个 bridge：监听既有 AG2 的 decision/tool/observation/handoff，写入同一
   `WorkflowTrace`；运行时只做权限、计划版本、检查点和过程图整理。
3. 让 B1/B2/B3 的差异只发生在“是否允许根据观测修订计划、是否允许引用检查点”，而不预先替
   Scientist 填写后续 phase。
4. bridge 通过假模型和真实本地工具的无 API 集成测试后，才重新提交真实 15-run 的授权申请。

这是一项必要的“合流”工作，不是再加一层 agent 或再造一个框架。完成前，D3 只能标记为
`panel-ready / local-tool-preflight / live-execution-blocked`。
