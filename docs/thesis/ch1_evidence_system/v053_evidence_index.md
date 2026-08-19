# 第一章 v0.5.3 证据索引

最终代码提交：`0efd090`（v0.5.3）。结果目录被 Git 忽略；以下相对路径、命令和 SHA-256 使其可定位、可复核。

| 证据 | 路径 | SHA-256 | 复现入口 |
| --- | --- | --- | --- |
| 离线 15 槽验收 | `ExpertsRS/results/ch1_d3_light/v2_acceptance_0efd090/acceptance_manifest.json` | `358B709A907F523955B361B4007FA2E6BD7C974288AEF33BCE276902227DD89D` | `run_v2_scripted_acceptance(destination)` |
| 最终 live 5×3 | `ExpertsRS/results/ch1_d3_light/v2_authorized_pilot_0efd090/v2_pilot_summary.json` | `6C4F59098937AC895496BA175316B19CE7B086EAB19189C7F43B068512548D78` | `EXPERTSRS_D3_LIGHT_ALLOW_API=YES python -m ExpertsRS.evaluation.ch1.run_v2_live_pilot <destination>` |
| 隔离 UserAgent smoke | `ExpertsRS/results/ch1_d3_light/v2_user_agent_smoke_bb7c8bf/user_agent_summary.json` | `E60073E3B39F8B06D7B5BF595AEA1D87E398B1B38DF505B90653A2240B19A31C` | `python -m ExpertsRS.evaluation.ch1.run_v2_user_agent_smoke <destination>` |
| CLI NDVI | `ExpertsRS/results/ch1_d3_light/v2_closeout_0efd090_cli/ndvi_cli/result.json` | `1F3CBFF84A429E04549DDCC7975B46B707F4308015679CEC3DD25AF7FDA9360D` | `python -m ExpertsRS run ...` |

最终 pilot 的 v2 evaluator 为通过判据；v1 evaluator 仅并列保留作历史记录。前两轮 14/15、13/15 的目录也保留，失败原因是 provider 将相同 JSON 决策重复拼接；它们不支持任何成功 claim。

统一 closeout manifest 位于 `v2_acceptance_0efd090/closeout_manifest.json`：主环境及 clean-venv 均为 121/121，`compileall`、`git diff --check`、CLI NDVI、scripted 15-slot 和隐私扫描均通过。

允许 claim：结构化计划约束执行；task-11 可在 observation 后由 Scientist 局部重新授权并交付专题图和受限比例；澄清可由隔离 profile 回答后经 `.resume()` 结束。禁止 claim：规划优越性、行政区绿地覆盖率、稳定效果、用户研究结论、20×1 结果或 durable recovery。
