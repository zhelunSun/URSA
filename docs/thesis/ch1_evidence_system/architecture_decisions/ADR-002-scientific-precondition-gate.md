# ADR-002：遥感工具的科学前置条件采用 fail-closed 语义

> Status: accepted for M1 on 2026-08-07. 适用于当前工具、operator
> contract、validator fixture 与 scripted pilot；不是对所有传感器的完整本体设计。

## Context

独立审计发现，样例 Sentinel-2 栈的描述顺序为
`B2,B3,B4,B5,B6,B7,B8,B8A,B11,B12`，旧默认参数 `8/4` 被
rasterio 解释为栈内第 8/4 个波段，即 `B8A/B5`。同一 pilot 又把
NaN/nodata 写入 class 0，使类别计数与有效像元数不一致。进一步复核还发现：

- EVI/MSAVI 的常数项要求反射率量纲，不能直接对缩放整数套公式；
- 没有投影线性单位时，不能默认每像元为 10 m；
- pixel algebra 不能默许 shape/CRS/transform 不一致；
- Sentinel-2 光学栈没有当前 LST 算法所需的 Landsat-8 thermal B10
  与 TOA radiance 语义。

这些问题不是一般异常处理，而是“一个计划是否有资格执行”的科学前置条件。

## Decision

1. 光谱工具默认使用 `B8`、`B4` 等语义名称，并只按 raster band
   description 精确解析；缺描述、缺波段或重复描述时停止，不按文件名或常见顺序猜测。
2. 数字参数只表示专家显式给出的 rasterio 1-based 栈内位置，并在结果中标记
   `explicit_stack_index`；它不再被描述为物理波段号。
3. 当前本地 Sentinel-2 栈未声明 nodata，因此对参与计算的全部源波段同时为 0 的像元，
   按该数据产品的 no-signal footprint 处理为无效像元。这个判据属于本 fixture 的数据合同，
   未来通用 ingest 应优先使用产品 mask/nodata/quality layer。
4. threshold 输出以 255 保存 nodata；`class_0 + class_1 == valid_pixels`，且
   `valid_pixels + nodata_pixels == total_pixels`。面积和 zonal statistics 只消费有效像元。
5. 无显式 `pixel_area_km2` 时，面积只能从具有可转换线性单位的 projected CRS 推导；
   geographic CRS 停止。mask/zonal 的输入必须具有相同 shape、CRS 与 transform。
6. EVI/MSAVI 默认把 Sentinel-2 缩放整数除以声明的 `reflectance_scale=10000` 后再计算，
   并记录该尺度。调用方若使用其他产品，必须覆盖这一数据合同。
7. 当前 `calculate_lst` 只接受声明的 Landsat-8 B10
   `toa_radiance_w_m2_sr_um` 与显式 emissivity；Sentinel-2 LST 请求在执行前因缺 B10
   受控停止，不从光学 band 或栈内“第 10 层”伪造温度。
8. 上述规则同时进入直接工具实现、`OperatorSpec.required_bands/required_config`、validator、
   Agent prompt 与 deterministic tests，避免只修一条调用路径。

## Rationale

自动猜测可能提高单次 demo 成功率，却会把数据语义错误包装成结果。第一章研究的是可检查的
planning-control protocol，因此宁可产生结构化 stop，也不能在科学前置条件未知时继续执行。
把同一规则放入 tool、contract、validator 和 trace，使“为何执行/为何停止”能够在论文和实验中
被复核，并为第二章更丰富的 ScientificContract 留下清晰接口。

## Evidence

- `test_scientific_preconditions.py`：10 项真实 raster fixture 测试；
- `test_workflow.py`：adapter signature、required bands/config 和 output contract 测试；
- `react_pilot_20260807201058.json`：B8/B4 分别解析到栈内 7/3；
- 同一 trace：`248703 + 171136 = 419839` 个有效像元，另有 353281 nodata；
- `controlled_stop_trace.json`：Sentinel-2 LST 在执行前以 `missing_required_band: B10` 停止；
- `python run_m1_closeout.py`：33 tests、13 tool checks、repair/stop 与 real-tool pilot 全部通过。

生成结果位于 ignored `ExpertsRS/results/`；本 ADR 记录的原始运行发生在源码提交前，现已由
Chapter 1 baseline commits 固定入口。它仍是本地 `engineering_support + diagnostic_evidence`，
不是正式效果实验或公开 release。

## Consequences and claim boundary

- 修复后的 pilot 可证明“带显式 band/nodata provenance 的真实工具链可以闭合”，不再只是
  错误语义下的 plumbing smoke；
- 阈值 0.3 未经本任务独立校准，且没有地面真值，因此不能称 greenspace thematic accuracy、
  科学案例验证或方法效果证据；
- 当前 precondition vocabulary 仍未覆盖云/阴影 QA、atmospheric correction、重采样策略、
  extent/temporal compatibility 和多传感器本体；这些属于后续有任务证据时再增加的范围。
