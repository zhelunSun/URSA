# K0 六例开发小样：运行前合同

2026-09-10。研究者授权“开始推进”，沿现有 API / DeepSeek V4 Flash 六例设计实施；不是正式测试集。

U：`ClassificationComparisonSystem` 继承 ExpertsRSSystem 的 run/drive、Scientist 图验证、eligible-node 执行和报告核验；
只替换领域 provider 上下文、公共交付义务与共享输入/输出适配。G：一个 AutoGen AssistantAgent，自行选择工具、停止或报告，
没有 URSA 角色分工、图提交和 eligible-node 策略。两边使用同一 `create_model_client` 配置，均以 JSON 决策调用工具。
通用代码 Agent/现成外部产品未接入；本对照只能称单 agent 工具循环。

## 共同条件

- 数据：沿 preparation-03 冻结公共包、北京既有分类/AOI；资源文件与 AOI 组件逐项 hash 核验。
- 仅两个工具：summarize_classification / plot_classification_map，真实计算复用 LocalToolExecutor 与既有产品实现。
- `classification_bridge` 共同解析逻辑资源/类型/年份、校验原始输入和中间产品、验证输出归属/字节身份。
  U 额外保持图合法性、节点依赖与执行准入，这正是本对照保留的组织差异。
- 工具 schema、类型、参数、说明与数值事实均相同；模型只收到逻辑 ID、类型、hash 和无路径事实。
  两边获得相同 factual_deliverables（确定性产品事实），最终需引用实际产物并保持数值与范围，不能替任一方补答案。
- K0=knowledge unavailable；当前不提供知识工具，也不模拟已支持的知识返回，不评价知识推理。
- 公共 case ID 改为 K0-01/02/03，避免原开发文件名中的 MISSING/UNSUPPORTED 暗示预期结果。
- 原 state 与评分资料只由宿主准备/外部审查读取，未作为 agent 输入。模型没有 shell、任意代码/文件读工具；
  宿主仍非 OS 沙箱。未来开放代码工具时必须另验隔离，当前不能据此称自由代码 Agent 公平比较。

## 调度、预算与首错

固定顺序：K0-01 U/G，K0-02 G/U，K0-03 U/G。对应组成任务、缺 AOI、依据不足；每个条件每任务一次。
模型精确 ID deepseek-ai/DeepSeek-V4-Flash，SiliconFlow 官方 endpoint；thinking=false，temperature=0，top_p=1，
completion cap=4096，timeout=120 秒，SDK retries=0，cache=false。角色/工具描述不在看到 live 结果后调整。
每例 12 决策/10 工具/600 秒/70,000 recorded tokens，总计最多 72 决策；所有角色/失败响应计入实用量。
token 预算在响应返回后检查，有最后响应超出阈值的可能；同步遥感工具不能被 asyncio 抢占，因此墙钟不是进程硬限。

保留每例一个原始 attempt；任务/格式失败保留后继续其余槽，认证/网络异常或不可解释基础设施异常停止批次。
本批不修提示、不补跑、不选择最好结果。后续若使用允许的一轮开发反馈修订，必须新配置和新批次并保留本批。
Journal 写入每次意图及 AutoGen 原始请求/响应/usage，先保存响应再解析 JSON；不记录认证头，回显 key 脱敏。

## 评价冻结

评分在模型执行后独立进行。既有外部同产品 reference.json SHA：
`48ed17afda7de04a456b99470ceb437ce812a4f83f40e62204c2e57409221881`。
它与被测工具共享计算语义，只支持同产品一致性，不能当独立分类真值。

组成任务：终态+产物（表、图）+八类整数逐项精确+比例绝对误差 ≤1e-8+valid/nodata/总像元守恒+来源 hash一致；
图件用现有 scientific-figures 合同/manifest 做确定性审计，再查看 PNG；报告数值/分母/范围另作内容复核。
缺 AOI：必须具体识别研究区边界缺失，合理澄清/停止，不虚构 AOI、不声称已完成研究区统计。
依据不足：必须保留已验证生境结论，具体说明缺少定义/生态证据；即使输出描述图也不算完成生境任务。
后两项先只机器汇总终态与原始话语，最终有界内容复核；单纯 stop/clarification 不自动记为正确。

分别报告任务交付、合理未完成、产物一致性、解释边界、模型/工具调用、tokens、wall time、人工介入及基础设施错误。
六例一次开发运行不能给出统计优越性、机制独立效应或知识贡献。输出/版本/原始失败留存后再决定下一步价值。

入口：`scripts/run_ch3_k0_comparison.py`（需要显式 --allow-api、新目录和已推送的干净检查点）。
默认 classification-v1 的 live 仍被禁止；新增 `classification_admission=ch3-k0-dev-v1` 只用于上述有界适配器，
不是将旧 NDVI 提示原样开放给领域任务，也未开放任意领域/数据/工具。
