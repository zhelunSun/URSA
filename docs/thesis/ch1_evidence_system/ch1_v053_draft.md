# 第一章写作草案（v0.5.3）

本章实现以 `ExpertsRSSystem.run()` / `.resume()` 为唯一入口的可审计遥感任务运行时。Manager 负责澄清与报告，Scientist 提交完整、无路径的 TaskSpec 与 WorkflowGraph，Engineer 只能选择当前 eligible 的计划节点；runtime 绑定安全参数、验证图和 artifact 合同，并将 planned graph 与 observed graph 分别持久化。

对用户交付，运行时不再信任模型自行列出的 `requested_outputs`。它从原始请求派生 DeliveryObligation；task-11 必须同时提供植被覆盖专题图与绿色比例。后者只被表述为有效影像像元范围内的比例，缺少独立 AOI/行政区分母时不得称为东城区覆盖率。

最终 5×3 live pilot 的 v2 evaluator 15/15 closure，说明冻结条件下的运行、停止、澄清和局部恢复证据闭合。它不识别规划优越性或 checkpoint 的独立效应；task-11 的修订分类为局部重新授权。隔离的 ProfiledUserAgent 只证明一次澄清回答可经 `.resume()` 闭环，不构成用户研究。
