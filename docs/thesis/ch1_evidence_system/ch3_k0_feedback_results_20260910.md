# K0 共同反馈轮结果：保留负例，尚未通过领域交付

2026-09-10。执行前合同见 [共同反馈轮](ch3_k0_feedback_round_20260910.md)，原始首轮见 [batch-01 结果](ch3_k0_results_20260910.md)。
代码检查点 ead8a59，输出 ExpertsRS/results/ch3_k0_20260910/batch-02；本轮没有临场修改或补跑。

## 本轮结论

共同提示修订没有让正常任务完成：U 仍澄清，G 输出伪造完成并被格式校验拒绝。缺 AOI 两边仍合理询问边界；依据不足时 G 正常停止，U 的解释内容基本合理但未遵守 JSON 协议，因此系统失败。不能宣称修订有效，也不能据此归因于某一提示句或多智能体架构。

| 案例 | 实际终态 | 模型/工具调用 | tokens | 秒 | 内容判读 |
| --- | --- | --- | --- | --- | --- |
| 正常 U | needs_clarification | 1 / 0 | 1,716 | 3.140 | 改为确认类别编码；没有交付 |
| 正常 G | failed | 1 / 0 | 1,649 | 5.297 | 未计算却声称已有表/图，生成虚构数值和引用；schema 拒绝 |
| 缺 AOI G | needs_clarification | 1 / 0 | 998 | 1.219 | 具体索取研究区边界，合理未完成 |
| 缺 AOI U | needs_clarification | 1 / 0 | 1,145 | 6.984 | 具体索取研究区边界，合理未完成 |
| 依据不足 U | failed | 1 / 0 | 1,671 | 32.516 | 原始普通文本解释依据与能力不足；JSONDecodeError，未形成合法停止决策 |
| 依据不足 G | controlled_stop | 1 / 0 | 1,415 | 3.187 | 保留 verified habitat 结论；仍有 tree (urban-forest) 措辞风险 |

总计 6 次决策/6 次原始响应，7,673 prompt + 921 completion = **8,594 recorded tokens**；工具 0 次；各例 wall 合计 52.343 秒。六槽均执行，无未运行/中断槽、无 batch_error，无 SDK 自动重试。精确响应模型均为 deepseek-ai/DeepSeek-V4-Flash，finish_reason 均为 stop；该字段不是任务成功。没有按价格估计货币成本。

本地客户端未启用响应缓存；供应商响应包含 prompt_cache_hit_tokens，不能把客户端 cache=false 表述为服务端从未缓存。用量仍取原始响应所报的全部 prompt/completion tokens。

## 失败具体发生在哪一层

1. **类别语义与澄清：**工具合同已经提供 codes 0..7 和 class_order，实际实现中也有固定类别。U 提问还正确列出了对应关系，因此不是缺少原始数据或必须请求作者重新确定分类法；不过序列到编码的对应没有显式字典，下一版可使资源语义更直接。现有证据只说明未交付，不能推断补字典一定解决。
2. **G 虚构完成：**原始响应在正常任务首步直接 final，包含虚构产物 ID、虚构数字和额外 factual_deliverables 字段。run_single 在 exact-key schema 检查时先抛 ValueError，未到 validate_final。可报告“错误最终输出被运行时拒绝”；不能报告本次已触发数值事实核验或语义幻觉识别。原始响应和失败状态均保留。
3. **U 非结构化输出：**生态问题响应为普通英文段落，先于角色 schema 在 JSON 解析处失败。内容保留了验证依据边界，但调用方没有收到合法的结构化停止理由，external_checks 中 answer 为空，须由原始 journal 内容复核；不能把它算成正确停止。
4. **接口歧义待修：**共同提示允许能力/依据不足时 stop，而 Manager 初始允许值仅 clarify/handoff，停止由 Scientist 承担。这一接口不一致值得修正；当前 U03 首错仍是非 JSON，不将接口歧义未经验证地当作其唯一原因。
5. **G 生态措辞：**没有把产品图判成已验证核心生境，但 tree (urban-forest) 和 patch 的用词仍超出当前 class count/map 工具的严格表达；保留措辞风险，不评为无保留科学正确。

## 检查与证据边界

- 运行前共享工具/输入/报告边界测试 6 passed；本轮完整工程回归 **154 passed，30 个 Rasterio 同类弃用 warning**。没有新增测试数量冒充 live 改善。
- external_checks.json 共六行；正常 U/G 的 product_checks_pass 均 false。非完成任务该值为 null，传输字段即使全 true 也不说明模型语义或系统任务通过。
- 本轮无产物、无图件，图件审计/视觉验收均不适用；不能复用首轮地图来补本轮交付。
- 两批 public_packets 字节身份相同；两边获得同一共同反馈文本，模型、预算、顺序、资源和工具不变。U 保留角色/图约束，G 保留单工具循环。
- 两批不是纯提示消融：ead8a59 包含 065ec61 已记录的 G 空交付门槛和共享交付要求显式化。开发反馈用过这些题，不能当 held-out 或重复独立样本。
- 新的只读上下文审查原始响应与失败位置；结论和文件 hash 写入 post_run_review/content_review.json。该复核不是作者接受、独立科学真值或正式盲评。
- batch-01 和 batch-02 分别归档，原始运行文件不进入 Git；本地 ZIP/逐文件 hash 可检查完整性，尚不是异机备份。

## 下一步价值

本轮将“偏保守澄清”“格式不合法”“未执行却声称完成”分开定位，为下一里程碑提供了实际负例。先修资源元数据表达和角色终态协议，做保留响应的离线回放检查，再冻结下一次准入设计；不在本轮继续追加 live。正常交付稳定后再补资源绑定 resume 和知识服务。

面试与架构结论见 [research agent 工程/算法说明](research_agent_interview_20260910.md)。可以展示运行边界如何保留和拒绝失败；仍不具备稳定领域自主交付或多智能体优势的证据。

归档回执：`ch3-k0-six-case-20260910-batch02.zip`，45669 bytes，SHA256 `e8ed8b76cac189d070e9eb339c5e853a538b472395328e3e3a28e966ad861f27`；41 个文件逐项 hash 与 ZIP CRC 校验通过。本地留存，未声称异机备份。
