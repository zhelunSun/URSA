# ADR-003：采用有边界的插件化，而不整体迁移通用 Harness

> Status: accepted on 2026-08-25 for post-v0.5.3 evolution. 本 ADR 不修改 `0efd090`、
> v0.5.3 acceptance/live evidence、冻结 panel/gold 或第一章既有 claim。

## Context

v0.5.3 已把 Manager–Scientist–Engineer 的模型决策接入一个由 ExpertsRS 掌握控制权的领域 runtime。
AutoGen AgentChat 负责 model-facing agents、messages 和 team state；ExpertsRS 负责 typed plan、validator、
eligible-node、tool binding、permission、artifact、checkpoint、terminal state、report closure 和 evaluator export。
因此当前存在框架会话层与领域控制层，但 AutoGen 不是领域事实的权威来源。

DeepSeek Harness 使用 Cordis 组织插件树。其插件向 shared context 提供 services、typed events 和 reversible
effects；LLM adapter、tool registry、session log、agent loop、persistence、sandbox、approval 与 telemetry
均可按 profile/bundle 组合。该设计适合需要多产品形态、第三方能力、动态生命周期和通用执行世界的
agent harness，但其 Node/TypeScript/Cordis 运行模型不是当前 Python EO 工具链的原位替换。

研究系统还具有通用产品不同的约束：workflow validity、delivery obligations、终态和证据语义必须在所有
条件中保持一致。若这些也能被任意插件替换，实验 profile 可能改变“何为有效计划、成功或证据”，从而
破坏可比较性和 claim 边界。

## Decision

ExpertsRS 采用 **bounded plugin architecture**：

1. 保留一个稳定、不可绕过的 domain kernel；
2. 只把不定义论文成功语义的外部能力置于显式 port 后；
3. 先用 Python `Protocol`、依赖注入、显式 registry 和版本化 profile，不引入通用插件管理器；
4. DeepSeek Harness/Cordis 作为持续架构参照和可选外部 backend，不整体迁移；
5. 所有 adapter 替换必须通过 parity、schema、privacy 和 evaluator closure Gate。

### Stable domain kernel

以下对象不允许被部署 profile 静默替换或降级：

- `RunRequest/RunResult` 公共合同和 schema version；
- `TaskSpec/WorkflowGraph`、validator 与 eligible-node；
- planned action 到 bound execution 的一致性；
- runtime-owned delivery obligations 和 report evidence closure；
- actor/plan/node/artifact provenance；
- budget、terminal status、privacy 和 false-success 语义；
- planned workflow graph 与 observed process graph 的区分；
- evaluator-private 信息与 Agent context 的隔离。

这些对象可以版本化演进，但必须形成新版本、迁移说明和相称的证据重跑，不能作为普通插件配置变化。

### Replaceable capability ports

按收益和依赖顺序只冻结五个端口方向：

| Port | 首个 provider | 后续候选 | 不拥有的语义 |
| --- | --- | --- | --- |
| `DecisionProvider` | AutoGen 0.7.5 | direct model、MAF、Harness bridge | 角色时序、计划有效性、终态 |
| `ExecutionBackend` | local in-process | subprocess sandbox、container、remote/Harness | 工具准入、参数合同、完成判定 |
| `EventStore` | JSONL/state compatibility | SQLite、durable store | event vocabulary 和 actor attribution |
| `ScientificConstraintProvider` | NoOp/Fake | Chapter 2 reviewed knowledge provider | 在线学习准入、evaluator gold |
| `TelemetrySink` | manifest/JSON | OpenTelemetry、experiment DB | 运行事实和论文 claim |

tool kits 可以按 provider/registry 组织，但 runtime 仍拥有 allow-list、effect、输入输出合同和权限决定。
外部 evaluator 不是系统插件；它只消费冻结 export，并保持自己的 gold/fault/grader 私有视图。

## Direct code reuse policy

复用分为三档：

1. **Architecture reuse（默认）**：借鉴 service definition/provider/consumer、append-only durable facts、
   context projections、guarded execution、profile composition 和 sandbox enforcement reporting；
2. **Backend reuse（条件式）**：若需要真实 shell/sandbox/remote execution，可将 DeepSeek Harness 的独立
   能力作为 sidecar/backend，经 IPC/CLI/RPC 适配到 `ExecutionBackend`；
3. **Source transplant（例外）**：默认不把 Cordis-bound agent loop、session 或 tool packages 移植到
   Python。只有删除的自研代码和获得的稳定能力明显多于跨语言胶水、重复类型和维护负担时才提案。

DeepSeek Harness 仓库使用 MIT license，但任何源码复制仍须逐包检查 license 与 third-party notices，
保留版权/许可证、记录上游 commit、修改和本仓 provenance。复用的基础设施不得重标为论文方法创新。

## Rationale

- 当前系统规模小、六个安全工具、单机短任务，不需要动态发现、热卸载或复杂插件生命周期；
- 显式 port 已能获得测试替身、框架替换、profile composition 和依赖倒置的大部分收益；
- 领域内核保持稳定，才能让 AutoGen/direct/Harness 等 adapter 条件具有可比性；
- 将 sandbox 作为 `ExecutionBackend` 比迁移整个 agent loop 更直接地补齐当前真实缺口；
- Cordis 的 shared context 很强，但在小型 Python 研究系统中可能演变成隐式 service locator，增加初始化
  顺序、组合爆炸、调试和安全风险；
- “思想与 SOTA 对齐”应体现为边界、事实源和验证 Gate，而不是依赖名称或代码量。

## Adoption gates

完整 Harness 评估只有在 PLAN 第 13 节列出的需求触发条件达到至少三项后启动。原型必须位于独立分支，
只运行一条普通 NDVI parity 和一条 task-11 recovery parity，并满足：

1. domain contracts、delivery closure 和两类图保持兼容；
2. v2 evaluator closure 不下降且没有新增 false-success；
3. 获得可量化的 sandbox、durability 或维护收益；
4. adapter/bridge 没有产生第二套事实源；
5. 版本、回滚、成本和证据重跑范围获批。

任一 Gate 失败即停止 Harness 原型，不影响当前 runtime。

## Consequences

- 近期优先抽取 `DecisionProvider`、`ExecutionBackend` 和版本化 `EventStore`，不实现 Cordis clone；
- AutoGen 保留为已验证 adapter，生命周期状态不触发紧急迁移；
- plugin、MCP、dynamic subagent、jobs、Web UI 和 OTel 仍是产品化/求职支线，不阻塞论文；
- 每个新 provider 必须显式声明版本、能力、权限、错误映射和 evidence identity；
- 当前系统可描述为“具有 harness-style runtime capabilities 的领域研究系统”，但在完成通用 plugin、
  process sandbox、durable session 等能力前，不描述为通用或生产级 agent harness。

## References

- DeepSeek Harness architecture: <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md>
- DeepSeek Harness capability seams: <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/capability-seams.md>
- DeepSeek Harness sandbox: <https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/sandbox.md>
- DeepSeek Harness license: <https://github.com/deepseek-ai/deepseek-harness/blob/master/LICENSE>

