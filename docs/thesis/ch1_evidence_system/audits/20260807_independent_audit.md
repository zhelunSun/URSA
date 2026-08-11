# 2026-08-07 第一章独立审计

> Mode: dedicated read-only subagent, counter-evidence first. 主代理另行复核关键发现、运行当前 closeout，并在隔离导出中运行远端 runtime 分支测试。

> Remediation status, 2026-08-07 20:10 CST: F-01、F-02、F-03 与 F-05 的
> 当前 P0 实现缺陷已经修复并进入 regression tests；Sentinel-2 LST 另增加了执行前
> controlled stop。下文保留的是发现当时的原始审计结论，避免用事后修改抹去证据轨迹。
> F-04（两条 live path 未贯通）、完整 fault coverage、environment/release provenance 与
> 正式 P0--P3 仍开放。

## 审计时总结判定

当前仓库形成了有价值的最小方法机制，但不存在一个完整的
`LLM -> typed graph -> validate/repair -> real execution -> unified trace`
集成闭环。现有 scripted pilot 还有 P0 级科学语义问题，因此第一章必须区分：

- software method kernel：已实现最小版本；
- engineering integration smoke：已运行；
- scientifically valid RS pilot：暂时 blocked；
- opening-ready P0--P3 evidence：未完成；
- formal thesis effect evidence：未完成。

## 原始 notebook 判定

`ExpertsRS/ExpertsRS_notebook.ipynb` 仍在。最早版本可从 `19db55b` 恢复；May 2025 case 在 `878e84b` 形成稳定文件名。`ba1248c` 在 2026-04 将其改为 18-tool/tool-first 兼容入口，之后到当前 HEAD 未再变化。

因此可写“本次 sidecar 升级没有改当前 notebook”，不可写“notebook 自论文原型以来从未改变”。原始路由由 last speaker、`Approve/End` 和 error keywords 驱动，没有显式 state/graph/validator/trace。

## P0 findings

### F-01：物理波段编号与栈内位置混淆

样例 raster 的 descriptions 为：

```text
B2, B3, B4, B5, B6, B7, B8, B8A, B11, B12
```

但 [run_react_pilot.py](../../../../ExpertsRS/run_react_pilot.py) 调用 `nir_band=8, red_band=4`，而 rasterio 将其解释为第 8/4 个栈内 band，即 `B8A/B5`。`index_kit.py` 又把这组位置标成 Sentinel-2 B8/B4 NDVI。当前产品不能作为科学正确的 NDVI/greenspace 证据。

### F-02：nodata 被写成背景类且统计不变量破坏

`apply_threshold` 对 NaN 比较后直接转 `uint8`，实际写为 0，虽然 profile 宣称 nodata=255。trace 中 `total_pixels=419839`，但 class0+class1=`651592+121528=773120`。当前 mask 只能证明文件生成，不能证明有效像元分类或面积语义。

### F-03：18 个 adapter 名称覆盖不等于可执行 contract

至少存在三处参数名/必需参数不一致：

- `save_raster`：adapter `array`，真实函数 `data`，且 adapter 未表达 `output_path`；
- `apply_mask`：adapter `data_file`，真实函数 `input_file`；
- `zonal_statistics`：adapter `data_file/zones_file`，真实函数 `value_file/zone_file`。

当前 drift check 只比工具名集合，因此 “18/18 contracted” 不能推出 “18/18 executable”。

## Architecture findings

### F-04：typed workflow 与 ReAct 是平行路径

- `react_demo.py` 不构造或验证 WorkflowGraph；
- `workflow/run_closeout.py` 不执行 graph operator；
- `run_react_pilot.py` 执行真实工具，但不消费 graph；
- 两者只复用通用 event container。

当前允许表述为“分别实现并测试 typed planning kernel 与 ReAct observation routing”，不允许画成已经贯通的 live pipeline。

### F-05：ReAct trace 不可精确 replay

scripted `_decision` 把 arguments 固定记录为 `{}`，与真实 NDVI/threshold 参数不符；observation 是截断后的 Python dict string。trace 可检查顺序，不能恢复真实 invocation 或验证 checksum。

### F-06：Workflow contract 仍可绕过

- caller 可向 `add_step` 传入与 operator contract 不同的 output type；
- `produced_types` 包含输入 artifact，可能把输入误当任务输出；
- intermediate artifact `uri=None` 可跳过 `file_exists`；
- constraints、validation needs、unresolved questions 尚未参与 validator；
- 无 config、CRS、resolution、extent、band、nodata 或 parameter range checks。

## Engineering findings

- 当前 7 workflow + 7 ReAct tests 通过，但 fault-family coverage 不完整；
- `test_tools.py` 是脚本检查，registry coverage 和 functional correctness 没有严格分离；
- requirements 只有宽松下限，无 lock/environment manifest；
- raw results 被 Git ignore，tracked evidence 没有 checksum、package versions 或 dirty patch hash；
- 当前 workflow/ReAct 源码大多未跟踪，`fe9c0f5` 不能重建生成结果；
- README 的 v0.3/v0.4 尚无 commit/tag；
- 远端 runtime 分支隔离复跑 28 项检查通过，但它未合并、node 是 deterministic callables、LangGraph 只是 adapter stub，不能计作当前 live runtime。

## Scientific novelty audit

Typed graph、ReAct 和 trace 本身不宜作为 novelty。Spatial-Agent 已提供 GeoFlow DAG、functional constraints 与 IO-port composition；Constraint-aware AoV 已验证 CRS/geometry/extent edges；Earth-Agent/OpenEarthAgent 已有大规模 tool trajectory 和结果评测。

仍有潜力的候选是：EO-specific operator/artifact semantics + structured violation taxonomy + conservative local repair/appropriate stop + matched fault ablation。但当前粗粒度 raster/index/mask type 尚不足以充分代表 EO-specific contract language。

## Priority

### P0：对外展示或提交前

1. metadata-aware band resolver 与真实 sensor fixture；
2. nodata=255 的实际写入和 count invariant；
3. adapter signature/output contract validation；
4. trace 真实 arguments、structured results、checksum；
5. 文档明确两条路径未集成；
6. 将源码与 evidence source 纳入可重建 Git baseline。

### P1：可信工程包

增加 output spoofing、unknown/missing/order/precondition、真实 ambiguity、多 expected outputs 等反例；锁定环境；引入 trace schema/version/manifest；接受或修改 ADR-001。

### P2：开题/论文证据

贯通 live LLM plan path，多 task family 与 fault fixtures，完成 P0--P3 matched study，并进行正式 comparator literature review。

## 审计后证据变更

本次审计没有把“发现缺陷”视为项目失败，而是触发了显式 evidence downgrade：`C1-SCI-01` 从可能的案例证据改为 blocked integration smoke。只有修复、复测和新 manifest 能重新晋级，不能用文字解释绕过。

## 主代理复核与处置记录

| Finding | 处置 | 新证据 | 剩余边界 |
| --- | --- | --- | --- |
| F-01 band ID/position | semantic name 精确匹配 band descriptions；数字仅为显式 stack override | B8/B4 -> positions 7/3；semantic resolver tests | 缺 descriptions 时停止；未建立全传感器 ontology |
| F-02 nodata invariant | mask nodata=255；class/valid/total 分开统计；area/zonal 排除 nodata | `248703+171136=419839`，另 353281 nodata | threshold 0.3 无独立校准，不是 thematic gold |
| F-03 adapter drift | 修正三个参数合同并用 `inspect.signature` 自动对照全部 catalog callable | workflow signature test | 类型仍较粗，未覆盖所有 EO compatibility |
| F-05 trace arguments | scripted call 写入真实 JSON arguments，observation 保留结构对象 | reconstructable-arguments test 与新 pilot | 尚无 checksum/schema version/replay runner |
| 新发现：Sentinel-2 LST | LST 收窄为 Landsat-8 B10 TOA radiance；validator 检查 required band/config | `missing_required_band: B10` controlled-stop trace | 尚未验证独立 Landsat-8 LST product accuracy |

处置依据见 `ADR-002-scientific-precondition-gate.md`。证据只从 blocked
升级为单 fixture 的 `diagnostic-supported`；formal effect 和 thematic accuracy 没有升级。
