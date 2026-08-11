# 第一章 D2 无 API 最小闭环证据

> 运行时间：2026-08-11 13:26 CST
> 证据角色：`mechanism_fixture` / `engineering_regression`
> 非证据：遥感主题精度、真实 LLM 规划增益、一般恢复能力、多智能体优越性

## 人类可读结论

从 `ExpertsRS/` 执行 `python run_d2_closeout.py` 后，43 项 workflow、ReAct、科学前置条件、
benchmark 与新增运行接口测试通过。无 API 小样完成以下一条可追溯路径：

1. 读取真实 Sentinel-2 栅格元数据并登记为有效产出；
2. 在有效边界建立逻辑检查点；
3. 明确注入不存在的波段名 `B99`，真实 NDVI 工具按科学前置条件失败；
4. 保留计划 v1 与失败反馈，创建计划 v2，并引用原检查点和失败原因；
5. 复用元数据产出，以 metadata 已验证的 `B8/B4` 重试成功；
6. 从同一组 17 条运行事实确定性整理出 17 个节点、37 条时序/语义边；
7. 对结果目录之外的写入请求作出 `deny` 决定，且没有执行该动作。

这证明第一章的“可调整规划—真实反馈—过程图—检查点局部恢复”最小接口已经实现并贯通。`B99`
只是故障注入，成功的 `B8/B4` 也只证明既有工具前置条件可执行；本小样不包含阈值分类，不能
评价绿地精度，也没有调用 LLM。

## 本次运行摘要

| 项目 | 结果 |
| --- | --- |
| run ID | `ch1_d2_adaptive_20260811132606` |
| 故障是否被观察 | `true` |
| 新计划 | `greenspace-plan:v2` |
| 复用产出 | `artifact-metadata` |
| 重试是否成功 | `true` |
| 越界动作 | `deny: resource_outside_allowed_write_roots` |
| 事件 / 图节点 / 图边 | `17 / 17 / 37` |

## 可重建入口与完整性

生成物位于 `ExpertsRS/results/ch1_d2_closeout/`，该目录被 Git 忽略，必须通过下列入口重建，
不能只依赖本地时间戳文件：

- 总入口：`ExpertsRS/run_d2_closeout.py`
- 故障小样：`ExpertsRS/workflow/run_adaptive_pilot.py`
- 运行接口：`ExpertsRS/workflow/runtime.py`、`trace.py`
- 接口测试：`ExpertsRS/test_adaptive_runtime.py`

本次 SHA-256：

| 对象 | SHA-256 |
| --- | --- |
| 输入 Sentinel-2 栅格 | `557E28C8E947C609DD57E20E7854DF0F775648223F8BC2197BC8297A4C739F9F` |
| `adaptive_recovery_trace.json` | `9C85DE0CC4B164D40C976B07CE192EEA763D8142EA793BD43437093DA7C80660` |
| `adaptive_process_graph.json` | `A45731A0473D8141E8D42C6211B243410C01839AE183771E9C95475AEF3D9080` |
| `adaptive_pilot_summary.json` | `5E9B30C2CF874D226C7D41A8CD54F8AB3A001527931245402EAA4414ABD7C562` |
| NDVI 输出 | `929A14170157ECE81F5F3E256BC9DA7BE9E338285DFFA5CC8CBEC970600F92C1` |

源码入口由本次第一章 Git baseline 固定；结果目录仍被 Git 忽略，必须通过入口重新生成。
正式 D3-light 实验前仍须另行完成真实模型对照和环境复核。
