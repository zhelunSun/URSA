# 实验谱系与 DeepSeek V4 Flash 当前实战检查

日期：2026-09-09。研究者提醒 prototype 与升级过程已有多轮实验，并授权使用现有 API、
以 DeepSeek V4 Flash 为基准开展实际测试。

## 先纠正“缺乏实战”的表达

URSA 不是只有工程测试、从未运行真实模型。原型和升级阶段都有实战；当前要区分三个问题：
已经做过什么、原始记录现在能否复核、已有实验是否覆盖新版本的领域任务及论文主张。
“原始包本机缺失”不等于“实验没做过”；“做过集成实验”也不自动证明方法效果。

| 阶段 | 实验事实及当前可用性 | 支持范围 |
| --- | --- | --- |
| Prototype / 已发表系统 | 原论文 20 请求评测；语义副本 `ExpertsRS/evaluation/ch1/benchmark_20_original.json` 可用，原运行目录本机未找到；保护 tag `prototype-notebook-v0-20250307` | 已发表可行性基础；不能拿不同输入/代码的现有结果直接做同条件升级前后比较 |
| M1 / D2 | scripted provider、真实栅格和工具；修补/停止、计划修订、产物复用与权限检查；本轮重新生成的本地诊断可用 | 工程与最小机制诊断。当前生成时间不能伪装成历史包原时间 |
| 08-14 真实模型 smoke | `a4006dc`、Paratera DeepSeek-V4-Flash；NDVI、故障恢复、澄清三例。历史摘要可用，raw 包待恢复 | 真实模型与工具集成，含故障及诚实终态 |
| 08-14 5×3 pilot | 运行时 `2aeecd3`、runner `30c8075`；摘要记载 15/15 evaluator closure、166,400 tokens；当前 raw 缺失 | 当时版本的集成检查，区别于后来的最终 v2 包 |
| 最终 v0.5.3 5×3 | `0efd090`；摘要记载 15/15 v2 closure、215,500 tokens、391.582 秒；5 completed、7 controlled-stop、3 clarification；raw 索引和 SHA 可用，文件待恢复 | 最终 v2 的有界 live 证据；不等于 100% 任务成功率或独立机制效果 |
| 澄清后继续 | rule/live UserAgent 隔离 fixture，`v2_user_agent_smoke_bb7c8bf`；原包待恢复 | 模拟用户接口与 resume，不是用户研究 |
| 09-09 北京新链 | v0.5.4.dev0；两次 scripted-offline 真实产品运行，第一次图件裁切保留，第二次复核通过；raw/ZIP 当前存在 | 分类组成、同源地图和报告接线；尚不证明模型自主组织该领域链 |

原始来源：[08-14 smoke](paratera_live_smoke_result_20260814.md)、[08-14 pilot](paratera_pilot_result_20260814.md)、
[最终结果表](v053_results_table.md)、[最终包索引](v053_evidence_index.md)、
[北京链验收](audits/20260909_domain_toolchain_closeout.md)。旧文“文件存在”描述的是当时检查状态，
当前本机可用性以本表和 09-09 审计为准。最终前的 14/15、13/15 等失败轮次也保留其历史记录，不合并成一次全通过运行。

此前请研究者从 laptop 同步的，正包括升级阶段的最终 5×3、smoke/澄清/验收等运行证据。
建议取回整组 `ExpertsRS/results/ch1_d3_light/` 对应目录及配套 manifest，先按旧 SHA 验证，不用新实战替换旧文件。

## 本轮先做什么

先验证现有 runtime 在指定基准模型上是否仍能完成已定义的三类任务，再推进北京 profile 的 live 接入。
这里复用开发 smoke，不能称 held-out 测试或受控模型排名；不是重做旧历史包，也不涉及第二章知识效果。

- 入口：`scripts/run_flash_runtime_smoke.py`；同一 `ExpertsRSSystem.run` 与 AutoGen provider。
- 渠道：现有 SiliconFlow API；模型精确 ID `deepseek-ai/DeepSeek-V4-Flash`，只读 `/models` 已返回该 ID。
- 模式：显式 `enable_thinking=false`、temperature=0、top_p=1、每次最多 4,096 completion tokens，120 秒请求超时、零 SDK 重试。
- 任务顺序：task-02/B2（NDVI），task-11/B3（一次受控故障后的局部恢复），task-13/B2（语义澄清）。
- 每例沿现有 panel 上限：12 次模型决策、10 次工具调用、600 秒、70,000 recorded tokens。
  总上限 3 例 / 36 次决策；token 阈值按返回用量在下一请求前检查，不宣称为绝不超出的账户扣费硬限。
- 评价使用既有 v2 evaluator；额外核查模型响应正常结束。任一失败停止批次，不自动反复尝试直至成功。
- 每次决策前落盘意图；AutoGen LLMCallEvent 保存原始模型请求/响应正文与 usage，随后才解析角色 JSON。
  不记认证头；原始输出若意外回显 key 则脱敏。失败解析也保留响应和其用量。
- 新目录只创建不覆盖；保留实际模型标识、代码/输入/evaluator hash、所有失败及未运行槽。
- 费用没有账单依据则留空；区分 API 实际响应使用量与 runtime 成功解析后记入的使用量。

官方接口依据：[SiliconFlow Chat Completions](https://api-docs.siliconflow.cn/docs/api/chat-completions-post)。
读取日期 2026-09-09；接口列出上述模型 ID 与 `enable_thinking` 字段，实际能力仍以本轮结果判断。
ProviderConfig 新字段默认 None，不改变旧模型默认参数；classification-v1 的 live 禁用本轮保持。

## 当前运行回执

待本轮三例实际运行后追加。源码/配置检查点必须先推送；结果仅以实际回执填写，不预填通过。
