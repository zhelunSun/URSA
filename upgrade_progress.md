# URSA 升级进度

> 项目：基于 LLM 的用户中心遥感分析系统
> 仓库：`https://github.com/zhelunSun/URSA`
> 本地路径：`c:\Users\zhelunStation\WorkBuddy\Claw\URSA`

---

## Phase 0 — 漏洞修复 ✅ 已完成

| # | 内容 | 改动 |
|---|------|------|
| 0.1 | API key 安全化 | 新增 `.env.example`、`.gitignore`、`llm_config_list.py`；旧 JSON → `.json.template` |
| 0.2 | 移除硬编码数据路径 | Engineer prompt 改为动态发现数据文件 |
| 0.3 | results/ 目录创建 | Notebook 启动时 `os.makedirs(exist_ok=True)` |
| 0.4 | 依赖清单 | 新增 `requirements.txt` |

---

## Phase 1 — 工具模块 ✅ 已完成（2026.04.14）

把 Engineer 从"自由写代码"改为"调用标准化遥感工具"

### 已实现的工具包

```
tools/
├── __init__.py       # 统一导出 get_all_tools, get_tool_schemas
├── io_kit.py         # ✅ 栅格读写、元数据查询、波段提取
├── index_kit.py      # ✅ NDVI, EVI, NDWI, LST, NBR, MSAVI
├── analysis_kit.py   # ✅ 阈值分割、面积统计、掩膜、区域统计
├── viz_kit.py        # ✅ 专题图、热力图、假彩色合成
└── registry.py       # ✅ AutoGen function_map + tool schemas 注册
```

**共 18 个工具函数**，全部通过 `function_map` 注册给 Engineer agent。

### Notebook 改动
- 新增 cell：工具加载（`from tools import ...`）
- Engineer agent：`function_map=function_map` + `tools=tool_schemas`
- StateFlow 注释更新

### Engineer Prompt 改动
- 从"自由写 Python 代码" → "优先调用工具，写胶水代码"
- 新增工具列表文档（每个工具的用途、参数）
- 错误处理：检查 `success` 字段
- 波段约定：1-based（Band 4 = index 4，不是 3）

---

## Phase 2 — 数据模块（GEE）📋 规划中

新增 `data/gee_client.py`：根据用户时间/地点自动从 GEE 获取数据。

---

## Phase 3 — 流程增强 📋 规划中

- 错误自动重试加强
- 多任务模板库
- 用户历史记忆

---

## 当前文件结构

```
URSA/
├── .gitignore                    ✨ Phase 0
├── requirements.txt              ✨ Phase 0
├── ExpertsRS/
│   ├── .env.example              ✨ Phase 0
│   ├── llm_config_list.py        ✨ Phase 0
│   ├── llm_config_list.json.template  ✨ Phase 0
│   ├── prompts.py                ✨ Phase 0 + 1.7
│   ├── ExpertsRS_notebook.ipynb  ✨ Phase 0 + 1.7
│   ├── data/
│   └── tools/                    ✨ Phase 1（新增）
│       ├── __init__.py
│       ├── io_kit.py
│       ├── index_kit.py
│       ├── analysis_kit.py
│       ├── viz_kit.py
│       └── registry.py
└── assets/
```

---

## 阶段性总结：全部改动一览

### Phase 0 — 漏洞修复 ✅

| 文件 | 改动 |
|------|------|
| `ExpertsRS/llm_config_list.py` | 新建，从 `.env` 读取 API key |
| `ExpertsRS/.env.example` | 新建，用户填写指南 |
| `ExpertsRS/llm_config_list.json` → `.json.template` | 重命名，保留为模板参考 |
| `.gitignore` | 新建，排除 `.env`、`results/`、`__pycache__/` |
| `requirements.txt` | 新建，依赖清单 |
| `prompts.py` | 数据路径动态化（移除硬编码文件名） |
| `ExpertsRS_notebook.ipynb` | 配置加载重构、results 目录创建 |

### Phase 1 — 工具模块 ✅

| 文件 | 改动 |
|------|------|
| `tools/__init__.py` | 统一导出接口 |
| `tools/io_kit.py` | 5个工具：列表数据、读元数据、读单/多波段、保存栅格 |
| `tools/index_kit.py` | 6个工具：NDVI、EVI、NDWI、NBR、LST、MSAVI |
| `tools/analysis_kit.py` | 4个工具：阈值分割、面积统计、掩膜应用、区域统计 |
| `tools/viz_kit.py` | 3个工具：指数地图、专题图、假彩色合成 |
| `tools/registry.py` | AutoGen function_map + OpenAI schema 注册 |
| `prompts.py` | Engineer prompt 全面重构，工具优先 |
| `ExpertsRS_notebook.ipynb` | 新增工具加载 cell，Engineer 注册 function_map |
