# 第一章可重建环境清单

> 记录时间：2026-08-11；用途：无 API M1/D2 基线复现，不是完整生产部署清单。

## 已验证运行环境

| 项目 | 值 |
| --- | --- |
| 操作系统 | Windows（PowerShell） |
| Python | 3.11.5 |
| Python 发行版 | Anaconda，解释器路径为 `D:\software\Anaconda\python.exe` |
| Git | 2.44.0.windows.1 |
| 输入栅格 | `ExpertsRS/data/Sentinel2_Dongcheng_20230718.tif` |
| 输入栅格 SHA-256 | `557E28C8E947C609DD57E20E7854DF0F775648223F8BC2197BC8297A4C739F9F` |

## 关键已安装版本

```text
numpy 1.26.4
pandas 2.2.3
scipy 1.11.4
rasterio 1.4.3
geopandas 1.0.1
shapely 2.1.1
pyproj 3.7.1
matplotlib 3.8.0
pytest 7.4.0
openai 2.38.0
requests 2.32.5
python-dotenv 1.0.1
jupyter 1.0.0
ipykernel 6.25.0
```

## 当前边界

本清单支持仓库内的无 API M1/D2 closeout。当前环境尚未完整满足
`requirements.txt`：`GDAL`、`contextily`、`folium`、`autogen-agentchat`、
`autogen-ext` 和 `anthropic` 未被当前解释器发现；Earth Engine 依赖在
requirements 中是可选项。真实 LLM 对照前必须另行锁定 provider、模型、预算、
包版本和调用记录，不能把本清单当作正式实验环境锁定。

## 重建入口

从 `ExpertsRS/` 执行：

```powershell
python run_m1_closeout.py
python run_d2_closeout.py
```

两条命令会把时间戳结果写入被 Git 忽略的 `ExpertsRS/results/`；可读证据和哈希
记录分别见 `docs/evidence/ch1_m1/README.md` 与 `docs/evidence/ch1_d2/README.md`。
