# 2026-09-10 实验准备回执

范围：知识模块暂不接入；完成版本化接线、开发实验设计、公共任务投影和现有能力的定向检查。
设计主入口：[知识预留与验证设计](../validation_design_20260910.md)。
基础 HEAD：`02953a30975f580fa5fed7f6aa40ee068a010a50`；准备时新增文件未提交，因此回执同时保存源码 SHA，
不能仅凭该 HEAD 复现新增脚本。最终源码随本回执提交；未改 v0.5.3 冻结分支、旧 raw 或第二章代码。

## 实际完成

- 版本化 KnowledgeRequest / KnowledgeResponse / Protocol / UnavailableKnowledgePort；当前只由准备脚本调用，未接入模型决策。
- 三项公共开发任务：产品描述、缺 AOI、缺少生态解释依据；同条件 U/G 和 K0=unavailable 的实验草案。
- `preparation-03` 最终回执 passed；0 API、0 新 agent 任务执行。模型六例预算只是后续设计，本轮未使用。
- 核验分类 raster、AOI 的 shp/shx/dbf/prj/cpg 和 2 个登记主要产物。receipt 有 9 项 hash 映射，其中 study_area 与 study_area.shp 指同一文件，故为 8 个唯一文件。
- 此次没有重新计算整幅北京产品、重新读取独立 reference、渲染/人工复看地图，也未审计地图 SVG 等所有次要输出。
  同产品计数比较与图件检查仍引用 [09-09 既有验收](20260909_domain_toolchain_closeout.md)，不能称本轮新增专题精度验证。
- 公共包不含旧 state 路径、产物值、plan、trace 和 evaluator_only；组件限定为白名单后缀及 SHA256。
  这是显式字段投影，public/private 目录不是进程沙箱。工具描述/schema/执行解析入口和 G 循环尚未完成。

## 检查和修订

35 项不同的相关检查通过：7 项新 preparation 合同测试、9 项既有 domain runtime、13 项 v2 closeout、6 项 product tools。
原有两个组共 13 个 Rasterio PendingDeprecationWarning；没有修改其底层计算。本轮未重复全库 141 项测试，因主 runtime 未修改。
覆盖空服务不造答案、来源/适用性字段缺失拒绝、请求 ID 与内部调用预算、public 元数据投影、AOI 漂移、外来产物、
新输出不覆盖、首错保留、跨启动目录相对路径；既有测试覆盖真实小栅格、产品出处、输入/产物篡改、故障修订与报告边界。

低阶 fresh-context 子智能体只读检查了5个新文件，没有调用 API 或改文件。发现的三项当前问题已修复：
完整性校验从 assert 改为显式 ValueError；相对路径按 existing run 目录解析；components 不再任意复制。
其余进入条件（共享工具、隔离、独立评分/参考、真实知识依据核验）保留为待实现，不包装成准备已解决。

`preparation-01` 是初版；`preparation-02` 验证显式异常版的优化模式正常入口；`preparation-03` 是路径/投影修订后的最终版。
三个目录全部保留；它们都是准备回执，不是三次独立实验。三份 public packet 的 SHA 跨修订相同。
单元测试故意制造的错误只在临时目录测试，不冒充真实 live 首错。

## 可定位证据

本地目录：`ExpertsRS/results/ch3_preparation_20260910/`；逐文件 hash 清单为 `hashes.json`。
生成文件按现有规则不进 Git，仅此审阅索引与源码入 Git；不宣称完成异机原始包备份。
最终 receipt SHA-256：`b0c821b5f8cd51fe00087358924b3d3e91414c5288b23cb482f96931261a139e`。
既有北京 state SHA-256：`b1d60afaec602c06fd00db8dd376562754eef1132bcd9fc311771e12e3d418ed`。

| 公共任务文件 | SHA-256 |
| --- | --- |
| DEV-COMPOSITION.json | `5e84cf8ae68fcb1a97a3f4efa9fb3511a2628e524631e43ef4ee4a4722cd57d1` |
| DEV-MISSING-AOI.json | `aff3e73ad9780eb987b507d55e5cedd7e68e3a9c75bda508408cc0da07eeb7c0` |
| DEV-UNSUPPORTED-ECOLOGY.json | `88744d5437af0d05c43e0d24e5d6ae5be5f207f912ff3cf949b8e178534159f3` |

下一步无需等待知识模块：先把同一工具和公共资源交给两个实际执行入口，再准入 K0 的6例开发小样。
知识就绪后再接 K1；正式测试集、人工参考和效果判断仍需另行冻结。
