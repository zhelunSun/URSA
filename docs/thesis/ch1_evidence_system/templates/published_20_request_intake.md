# Published 20-Request Benchmark Intake

> Status: awaiting original source assets. 不根据论文摘要反向编造逐条任务。

## Provenance

- source file/location:
- paper version/DOI:
- original experiment date:
- model/config/prompt versions:
- evaluator(s):
- public/internal-use boundary:

## Request ledger

| Legacy ID | Exact request | Single/multi | Expected data | Expected method/tool sequence | Expected result | ExpertsRS score/result | Base LLM | Single agent | Tokens | Source locator | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- |
| `LEGACY-01` | | | | | | | | | | | |

复制到 20 行后逐项填充；不能只保留总百分比。

## Mapping decision

每条任务只允许一种主要去向：

- `provenance-only`：只支持历史结果；
- `supplementary-reproduction`：在冻结旧配置下复现；
- `task-family-seed`：只借用任务族，重新写独立 task/gold；
- `excluded`：数据泄漏、定义不清、无法恢复或不符合当前城市森林范围。

## Leakage control

- 新方法开发者是否看过该任务的 gold/历史结果：
- 是否进入 formal P0--P3 test：
- 若进入，如何重新隔离 task/gold：
- 是否存在 prompt/task wording contamination：

## Claim boundary

该表完成前，只可引用论文已公开的 aggregate result，不声称已恢复可执行 benchmark。
