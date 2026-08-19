# v0.5.3 正式结果表

最终 live pilot：`0efd090`，冻结 panel、DeepSeek-V4-Flash、温度 0、无 provider 重试，15/15 v2 closure。

| 任务类别 | 槽数 | 终态 | v2 closure |
| --- | ---: | --- | ---: |
| NDVI（task-02） | 3 | completed | 3/3 |
| 缺失 NDSI（task-03） | 3 | controlled_stop | 3/3 |
| LST 前置条件（task-10） | 3 | controlled_stop | 3/3 |
| task-11 故障/恢复 | 3 | B1 stop；B2/B3 completed | 3/3 |
| task-13 澄清 | 3 | needs_clarification | 3/3 |

总 token：215,500；总 wall time：391.582 s。task-11 B2/B3 的绿色比例均限于“有效影像像元范围内”，且专题图由 `plot_thematic_map(mask_raster)` 证据支持。其 graph diff 均为 `local_reauthorization_only`，不表示生成更优规划路径。
