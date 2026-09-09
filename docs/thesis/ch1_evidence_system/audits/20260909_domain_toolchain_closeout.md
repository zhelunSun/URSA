# 北京产品描述链：阶段验收记录

日期：2026-09-09。状态：S1 离线领域工程贯通通过；科学有效性、真实模型能力和作者接受未评估。

## 本轮改变了什么

在正式仓库 `D:/Projects/phd-thesis/URSA` 的 `codex/ch3-domain-toolchain` 上，复用现有
`ExpertsRSSystem.run`、CLI、计划验证、工具执行、产物登记、过程图与报告，加入显式
`classification-v1` 离线配置。默认 18 工具保持；新增组成统计与同源地图两个领域工具。
这完成第三章领域系统的第一条工程产品链，没有替代第一章方法实验或完成第三章全部系统研究。

代码检查点 `95990bb7a8a51bb11a73b3910e6e2ed954734251`；图件留白修正及后续阶段计划为
`6800a376f9b44bb4186dd8688547e4e0d52953e8`。两者均在完整北京运行前提交并推送。
软件为 `0.5.4.dev0`；冻结研究基线仍为 v0.5.3，原活动分支起点 `cedeb960f424f3d7547377818f803349700e00ac`。
保护标签仍解析到 prototype `19db55bf2a819e8b07722233330d1b541bd3f764`、v053 closeout
`9e18532bf69f8c8c114f1bae9c10bbf5ff4dbe6c`，未移动或改写。

检查发现并补齐：调用方资源 ID/AOI 绑定；非公开 helper 拒绝；实际产物必须存在、非空、
属于本 action 输出目录并记录 hash；输入和中间产物身份漂移拒绝；报告值和引用须对应事实产物。
范围、设计和后续阶段见 [阶段目标](../domain_toolchain_stage.md)。

## 验证证据

- 原 `.venv` 保留，原有 121 项回归通过；没有向冻结环境补装 domain 依赖。
- `.venv-domain` 从原环境冻结依赖构建，补入 Shapely 2.1.1、PyShp 2.3.1；完整清单在本轮运行父目录 `environment.pip.txt`。
- 留白修正前的整套功能代码：`python -m pytest ExpertsRS -q`，136 passed，44.07 秒；25 条 rasterio PendingDeprecationWarning。
- 仅柱条留白修正后：两个 domain 测试文件合计 15 passed，2.35 秒；13 条相同类别 warning。
- M1 no-API closeout：PASS（39 unittest、18 工具核验、修复/受控停止及真实工具 scripted pilot）。
- D2 no-API closeout：PASS（49 unittest、真实工具恢复/权限 fixture）。这些是当前工程检查，不补回 v053 历史运行包。
- `git diff --check`、编译检查、`git lfs fsck` 通过；未把本地 LFS 检查描述成干净云端恢复已验证。
- 低阶子智能体完成有界工具实现与只读检查；根智能体检查集成、运行真实产品并查看图件。没有将代码审查当作独立科学验证。

开发中的小栅格测试曾在并行编辑尚未完成时遇到绘图表路径缺失；补齐后定向检查和整套回归通过。
这属于工程接线问题，不是研究任务结果。第一次北京完整运行另外发现下述图件问题，原包保留。

## 输入身份与评价隔离

第三章工作副本为 `D:/Projects/phd-thesis/urbfo-agent-demo`；沿用其既有北京 2025 分类图和
`data/aoi/bejing_urban_forest_bound/BJuforebv4.shp`，未训练、重新分类或改写第三章数据/参考。

- 分类图 SHA256：`fe89f6069f6cbd8d443c2ad249babd66b76f94653af63c1c6e6ae85f0deee369`。
- 23,216 × 18,004，单波段 uint8，EPSG:4326，类别 0–7，nodata=255。
- `.shp/.shx/.dbf/.prj` 与参考一致；运行还登记存在的 `.cpg`。逐文件身份保存于运行 manifest。
- 外部参考：`experiments/results/beijing-product-description-v0.1/reference.json`，SHA256
  `48ed17afda7de04a456b99470ceb437ce812a4f83f40e62204c2e57409221881`。
- `scripts/check_classification_run.py` 只在运行之后读取参考；runtime、工具和决策接口均不读取参考答案。
- 被测计算适配自同一参考算法，所以数值吻合只证明同产品计算一致，不能充当独立专题真值或系统效果。

## 第一次完整运行与修复

`ExpertsRS/results/domain_beijing_20260909/beijing-domain-01`，代码 `95990bb`，216.178 秒，
2 次工具执行、6 次 scripted 决策、0 API 调用、0 recorded tokens，运行状态 completed。
11 项外部核验全部通过；图件确定性审计 0 errors / 0 warnings。

根智能体查看 3600 × 2400 PNG 后发现：最大类别的柱条标签 `36,912,182` 被图像右边界裁切。
因此该图件未获视觉验收。保留 result、图件、manifest、comparison、figure_audit 和 visual_review；
修复将计数坐标轴设为零至最大值的 1.30 倍，并在绘图前合同中声明。新运行编号为 `beijing-domain-02`，
不覆盖第一次结果，也不调整任何类别数值。

## 最终验收

`ExpertsRS/results/domain_beijing_20260909/beijing-domain-02`，代码 `6800a37`，218.396 秒，
2 次工具执行、6 次 scripted 决策、0 API 调用、0 recorded tokens，运行状态 completed。
11 项外部核验全部通过；figure audit 0 errors / 0 warnings；根智能体再次查看实际 PNG，
八个数字完整可读、最大值标签已消除裁切，标题/坐标/图例/范围说明可读，柱条零基线保留。
密集分类图仍只适合作为空间预览，不用于逐像元判读；专题质量与作者图件接受另行评估。

| 验收字段 | 结果 |
| --- | --- |
| AOI 像元中心总数 | 109,055,410 |
| 有效分类像元 / nodata | 108,566,019 / 489,391 |
| 八类计数及比例 | 与冻结参考逐项一致；比例容差 1e-12 |
| result.json SHA256 | `7edb6165c590fad56a10fb0a7dbdcff5c56124c0bab4dfb8a9c70b84ccdb7cd2` |
| 最终 PNG SHA256 | `f58f64d4f9c2593f0a0bffebeab2236b58abc70ad2d6d24cd112075d40932649` |

运行父目录的 `beijing-domain-20260909-r1.zip` 为 2,608,151 bytes，包含两次运行及实际环境清单，
额外 `package_manifest.json` 列出 37 个归档文件的相对路径、大小、SHA256。已执行 ZIP CRC 检查，
并逐个从 ZIP 读出这 37 个文件核对 SHA256；输入栅格/AOI 和环境二进制不在该包内。
ZIP SHA256：`dd407b0f13a12c5bec98b879661a676fd2c4f05d9b6f7768e7e1dd03b7886221`。
这是本地归档，不是异地/云端备份。原始结果、PNG 和 ZIP 按仓库规则留在 Git 外；本文提交小型可复核回执。

## 复现入口

从 URSA 根目录运行，使用集成环境。下面示例必须选择一个尚不存在的 run ID；保留原运行目录。
`environment.pip.txt` 是实际环境快照，输入文件本身仍归第三章数据资产管理，不包含在运行包内。

```powershell
$domainRaster = '../urbfo-agent-demo/data/processed/rf_maps/routeb_h07_cs8k_strict500_seasonal17_v2_20260708/beijing_rf_routeb_h07_cs8k_strict500_seasonal17_v2_full_2025_20260708.tif'
$domainAoi = '../urbfo-agent-demo/data/aoi/bejing_urban_forest_bound/BJuforebv4.shp'
.venv-domain/Scripts/python.exe -m ExpertsRS run --profile classification-v1 --request '使用指定的北京2025年八类分类产品与研究区边界，统计原网格有效像元的类别组成，生成同源地图和可追溯报告。' --data $domainRaster --aoi $domainAoi --product-year 2025 --raster-sha256 fe89f6069f6cbd8d443c2ad249babd66b76f94653af63c1c6e6ae85f0deee369 --output-dir ExpertsRS/results/domain_beijing_20260909 --run-id beijing-domain-new --max-wall-time-seconds 900
.venv-domain/Scripts/python.exe scripts/check_classification_run.py --run-dir ExpertsRS/results/domain_beijing_20260909/beijing-domain-new --reference ../urbfo-agent-demo/experiments/results/beijing-product-description-v0.1/reference.json --output ExpertsRS/results/domain_beijing_20260909/beijing-domain-new/comparison.json
```

完整运行当前会扫描原网格两次（组成、地图的同源复核）；不应将当前耗时直接当作优化后的系统性能。
图件审计使用 scientific-figures 的 `figure_audit.py`，传入该 run 下实际 `*.figure_contract.json`
和 `*.render_manifest.json`，再查看 PNG。schema 审计不能替代视觉检查，本轮第一次裁切正说明了这一点。

## 下一步价值

S1 只证明领域接线和可追溯交付。S2 应从第二章真实求解入口的适配合同开始，让知识依据实际影响
一个方法选择或结果解释，再接一个已有专题工具消费中间产品。森林对象/格局定义沿现有研究口径核定。
S3 真实模型小样需独立固定模型、输入、预算与交付；S4 再设计同条件系统比较和专题质量验证。
本地同步工具的不可抢占执行、进程崩溃恢复、完整领域恢复仍未解决，按真实任务需要安排。
历史 laptop 5×3 包仍待取回，不阻塞这条新开发链，也不能用本轮结果替代它。
