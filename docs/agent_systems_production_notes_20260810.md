# Agent 系统建立：生产环境实践资料笔记

> 私有研究笔记｜首次整理：2026-08-10（Asia/Shanghai）
>
> 目标：从 Anthropic 的 *Building effective agents* 出发，补充 Anthropic、OpenAI、Google 官方公开材料中对生产级 Agent 最有迁移价值的经验。优先记录工程方法、失败模式、运行时与评估，而不是模型排行榜或论文结论。
>
> 配套公开仓库草案：[Agent Systems Field Guide](D:/projects/phd-thesis/agent-systems-field-guide/README.md)。该仓库将把本笔记中的来源进一步拆成可维护的 source cards、pattern cards 和小实验。

## 0. 先给结论

生产级 Agent 已经不应被理解为“LLM + 一组 function calling”。更准确的系统边界是：

```text
模型（reasoning）
  + 工具与数据连接（tools / MCP / APIs）
  + 工作流/编排（loop / routing / handoff）
  + 状态与上下文（session / memory / artifacts）
  + 执行环境（sandbox / browser / code runtime）
  + 控制层（auth / permissions / guardrails / human approval）
  + 可观测与评估（traces / trajectory evals / online monitoring）
```

三家材料共同指向一套相当务实的路线：

1. 先做一个边界清楚、工具少而专的单 Agent，建立可重复的质量基线。
2. 只有在任务可以并行分解、上下文需要隔离、或专业能力确实不同的时候，再引入多 Agent。
3. 把上下文当作有限资源管理：按需检索工具和记忆，大对象放到 artifact/file store，不要把所有东西不断追加进 prompt。
4. 把 session/event log、harness/orchestrator、sandbox/tools 解耦，使故障可恢复、组件可替换、凭证不可达。
5. 评估完整轨迹和状态变化，而不仅是最终答案；上线前做离线回归，上线后做线上监控和分阶段发布。
6. 对发送消息、付款、删除、提交代码等不可逆动作，使用确定性策略、权限隔离和人工审批，不把安全完全寄托给 system prompt。

## 1. 推荐资料总表

优先级说明：P0 = 建议优先精读；P1 = 针对专项问题阅读；P2 = 作为案例或补充。

| 厂商 | 优先级 | 资料与时间 | 最值得带走的内容 | 适合回答的问题 |
|---|---:|---|---|---|
| Anthropic | P0 | [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)，2024-12-19 | 基础模式：single-agent loop、prompt chaining、routing、parallelization、orchestrator-workers、evaluator-optimizer；核心建议是从最简单的模式开始 | Agent 工作流有哪些基本架构？什么时候不应该上多 Agent？ |
| Anthropic | P0 | [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)，2025-09-29 | 从 prompt engineering 转向 context engineering；上下文是有限的“注意力预算”，目标是每次推理提供最小但高信号的信息集合 | 长对话、工具结果、记忆和 MCP 如何共同进入上下文？ |
| Anthropic | P0 | [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)，2025-11-04 | 用代码访问 MCP，把工具发现、循环、过滤、聚合放到执行环境；减少工具定义和中间结果在模型上下文中的重复传递 | 工具很多、数据很大时如何降 token、降延迟和降复制错误？ |
| Anthropic | P0 | [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)，2026-01-09 | 用 task / trial / grader / transcript（完整 trace）组织 Agent eval；多次 trial、组件检查、端到端检查和线上监控结合 | 如何评估多轮、改状态、会失败恢复的 Agent？ |
| Anthropic | P0 | [Harness design for long-running application development](https://www.anthropic.com/engineering/harness-design-long-running-apps)，2026-03-24 | planner-generator-evaluator 三角色；按 feature/sprint 分块；用结构化 artifact 交接；独立 evaluator 比自评更可靠；可用测试/浏览器真实操作检查成果 | 多小时任务如何避免跑偏？如何让 Agent 产生可验证的工作产物？ |
| Anthropic | P0 | [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)，2026-04-08 | session 是持久事件日志，harness 是可替换的循环，sandbox/tools 是“hands”；三者解耦后可独立失败、恢复和扩缩容；凭证不进入 sandbox | 长时 Agent 的运行时应该如何拆分？如何处理崩溃、重试和网络边界？ |
| Anthropic | P1 | [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)，2025-06-13 | lead agent + 并行 subagents；适合 breadth-first、开放式、可独立探索的研究；代价是 token 和协调复杂度明显增加 | 多 Agent 何时真的带来收益？并行研究系统怎么做？ |
| Anthropic | P1 | [Introducing advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use)，2025-11-24 | Tool Search Tool、Programmatic Tool Calling、Tool Use Examples；工具按需发现，常用工具常驻，其余延迟加载 | 数十/数百个工具怎样仍保持工具选择准确率？ |
| Anthropic | P1 | [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)，2025-10-16 | progressive disclosure：先给 skill 元数据，相关时再加载完整说明和附加文件；能力包可以比单个上下文窗口大得多 | 如何组织可复用的领域能力、操作手册和工具知识？ |
| OpenAI | P0 | [A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) | 基于客户部署经验的入门框架：先验证是否真的需要 Agent；模型/工具/指令三要素；先单 Agent 建基线，再按复杂度拆分；guardrails 与人工介入是必要设计 | 哪些业务适合 Agent？如何选择模型、工具和编排方式？ |
| OpenAI | P0 | [Agents SDK 官方指南](https://developers.openai.com/api/docs/guides/agents) | 明确区分 Responses API（应用自己拥有 loop）与 Agents SDK（SDK 管理 loop）；提供 sessions、handoffs、guardrails、resumable approval、traces | 什么时候自己写 loop，什么时候用 SDK？生产系统最小能力面是什么？ |
| OpenAI | P0 | [Trace grading 官方指南](https://developers.openai.com/api/docs/guides/trace-grading) | 对 agent trace（决策、工具调用、推理步骤的端到端日志）打结构化分数/标签，以定位编排或行为问题 | 如何把“看起来答对了”转化为可定位的工程质量信号？ |
| OpenAI | P0 | [New tools for building agents](https://openai.com/index/new-tools-for-building-agents/)，2025-03-11 | Responses API、内置 web/file/computer tools、Agents SDK、observability 的平台化组合；生产 Agent 的难点被明确归纳为 orchestration 和 visibility | OpenAI 当前 Agent 平台的基础抽象是什么？ |
| OpenAI | P1 | [Introducing AgentKit](https://openai.com/index/introducing-agentkit/)，2025-10-06；2026-06-03 更新 | Agent Builder、Connector Registry、ChatKit、datasets/trace grading 等产品化尝试；重要状态变化：OpenAI 已公告 Agent Builder 和 Evals 将于 2026-11-30 后停止，代码工作流建议转向 Agents SDK | 如何看待厂商托管的可视化 Agent 平台？哪些抽象值得自建？ |
| OpenAI | P1 | [ChatGPT agent System Card](https://openai.com/index/chatgpt-agent-system-card/)，2025-07-17 | 研究、远程视觉浏览器、terminal、外部连接器组合成一个 agentic product；说明 terminal、浏览器和外部数据会显著扩大安全边界 | 真实产品如何把 research、browser、code execution 和 connectors 组合起来？ |
| OpenAI | P1 | [Keeping your data safe when an AI agent clicks a link](https://openai.com/index/ai-agent-link-safety/)，2026-01-28 | URL 不只是目的地，也可能是数据外泄通道；对自动抓取 URL 做“是否独立地公开可验证”的检查，并保留用户确认机制 | Agent 浏览网页/调用外部 URL 时，如何防止隐蔽数据外泄？ |
| Google | P0 | [A developer's guide to production-ready AI agents](https://cloud.google.com/blog/products/ai-machine-learning/a-devs-guide-to-production-ready-ai-agents)，2026-02-25 | 覆盖完整生命周期：architecture、MCP/A2A、context engineering、trajectory eval、sandbox/canary/production、session/memory/observability | 从 prototype 到 production 需要补齐哪些系统部件？ |
| Google | P0 | [Architecting efficient context-aware multi-agent framework](https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/)，2025-12-04 | 把 context 视为对结构化 state 的“compiled view”；storage 与 presentation 分离；artifact 按需加载；memory 可检索；handoff 只传必要上下文 | 如何从“拼字符串 prompt”升级到上下文系统？ |
| Google | P0 | [20 questions for the agentic enterprise](https://cloud.google.com/blog/products/ai-machine-learning/20-questions-for-the-agentic-enterprise)，2026 | 企业视角的实操清单：single→multi、enterprise truth、动态工具/skills、runtime、memory、sandbox、guardrails、eval、成本和治理 | 企业部署 Agent 时最容易漏掉哪些问题？ |
| Google | P1 | [Agent Development Kit](https://developers.googleblog.com/agent-development-kit-easy-to-build-multi-agent-applications/)，2025-04 | ADK 的 code-first、多 Agent、容器/Agent Engine 部署路径；适合作为“框架如何把生产边界产品化”的对照样本 | 如何理解一个 Agent framework 的完整栈？ |
| Google | P1 | [Agent Factory Recap: Securing AI Agents in Production](https://cloud.google.com/blog/topics/developers-practitioners/agent-factory-recap-securing-ai-agents-in-production)，2025-10-23 | 生产安全的分层防御、模型前后置安全检查、合规与安全的区别 | 如何建立 Agent 安全的 threat model 和 defense-in-depth？ |

## 2. 三家材料的共同工程原则

### 2.1 先单 Agent，后多 Agent

多 Agent 不是默认的“更先进架构”。OpenAI 和 Google 都建议从单个边界清晰的 specialist 开始；Anthropic 的研究系统则说明，多 Agent 的收益主要出现在：

- 子任务之间可以真正并行；
- 问题是开放式探索，无法提前写死路径；
- 信息量超过单一上下文窗口；
- 不同子任务需要不同工具、提示或权限。

如果子任务高度耦合、共享大量状态、依赖顺序执行，拆成多个 Agent 往往只是增加通信、token、延迟和调试成本。多 Agent 的设计理由应该能写成一个可验证的假设，而不是“看起来更像智能体系统”。

### 2.2 Context engineering 是系统工程，不是 prompt 魔法

值得采用的抽象是：

```text
durable state = session log + memory + artifacts
working context = 针对本次模型调用编译出来的视图
```

具体实践：

- 大文件、完整 API 响应、长 transcript 放到 artifact store，只在需要时加载；
- 记忆可搜索、按需召回，不要永久钉在每轮 prompt 中；
- 工具按需发现，常用工具少量常驻，其余延迟加载；
- handoff 给子 Agent 时只传它需要的 query、artifact 和约束，不默认复制全部祖先历史；
- 把 compaction、summary、filter、relevance retrieval 作为可观察、可测试的处理器，而不是散落在 prompt 拼接代码里。

### 2.3 工具应该是产品接口，而不是“函数清单”

一个生产工具至少应有：明确名称、输入/输出 schema、权限边界、幂等性说明、错误语义、超时/重试策略、示例和验证方式。工具分为三类很有用：

| 类型 | 作用 | 例子 |
|---|---|---|
| Data | 获取执行所需事实 | 查 CRM、读文件、搜知识库 |
| Action | 改变外部状态 | 更新记录、发消息、提交工单 |
| Orchestration | 组合能力或转交 | 调用 specialist、启动子任务、请求人工审批 |

当工具规模变大，直接把所有 schema 塞进上下文会同时伤害成本、延迟和工具选择准确率。优先考虑 tool search、skills、filesystem/code API、返回 handle 而不是返回完整对象。

### 2.4 长时间 Agent 要像分布式系统一样设计

Anthropic Managed Agents 的“brain / hands / session”拆分是一个很强的可迁移抽象：

| 组件 | 应负责 | 不应隐含依赖 |
|---|---|---|
| Brain / model | 决策与计划 | 某一个固定容器、固定工具位置 |
| Harness / orchestrator | 驱动 loop、路由工具、恢复运行 | 用户数据和凭证必须留在本地进程 |
| Session | append-only 事件、可恢复历史 | 当前模型上下文窗口 |
| Hands / sandbox | 执行代码、文件和外部动作 | 直接接触高权限 secrets |

故障处理的目标是：harness 挂掉可以由新实例从 session log 恢复；sandbox 挂掉可以重建并把错误作为工具结果返回；模型升级不会迫使 durable state 绑定某一种 prompt 格式。

### 2.5 评估的是轨迹和状态，不只是答案

建议把每个 Agent eval 定义为：

```text
task     = 输入、环境、权限和成功标准
trial    = 一次完整运行（通常需多次重复）
trace    = 模型调用、工具调用、中间结果、状态变化、错误与恢复
grader   = 对最终结果、过程、工具选择和安全行为的检查器
```

至少建立四层：

1. 工具/节点单元测试：schema、权限、错误、幂等性。
2. 任务级离线 eval：最终结果、必要步骤、禁止动作、资源消耗。
3. 轨迹级 eval：工具选择、重试、是否正确恢复、是否越权、是否需要澄清。
4. 线上观测：分布漂移、未知失败、成本/延迟、人工接管率和用户反馈。

对主 Agent 做独立 evaluator 或 deterministic check，通常比让它自己给自己的成果打分更可靠。对代码/网页任务，尽量让 evaluator 真实运行测试、浏览器操作、截图或检查数据库状态，并要求 Agent 给出证据，而不是只返回“已完成”。

### 2.6 安全边界必须外置

最低限度的控制面：

- 最小权限：每个 Agent/工具只拿到完成任务所需权限；
- 凭证隔离：token 放在 vault/proxy，sandbox 中不可读；
- 确定性 guardrails：规则、schema、策略检查和速率/金额/次数上限；
- 高风险动作人工确认：付款、删除、发送外部消息、合并代码、修改权限；
- 沙箱：浏览器、代码执行、不可信文件和网络访问放到隔离环境；
- prompt injection 防御：把外部文本当作不可信输入，不能让网页/文档改写权限策略；
- staged rollout：内部 sandbox → canary → 小流量生产 → 全量；
- 全链路审计：记录谁触发、模型决定了什么、调用了什么工具、改了什么状态。

## 3. 对当前研究/项目的可执行检查清单

### 3.1 需求入口

- [ ] 该任务是否真的需要 LLM 控制工作流？如果流程完全确定，优先使用普通程序或规则。
- [ ] 成功标准是否能写成可检查的输出、状态或副作用？
- [ ] 哪些动作是只读，哪些动作会改变外部世界？
- [ ] 哪些失败必须停止并交还给人？

### 3.2 Agent contract

- [ ] agent 的职责、输入、输出和完成条件是否唯一且清楚？
- [ ] 工具是否少而专、输入输出可验证、错误可恢复？
- [ ] 是否有 max turns、timeout、budget、retry 和 escalation？
- [ ] 是否记录 trace、tool call、token/cost、latency 和最终状态？

### 3.3 Context/state

- [ ] session log 是否持久化，能否从任意失败点恢复？
- [ ] 大对象是否使用 artifact/file handle，而不是每轮复制进 prompt？
- [ ] memory 是否按需检索，并能删除、修正和审计？
- [ ] handoff 是否只传必要上下文？
- [ ] compaction/summary 是否有单测和回归样例？

### 3.4 Evaluation/operations

- [ ] 是否有至少一组代表性任务集，而不是只测 demo？
- [ ] 是否每个任务跑多次 trial，并保留完整 trace？
- [ ] 是否分别测最终结果、过程、工具选择、安全和成本？
- [ ] 是否有独立 evaluator 或确定性验证器？
- [ ] 是否先 sandbox、再 canary，并能一键停止/回滚？

## 4. 建议阅读顺序

1. Anthropic [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) + OpenAI [A practical guide](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)：建立共同术语和基本架构。
2. Anthropic [Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) + Google [Context-aware multi-agent framework](https://developers.googleblog.com/architecting-efficient-context-aware-multi-agent-framework-for-production/)：理解上下文、记忆和 artifact 的系统化管理。
3. Anthropic [Code execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp) + [Advanced tool use](https://www.anthropic.com/engineering/advanced-tool-use)：理解工具规模化和 programmatic tool calling。
4. Anthropic [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) + OpenAI [Trace grading](https://developers.openai.com/api/docs/guides/trace-grading)：建立 trajectory/trace 评估思维。
5. Anthropic [Harness design](https://www.anthropic.com/engineering/harness-design-long-running-apps) + [Managed Agents](https://www.anthropic.com/engineering/managed-agents)：理解长时间任务、恢复和运行时解耦。
6. Google [Production-ready AI agents](https://cloud.google.com/blog/products/ai-machine-learning/a-devs-guide-to-production-ready-ai-agents) + [20 questions](https://cloud.google.com/blog/products/ai-machine-learning/20-questions-for-the-agentic-enterprise)：用企业上线视角补齐 runtime、sandbox、治理、成本和发布。
7. OpenAI [ChatGPT agent System Card](https://openai.com/index/chatgpt-agent-system-card/) + [URL safety](https://openai.com/index/ai-agent-link-safety/)：专门学习 browser/terminal/外部连接器带来的安全边界。

## 5. 需要保持警惕的地方

- 三家官方材料都带有自身平台的产品视角；架构原则可以迁移，产品名称、API、可用性和性能数字必须在实现前重新核对。
- 厂商给出的内部 eval 提升和客户案例不能直接当成普适结论。应关注任务定义、基线、成本、失败样本和是否公开了完整方法。
- “Agentic”不等于“完全自治”。生产系统更可能是 Agent + deterministic workflow + policy gate + human escalation 的混合体。
- 2026 年产品路线仍在快速变化。例如 OpenAI 在 AgentKit 页面更新中已公告 Agent Builder/Evals 的停止安排；因此不宜把某个可视化产品当成长期架构依赖，代码化的 Agents SDK、Responses API 或自有 runtime 更适合做稳定边界。

## 6. 待继续补充

- [ ] 各家官方 Agents SDK/ADK 的 session、sandbox、MCP 和 tracing 具体 API 对比。
- [ ] 生产指标模板：成功率、任务完成时间、TTFT、tool-call error rate、human takeover rate、cost per successful task。
- [ ] Agent threat model：prompt injection、tool poisoning、data exfiltration、权限提升、供应链和多租户隔离。
- [ ] 针对 URSA 的 Agent contract、trace schema 和最小可行 eval suite。

## 7. GitHub 生态补充

这些仓库不是同一种资源，应该按用途吸收：

- [NirDiamant/agents-towards-production](https://github.com/NirDiamant/agents-towards-production)：生产组件和部署教程；
- [microsoft/multi-agent-reference-architecture](https://github.com/microsoft/multi-agent-reference-architecture)：企业多 Agent 架构与治理；
- [FareedKhan-dev/all-agentic-architectures](https://github.com/FareedKhan-dev/all-agentic-architectures)：可运行的架构模式教材；
- [agentevals-dev/agentevals](https://github.com/agentevals-dev/agentevals)：从 trace 做 Agent 评估；
- [github/gh-aw](https://github.com/github/gh-aw)：安全隔离、只读默认权限和 staged writes 的真实案例；
- [korchasa/awesome-ai-agents](https://github.com/korchasa/awesome-ai-agents)：只作为广泛发现入口，不作为质量证明。

这里的核心方法不是把所有链接搬进列表，而是为每个来源建立：来源主张、工程解释、适用边界、反例、验证计划和最后核验日期。第一轮判断可以由 AI 起草，但必须标记为 ai-drafted，并与原始主张和后续人工/实验修订分开保存。
