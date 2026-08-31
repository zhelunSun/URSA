# 华为 Agent Harness 面试：最小知识地图

> 版本：2026-08-19  
> 定位：第一轮基础复习入口，不是完整八股答案集。  
> 后续用法：先建立概念地图，再以面经逐题扩写口述卡，并映射到 URSA 第一章。

## 0. 这份地图解决什么问题

目标不是重新学习一遍完整的机器学习或计算机专业，而是建立一套面试时可快速调用的知识索引：

1. 听到一个术语，知道它在整套系统中的位置；
2. 能在 30～60 秒内先给出准确主干；
3. 被追问时，能继续展开原理、工程选择和适用边界；
4. 知道哪些内容需要映射到自己的项目，哪些只需具备基础常识。

每个概念最终都按下面的口语顺序准备：

```text
一句话定义：它是什么？
最小机制：它大致怎样工作？
工程作用：为什么系统需要它？
边界与权衡：它什么时候失效，替代方案是什么？
项目连接：我在哪里实际使用、观察或改进过它？
```

这不是要求面试时机械念五点。实际回答先说前三项，面试官继续追问时再展开边界与项目。

## 1. 岗位边界：Harness 到底是什么

华为云 AgentArts 的公开定义是：`Agent = Model + Harness`。Harness 是模型之外的基础设施，决定模型能看到什么、能做什么、何时停止，以及出错时如何处理。

因此 Harness 岗位位于三类工作的交叉点：

```text
                   模型与推理
           Transformer / LLM / RAG
                         │
                         ▼
软件与分布式系统 ─── Agent Harness ─── Agent 产品与交互
状态 / 并发 / 沙箱       │              工具 / 人机协作
恢复 / 可观测性          │              长任务 / Coding Agent
                         ▼
                 评测、安全与反馈闭环
```

它不是纯模型训练岗，也不是简单的 LangChain 应用开发。最低能力面应包括：

- 理解模型怎样接收和生成信息；
- 理解检索、上下文和工具如何影响模型行为；
- 能设计 Agent loop、状态、执行环境和恢复机制；
- 能用评测与 trace 判断某种 Harness 设计是否真的更好；
- 能把研究想法实现为稳定、可控、可验证的软件系统。

### 一页总览

| 层 | 核心问题 | 第一轮最重要的节点 |
|---|---|---|
| 数学与表示 | 模型如何用数字表达与比较信息？ | 向量、点积、范数、余弦、Softmax |
| 神经网络与 Transformer | LLM 如何编码上下文并生成 token？ | Embedding、QKV、Attention、mask、KV Cache |
| LLM 训练与调用 | 模型能力从哪里来，调用时能控制什么？ | Pretraining/SFT/对齐、采样、Structured Output |
| 检索与 RAG | 外部知识怎样被召回、排序和验证？ | chunk、dense/sparse、ANN、rerank、指标 |
| Agent 控制流 | 模型如何根据反馈持续行动？ | workflow/agent、ReAct、planning、loop、termination |
| Harness Runtime | 模型之外谁管理状态、工具和执行？ | context、memory、artifact、MCP、sandbox、resume |
| 生产保障 | 怎样知道系统有效、可靠且安全？ | trace、grader、observability、HITL、injection 防御 |
| 软件基础 | 上述系统依赖哪些通用工程能力？ | Python async、HTTP/RPC、数据库、Linux/Git、算法 |

## 2. 优先级规则

### P0：面试前必须能口述

能给定义、原理和一个工程例子；常见追问不能完全空白。

### P1：知道位置和主要权衡

第一轮不必推导，但必须知道它解决什么问题、与相邻概念有什么区别。

### P2：岗位或面试信号明确后再深入

包括完整数学证明、训练系统细节、特定框架 API 和冷门论文方法。

总体复习顺序：

```text
数学与表示
  → 神经网络与 Transformer
  → LLM 训练和推理
  → 信息检索与 RAG
  → Agent 基本控制流
  → Harness 运行时
  → 评测、安全与生产化
  → 项目映射和面经作答
```

---

# 第一层：数学与表示基础

这部分的目标不是证明定理，而是确保 Embedding、Attention、RAG 和模型采样中的公式可以说清楚。

## 3. 标量、向量、矩阵、张量（P0）

**口语锚点：**标量是单个数；向量是一组有顺序的数；矩阵是二维数表；张量是对更高维数组的统称。神经网络的大部分计算，本质上是张量经过参数化变换。

最低要求：

- 看懂形状，例如 `X ∈ R^(n×d)` 表示 n 个 d 维表示；
- 知道矩阵乘法要求内维相等；
- 能解释 batch、sequence length、hidden dimension 分别是哪一维。

常见追问：Attention 中 `QKᵀ` 的形状是什么？为什么结果能表示 token 两两之间的相关性？

## 4. 点积、模长与范数（P0）

**口语锚点：**点积把两个同维向量压成一个数，可以理解为方向一致程度与模长的共同作用；范数用于衡量向量大小，最常见的是 L2 范数。

核心公式：

\[
x \cdot y = \sum_i x_i y_i,
\qquad
\|x\|_2 = \sqrt{\sum_i x_i^2}
\]

工程连接：

- Attention 用 query 与 key 的点积计算匹配分数；
- 向量检索可以用点积进行近邻排序；
- normalization 会改变不同距离度量之间的关系。

## 5. 余弦相似度、欧氏距离与归一化（P0）

**口语锚点：**余弦相似度主要比较方向，欧氏距离比较空间位置；是否归一化决定了两者在工程上是否等价。

\[
\cos(x,y)=\frac{x\cdot y}{\|x\|\|y\|},
\qquad
d(x,y)=\|x-y\|_2
\]

当 `x`、`y` 都经过 L2 归一化时：

\[
\|x-y\|_2^2 = 2-2(x\cdot y)=2-2\cos(x,y)
\]

所以三种排序在该条件下等价：

- 余弦相似度从高到低；
- 点积从高到低；
- 欧氏距离从低到高。

边界：不能泛化为“所有 Embedding 天然归一化”。必须检查模型说明和调用配置；向量数据库的索引 metric 也必须与训练/归一化方式匹配。

## 6. Logit、概率与 Softmax（P0）

**口语锚点：**logit 是模型尚未归一化的打分，Softmax 把一组打分转成总和为 1 的概率分布。

\[
p_i=\frac{e^{z_i}}{\sum_j e^{z_j}}
\]

需要理解：

- 加同一个常数不会改变 Softmax 结果；实现时常减去最大 logit 以提高数值稳定性；
- logit 差距越大，输出分布越尖锐；
- Attention 中 Softmax 把 query 对不同 key 的匹配分数变成权重；
- 生成中温度会缩放 logits，而不是直接“增加模型知识”。

## 7. 交叉熵、梯度与优化（P1）

**口语锚点：**交叉熵衡量预测概率与目标分布的差异；反向传播计算参数对损失的梯度；优化器沿降低损失的方向更新参数。

最低要求：

- 知道训练与推理的区别；
- 知道学习率过大或过小的问题；
- 能解释参数、梯度、loss、epoch、batch；
- 不要求第一轮手推复杂反向传播。

---

# 第二层：神经网络与 Transformer

## 8. 神经网络、线性层与激活函数（P0）

**口语锚点：**神经网络是多层参数化函数的组合；线性层做特征变换，激活函数引入非线性，使多层网络不退化为一个线性变换。

\[
y=f(Wx+b)
\]

需要知道：参数由训练学习；推理时参数通常固定；常见激活包括 ReLU、GELU、SiLU。

## 9. Embedding（P0）

**推荐口述：**

> Embedding 是把离散对象或复杂输入映射为连续稠密向量的可学习或预训练表示。相似对象通常会在表示空间中具有相近的几何关系。对 LLM 来说，token embedding 是模型的输入表示；对 RAG 来说，sentence/document embedding 用于语义检索。它不只等于“词向量”，对象也可以是句子、文档、图片、用户或代码。

最低机制：

- token embedding 常可理解为从 embedding matrix 中按 token ID 查表；
- 检索 embedding 通常由编码器对整段文本编码并池化得到；
- 表示空间的几何意义由训练目标塑造，而不是人工规定。

边界与追问：

- token embedding 与 sentence embedding 有什么区别？
- 为什么同一个词在上下文中的 hidden state 会不同？
- Embedding 维度越高是否一定越好？
- 相似度度量为什么必须匹配模型训练方式？

## 10. Tokenization（P0）

**口语锚点：**Tokenizer 把原始文本切分成模型词表中的 token ID；模型处理的是 token 序列而不是原始字符或“词”。

需要知道：

- BPE、WordPiece、SentencePiece 的大致目的；
- token 数影响上下文容量、延迟和成本；
- 中文字符数不等于 token 数；
- tokenizer 属于模型接口的一部分，不能随意替换。

## 11. Residual、LayerNorm 与 FFN（P0）

**口语锚点：**Residual 为信息和梯度提供直通路径；LayerNorm 稳定每个 token 表示的数值分布；FFN 对每个位置独立进行非线性特征变换。Transformer block 不只有 Attention。

常见追问：

- 为什么残差有利于训练深层网络？
- LayerNorm 与 BatchNorm 的对象有什么区别？
- Attention 负责 token 间交互，FFN 主要负责什么？

## 12. Q、K、V 与 Scaled Dot-Product Attention（P0）

**推荐口述：**

> Attention 可以理解为一次可学习的软检索。当前位置生成 Query，与各位置的 Key 做匹配，Softmax 得到权重，再对相应 Value 加权求和。除以 `√d_k` 是为了避免维度增大后点积方差过大，使 Softmax 过度饱和。

\[
\mathrm{Attention}(Q,K,V)
=\mathrm{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V
\]

必须能解释：

- Q、K、V 都是输入表示经过不同线性投影得到；
- `QKᵀ` 产生位置之间的匹配矩阵；
- Softmax 后每个 query 获得对所有允许 key 的权重；
- 与 V 相乘得到聚合后的新表示。

## 13. Self-Attention、Cross-Attention 与 Multi-Head（P0）

**口语锚点：**Self-Attention 的 Q/K/V 来自同一序列；Cross-Attention 的 query 与 key/value 来自不同序列；Multi-Head 让模型在不同子空间并行学习不同关系，再拼接映射。

边界：多头并不保证每个头都有清晰的人类语义，也不能简单说“一个头负责语法、一个头负责语义”。

## 14. Causal Mask 与双向注意力（P0）

**口语锚点：**Causal Mask 阻止当前位置看到未来 token，使自回归模型只能根据前缀预测下一个 token；BERT 类编码器通常允许双向注意力。

常见比较：

- GPT：decoder-only、causal language modeling；
- BERT：encoder-only、双向表示学习；
- encoder-decoder：输入编码与输出自回归解码结合。

## 15. 位置编码与 RoPE（P1）

**口语锚点：**Attention 本身不感知序列顺序，需要把位置信息注入表示或注意力计算；RoPE 通过对 Q/K 做与位置相关的旋转，使点积携带相对位置信息。

最低要求：知道绝对位置、相对位置和 RoPE 的差异，不要求先推导复数形式。

## 16. Context Window 与 Context Rot（P0）

**口语锚点：**Context window 是一次推理中模型可以接收的 token 范围；没超过硬上限不代表信息都能被同样可靠地利用，长上下文还会带来成本、延迟和相关信息被干扰的问题。

工程连接：compaction、retrieval、artifact、tool search 和 sub-agent 都是在管理有限的上下文与注意力预算。

## 17. Prefill、Decode 与 KV Cache（P0）

**口语锚点：**Prefill 并行处理已有输入，计算各层表示和 KV；Decode 每次生成新 token，并复用已有 KV Cache，避免把整个前缀重复计算。

需要知道：

- 长 prompt 主要增加 prefill 成本；
- 长生成主要增加逐 token decode 延迟；
- KV Cache 用显存换计算；
- Prompt Cache 与单次生成内部的 KV Cache 不是同一个抽象。

## 18. Temperature、Top-k、Top-p（P0）

**口语锚点：**这些参数改变的是从模型概率分布中怎样采样，不会向模型注入新知识。低温通常更稳定，高温更发散，但不能把低温等同于“没有幻觉”。

---

# 第三层：LLM 训练、对齐与调用

## 19. Pretraining、SFT、RLHF/RLAIF、DPO（P0）

**口语锚点：**预训练让模型从大规模数据学习通用预测能力；SFT 用高质量示范教模型遵循任务格式；偏好对齐使用人类或 AI 偏好信号，使输出更符合有用性、安全性和风格要求；DPO 是不显式训练在线 RL policy 的直接偏好优化方法之一。

第一轮只需说清训练目标和数据来源的区别，不必先展开 PPO/GRPO 推导。

## 20. Fine-tuning、Prompting、RAG 与 Tool Use 的选择（P0）

**口语锚点：**

- Prompting：改变当前任务指令和上下文；
- RAG：在推理时补充可更新、可引用的外部知识；
- Fine-tuning：改变模型参数，适合学习稳定行为、风格或领域模式；
- Tool Use：让模型获取实时信息或改变外部状态。

不要回答“知识不足就微调”。需要先判断问题来自知识、行为、接口还是验证。

## 21. LoRA、量化、蒸馏（P1）

**口语锚点：**LoRA 用低秩增量减少微调参数；量化用更低数值精度降低显存和计算成本；蒸馏让较小模型学习较强模型的输出或中间行为。

工程连接：Harness 中可用模型路由，让小模型承担分类、抽取和压缩，让强模型负责高歧义规划。

## 22. Structured Output 与 Function Calling（P0）

**口语锚点：**Structured Output 约束模型输出满足 schema；Function Calling 让模型选择工具并生成结构化参数，但真正执行函数、做权限校验和处理结果的是外部 runtime/Harness。

关键边界：模型产生合法 JSON 不代表参数语义正确，也不代表该动作被授权。

## 22.1 Prompt、消息角色与 Few-shot（P0）

**口语锚点：**Prompt 不只是用户的一句话，而是送入模型的指令、示例、上下文和输出约束的组合。system/developer/user/tool 等消息由应用按既定优先级组织；Few-shot 用少量典型示例表达期望行为和格式。

最低要求：

- 清楚 instruction、data 和 tool result 的边界；
- 示例应少而典型，不要用大量边界案例淹没主规则；
- Prompt 可以引导行为，但不能替代权限、schema、验证和沙箱；
- Prompt 变更也属于系统版本变更，需要回归评测。

## 23. 幻觉（P0）

**口语锚点：**幻觉是模型生成流畅但缺乏事实或环境依据的内容。它不是只靠一个提示词或降低温度就能消除，需要通过检索、工具、引用、验证器、拒答策略和风险分级共同控制。

追问方向：

- factual hallucination 与 action hallucination；
- 检索错、模型没使用证据、证据本身过期如何区分；
- 为什么“输出推理过程”不是可靠验证器。

---

# 第四层：信息检索与 RAG

## 24. RAG 的完整链路（P0）

**推荐口述：**

> RAG 在推理时先从外部知识源检索与问题相关的证据，再把筛选后的证据放入模型上下文生成答案。离线侧包括解析、切分、Embedding 和建索引；在线侧包括 query 理解、召回、过滤、rerank、上下文构造、生成和引用验证。

不能只回答“向量库 Top-k + LLM”。

## 25. Chunking（P0）

**口语锚点：**Chunking 把长文档切成适合索引和注入上下文的检索单元；过小会丢语义和上下文，过大会降低检索区分度并浪费 token。

需要知道：固定长度、递归切分、按标题/段落/代码结构切分、overlap、parent-child retrieval。

## 26. Sparse、Dense 与 Hybrid Retrieval（P0）

**口语锚点：**Sparse retrieval 如 BM25 擅长精确词项、专有名词和编号；dense retrieval 用 Embedding 捕捉语义相似；hybrid retrieval 合并两类候选，提高不同查询上的稳健性。

边界：Dense retrieval 不是任何情况下都优于关键词检索。

## 27. Vector Database 与 ANN（P0）

**口语锚点：**向量数据库管理向量、元数据和近邻索引；ANN 用近似搜索换取大规模查询速度和存储效率，常见索引包括 HNSW、IVF 和 PQ 类方法。

最低要求：知道 recall–latency–memory 的权衡；不需要第一轮推导 HNSW 建图算法。

## 28. Bi-Encoder 与 Cross-Encoder Reranker（P0）

**口语锚点：**Bi-encoder 分别编码 query 和文档，向量可预计算，适合大规模召回；cross-encoder 联合编码 query–document，对交互建模更精细但计算更贵，适合对少量候选 rerank。

典型漏斗：大规模召回 Top-100 → rerank Top-20 → 注入 Top-5；具体数字应由评测决定。

## 29. Retrieval 指标（P0）

最低集合：

- Recall@K：相关证据有没有被召回；
- Precision@K：召回结果中相关内容的比例；
- MRR：第一个相关结果排得多靠前；
- NDCG：考虑多级相关性与排序位置；
- answer correctness/faithfulness：生成答案是否正确、是否受证据支持。

关键意识：最终答案错误时，要区分解析、切分、召回、rerank、context packing 和 generation 哪一层失败。

## 30. RAG 与 Agent Memory 的关系（P0）

**口语锚点：**RAG 是检索增强的生成模式；Memory 是跨步骤或跨会话保存和恢复状态/经验的系统能力。Memory 可以使用 RAG 检索，但不等同于一个向量数据库。

---

# 第五层：Agent 基本控制流

## 31. Workflow 与 Agent（P0）

**口语锚点：**Workflow 的执行路径主要由代码预先定义；Agent 让模型根据中间环境反馈动态决定下一步。生产系统通常是二者混合：确定性流程负责边界和安全，模型负责高歧义决策。

## 32. ReAct（P0）

**口语锚点：**ReAct 把推理、行动和环境观察交替起来，使模型能根据真实反馈更新计划，而不是一次性生成完整答案。

```text
state → model decision → tool/action → observation → update state → ...
```

边界：ReAct 容易局部短视、路径震荡和上下文膨胀，需要预算、状态记录、终止条件和重规划。

## 33. Plan-and-Execute / Replan（P0）

**口语锚点：**先形成高层任务分解，再逐步执行；环境或假设变化时重新规划。适合长任务和依赖关系清晰的任务，常与步骤内部 ReAct 结合。

常见追问：计划如何表示？谁判断步骤完成？何时 replan？计划错误怎样恢复？

## 34. Reflection、Critic、Evaluator（P0）

**口语锚点：**Reflection 让模型检查并修正自身轨迹；Critic/Evaluator 对结果或过程给反馈。但自评可能共享同样盲点，高风险任务应优先使用独立模型、确定性测试或真实环境验证。

## 35. Agent Loop 与终止条件（P0）

Harness 至少需要管理：

- 当前 state；
- 模型请求与响应；
- tool call 调度；
- observation 回写；
- max turns、timeout、token/cost budget；
- success、failure、blocked、cancelled 等终态；
- retry、replan、escalation。

“模型输出 Final Answer”不一定代表任务真实完成，尤其在代码、文件和外部动作场景中。

## 36. 单 Agent 与 Multi-Agent（P0）

**口语锚点：**多 Agent 的价值主要来自上下文隔离、专业分工和真正可并行的探索；代价是通信、状态一致性、token、延迟和调试复杂度。默认从边界清晰的单 Agent 开始。

---

# 第六层：Harness 核心系统

## 37. State、Context、Memory、Artifact（P0）

这是 Harness 面试最重要的概念组。

- **State**：任务在运行时的真实结构化状态；
- **Context**：某一次模型调用实际可见的 token 视图；
- **Memory**：跨步骤或跨会话可持久化、可检索的信息；
- **Artifact**：文件、代码、完整日志、数据集、截图等较大工作产物。

推荐表达：

> Durable state 不应等同于当前 prompt。Context 应当是 Harness 根据 state、memory、artifact 和策略，为本次推理编译出的有限视图。

## 38. Context Engineering（P0）

**口语锚点：**Context Engineering 是选择、组织和维护每次模型推理所需信息的过程，目标是在有限 token 和注意力预算内提供最小但足够的高信号上下文。

组成：system instructions、用户需求、最近消息、计划、记忆、工具定义、工具结果、检索证据和 artifact 引用。

## 39. Compaction（P0）

**口语锚点：**Compaction 把长轨迹压缩成可恢复的执行状态，同时保留目标、约束、决策、进度、失败和未解决问题，丢弃冗余工具输出与重复讨论。

必须知道：

- summary 不是无损压缩；
- 关键需求应结构化保存并做 coverage check；
- compaction 应可观察、可版本化、可回归测试；
- 原始数据保存期限由隐私、合规和产品政策决定。

## 40. Session、Event Log、Checkpoint、Resume（P0）

**口语锚点：**Session 表示一次持久任务；event log 记录发生过的模型、工具和状态事件；checkpoint 保存可恢复状态；resume 让新 runtime 从失败点继续，而不是重新执行整个任务。

工程追问：事件是否幂等？重放会不会重复发送邮件或重复扣款？模型/Prompt 版本如何记录？

## 41. Tool、Skill、Plugin、MCP（P0）

- **Tool**：模型可选择调用的单个结构化能力；
- **Skill**：围绕一类任务组织的说明、资源和工具使用方法；
- **Plugin**：可安装和分发的能力包，可能包含工具、Skill、UI 或服务；
- **MCP**：Host/Client/Server 之间交换 tools、resources、prompts 等能力的标准协议。

关键边界：MCP 解决互操作，不自动解决规划、权限、安全和工具质量。

## 42. Tool Design 与 Tool Search（P0）

好工具至少需要：清晰名称、单一职责、无歧义 schema、错误语义、权限说明、幂等性、超时和可验证结果。

工具很多时使用：

- role-based minimal toolset；
- 命名空间和分组；
- tool retrieval/search；
- progressive disclosure；
- 常用工具常驻、长尾工具按需加载；
- 在 tool side 做过滤和聚合，只返回高信号结果或 artifact handle。

## 42.1 Prompt Cache 与语义缓存（P1）

**口语锚点：**Prompt Cache 复用相同稳定前缀的模型计算，用于降低重复 system prompt、工具 schema 和公共上下文的延迟与成本；语义缓存则尝试复用相似请求的结果，两者的正确性边界不同。

工程要点：稳定内容放前、动态内容放后；保持 schema、顺序和序列化稳定；监控 cached tokens 和命中率；包含用户私有状态或实时数据的结果不能因为“语义相似”就盲目复用。

## 43. Sandbox 与执行环境（P0）

**口语锚点：**Sandbox 隔离 Agent 执行代码、文件、浏览器和网络动作造成的风险，使资源、权限、网络和生命周期受到控制。

追问方向：

- 进程/容器/虚拟机隔离；
- CPU、内存、时间、磁盘和网络配额；
- secrets 不进入不可信执行环境；
- workspace 快照和销毁；
- stdout/stderr、exit code 和 artifact 如何回传。

## 44. Retry、Timeout、幂等与错误分类（P0）

**口语锚点：**不是所有失败都应重试。Harness 应区分临时故障、永久参数错误、权限错误、业务冲突和模型决策错误；重试需要退避、上限和幂等保护。

关键例子：查询可安全重试；发送消息、支付、删除和提交代码必须使用 idempotency key、状态检查或人工确认，避免重复副作用。

## 45. Human-in-the-Loop 与权限（P0）

**口语锚点：**HITL 不是让人批准每一步，而是在高风险、低置信度、不可逆或权限升级的决策点请求人类确认。权限控制必须在 Harness/工具层外置，不能只写在 system prompt 中。

## 46. 多 Agent 通信与并发冲突（P1）

最低要求：

- orchestrator–worker；
- 结构化 task contract；
- message/event bus；
- artifact 引用；
- cancellation、timeout 和 partial failure；
- branch/worktree/patch + coordinator merge；
- 乐观并发控制或单写者原则。

---

# 第七层：评测、可观测性、安全与生产化

## 47. Task、Trial、Trace、Grader（P0）

**口语锚点：**Task 定义输入、环境和成功标准；trial 是一次完整运行；trace 记录决策、工具、状态变化和错误恢复；grader 对最终结果或轨迹给出结构化判断。

Agent 非确定性意味着一个任务通常需要多次 trial，不能只展示一个成功 demo。

## 48. 四层评测（P0）

1. 工具单测：schema、错误、权限、幂等；
2. 组件评测：检索、路由、压缩、工具选择；
3. 任务/轨迹评测：完成率、必要步骤、禁止动作、恢复；
4. 线上指标：成功率、延迟、成本、人工接管、未知失败。

对代码 Agent，测试、编译、静态分析和环境状态通常比模型自评更可靠。

## 49. Observability（P0）

至少记录：

- request/session/task ID；
- 模型与 Prompt/Harness 版本；
- 每轮输入构成和 token；
- tool name、参数摘要、延迟、结果、错误；
- 状态转移、retry、replan、handoff；
- 最终结果、grader、人工反馈；
- 成本和端到端延迟。

目标不是“多打日志”，而是能回答失败发生在哪一层、为什么发生、修改后是否回归。

## 50. Prompt Injection 与数据外泄（P0）

**口语锚点：**外部网页、文档和工具结果是不可信数据，可能包含试图改变 Agent 行为的指令。Harness 应隔离指令与数据、限制权限和数据流、校验外部动作，并对敏感传输要求确认。

## 51. 性能与成本（P1）

最低指标：TTFT、总延迟、输入/输出 token、tool latency、cost per successful task、cache hit、并发度、失败重试成本。

优化顺序：先减少无效步骤和失败，再做缓存、并行、模型路由和推理优化；不能只降低单次模型价格而忽略任务成功率。

## 52. 版本、回归与发布（P1）

Prompt、tool schema、模型和 Harness 代码都会改变 Agent 行为，应一起版本化；上线前跑固定 eval set，采用 sandbox/canary/gradual rollout，并保留回滚与运行中 session 的兼容策略。

---

# 第八层：Harness 岗需要的计算机基础

## 53. Python 与异步基础（P0）

最低集合：

- 可变/不可变对象、浅拷贝/深拷贝；
- generator、iterator、decorator、context manager；
- exception 和资源释放；
- thread、process、coroutine 的区别；
- `async/await`、event loop、并发限制、取消和超时；
- GIL 的实际含义与 I/O-bound、CPU-bound 的选择。

## 54. 网络与接口（P0）

最低集合：HTTP 请求响应、状态码、REST/RPC、JSON Schema、streaming、SSE/WebSocket、认证与授权、超时、重试、rate limit。

MCP 或工具调用最终仍建立在这些系统知识之上。

## 55. 数据库、缓存与消息（P1）

最低集合：事务、隔离级别的直觉、索引、乐观锁、Redis 缓存、消息队列、at-least-once 与幂等消费。

对应 Harness：session state、event log、分布式 worker、恢复与重复副作用。

## 56. Linux、Git 与开发工具链（P0）

最低集合：文件权限、进程与信号、环境变量、pipe、stdout/stderr、exit code、基础 Shell；Git commit/branch/merge/rebase/worktree/patch；测试、lint、build 和 CI。

Coding Agent Harness 很可能直接操作这些对象。

## 57. 数据结构与算法（P0）

最低集合：数组、字符串、链表、栈、队列、哈希表、树、图、堆、二分、DFS/BFS、排序、动态规划基础；能分析时间和空间复杂度。

建议目标不是刷极偏难题，而是保证经典中等题可以无 AI 写出、运行、打印调试并解释边界。

---

# 第九层：第一轮可以暂缓的内容

除非岗位信息或后续面试明确指向，否则第一轮不需要投入大量时间：

- 完整手推 Transformer 反向传播；
- PPO、GRPO 的详细推导与训练系统实现；
- CUDA kernel、FlashAttention 内核级优化；
- HNSW、IVF-PQ 的完整构建算法证明；
- 某个 Agent 框架的全部 API；
- 大量冷门 planning/reflection 论文；
- Multi-Agent 社会模拟和人格设定类方法；
- 为每个术语背固定数字、固定阈值和未经验证的性能提升。

这些内容不是不重要，而是当前优先级低于“能把系统主干说对并联系项目”。

---

# 第十层：通过标准与复习方式

## 58. 第一遍通过标准

完成第一遍时，应当做到：

- 能不看资料画出八层地图；
- 对所有 P0 概念给出 30～60 秒回答；
- 能写出并解释 Attention、Softmax、余弦相似度三个核心公式；
- 能完整讲一遍 RAG 链路和 Agent loop；
- 能区分 state/context/memory/artifact；
- 能说明 Harness 如何管理工具、沙箱、恢复和评测；
- 能指出至少三个“只靠 Prompt 解决不了”的生产问题。

不要求第一遍把每个追问都回答完美。

## 59. 概念卡模板

后续逐题扩写时使用：

```markdown
## 概念

### 30 秒口述
两到四句话，先定义，再机制，再作用。

### 公式或结构
只保留真正帮助理解的公式、图或伪代码。

### 工程化
在真实系统中怎样实现、怎样观测、主要指标是什么。

### 边界与常见误区
适用条件、失败模式、替代方案、不能泛化的结论。

### 项目映射
URSA/第一章做了什么、没做什么、如果生产化会怎样改。

### 高频追问
3～5 个逐层深入的问题。
```

## 60. 建议的口头训练法

每个概念做三次输出：

1. **15 秒版**：一句定义 + 一句作用；
2. **60 秒版**：定义 + 机制 + 工程例子 + 一个边界；
3. **追问版**：连续回答三个“为什么/什么时候/具体怎么做”。

判断掌握的标准不是“看懂了”，而是合上资料仍能组织出主干，并能承受至少两层追问。

---

# 参考入口

## 与岗位最相关

1. 华为云 AgentArts《产品介绍》：公开给出 `Agent = Model + Harness`，并列出 Planning、Memory、Tool Use、ReAct、MCP、HITL、Context Window 等核心概念。  
   <https://support.huaweicloud.com/productdesc-agentarts/01%20%E4%BA%A7%E5%93%81%E4%BB%8B%E7%BB%8D-pdf.pdf>
2. 工作区现有生产资料笔记：`docs/agent_systems_production_notes_20260810.md`。

## 基础原理

3. Transformer 原论文：<https://arxiv.org/abs/1706.03762>  
4. ReAct 原论文：<https://arxiv.org/abs/2210.03629>  
5. RAG 原论文：<https://arxiv.org/abs/2005.11401>  
6. MCP Architecture：<https://modelcontextprotocol.io/specification/2025-06-18/architecture>  
7. OpenAI Embeddings FAQ：<https://help.openai.com/en/articles/6824809-embeddings-faq>

## Harness 与生产实践

8. Anthropic, *Building effective agents*：<https://www.anthropic.com/engineering/building-effective-agents>  
9. Anthropic, *Effective context engineering for AI agents*：<https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>  
10. Anthropic, *Demystifying evals for AI agents*：<https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents>  
11. OpenAI, *A practical guide to building agents*：<https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/>

## 后续材料计划

本地图完成后，按以下顺序建立可口述卡：

1. 数学与 Embedding；
2. Attention 与 Transformer；
3. LLM 训练、推理和采样；
4. RAG；
5. Agent loop、Planning、Memory；
6. Tool/MCP、Context 与 Compaction；
7. Harness runtime、sandbox、recovery；
8. Eval、observability、security；
9. 华为及其他大厂面经逐题作答；
10. URSA 第一章的工业化项目叙事。
