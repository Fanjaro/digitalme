# DigitalMe

医学检测数据多 Agent 处理系统，基于 LangGraph 构建。从内部 API 提取原始 JSON 数据，经 12 个维度 Agent 并行处理，生成标准化健康检测报告。

## 架构

```
User → Supervisor (meta获取 + 路由) → Send 并行扇出 → 12个 dimension worker → synthesize → END
```

## 快速开始

```bash
cp .env.example .env
# 填入 ANTHROPIC_API_KEY
pip install -r requirements.txt

python main.py --list-dimensions    # 列出所有维度
python main.py --sample-id CD888888 # 指定样本运行
python main.py --interactive        # 交互模式
```

## 已注册维度 (12个, 15个前缀)

| 维度 | 前缀 | API | 说明 |
|------|------|-----|------|
| aging | KS, KS1027, TY | v1 | 衰老/亚健康 |
| cd | CD | v2 | 肠道微生物 |
| pf | PF | v2 | 皮肤微生物 |
| zl | ZL | v2 | 肿瘤ct-DNA |
| my | MY | v2 | 抗体免疫力 |
| zm | ZM | v2 | 自身免疫抗体 |
| gm | GM | v1 | 过敏原IgE |
| sw | SW, IgGFood | v1 | 食物不耐受IgG |
| dr | DR | v2 | 5大疾病风险 |
| yc | YC | v2 | 体细胞遗传突变 |
| smx | SMX | v2 | 女性私密微生物 |
| smy | SMY | v2 | 男性私密微生物 |

---

## 缺陷修复记录

### 已完成

| # | 缺陷 | 修复内容 | 涉及文件 |
|---|------|---------|---------|
| 1 | `.gitignore` 不完整 | 替换为标准 Python 忽略规则，补充 `.pytest_cache/`、`*.egg-info/`、`dist/` 等 | `.gitignore` |
| 2 | `dimensions/_base/` 未使用 | `DimensionResult` TypedDict 无任何引用，删除整个 `_base/` 目录 | `dimensions/_base/` (已删除) |
| 3 | 前缀注册不完整 | 注册 KS1027→aging、IgGFood→sw；`resolve_sample_id` 从固定 4/3/2 改为动态最长前缀匹配 | `dimensions/aging/config.yaml`, `dimensions/sw/config.yaml`, `dimensions/__init__.py` |
| 4 | 未注册前缀静默丢弃 | supervisor 对无法匹配的 sample_id 输出 warning 日志 | `supervisor.py`, `main.py` |
| 5 | `_agent_cache` 线程不安全 | LangGraph Send() 并行执行 dimension_worker，check-then-build 存在竞态；加 `threading.Lock` | `graph.py` |
| 6 | `get_llm()` 线程不安全 | 同上模式，加 `threading.Lock` | `config.py` |
| 7 | `skills/` 缺少 `__init__.py` | supervisor 用 `sys.path.insert` hack 导入；新建 `skills/__init__.py`，移除 hack | `skills/__init__.py` (新建), `supervisor.py` |
| 8 | API URL 硬编码在 12 个 tools.py 中 | 全部改为 `from config import API_V1_SAMPLES / API_V2_SAMPLES` | 12x `dimensions/*/tools.py`, `generator.py` |
| 9 | `create_react_agent` 已废弃 | langgraph v1.0 标记 deprecated，迁移到 `from langchain.agents import create_agent` | 12x `dimensions/*/__init__.py`, `generator.py`, `requirements.txt`, `pyproject.toml` |
| 10 | 缺少报告类型文档 | 基于公开 API 创建 25 个报告类型术语表 | `docs/report_types.md` (新建) |
| 11 | 缺少 URL 回归测试 | 扫描所有 tools.py 断言不含硬编码 IP | `tests/test_no_hardcoded_urls.py` (新建) |

### 未完成 (需要样本数据文件)

以下已上线报告类型在系统中无对应维度 Agent。需先用提取脚本获取 `_data.json` 样本，再通过 `generator.py` 生成。

| 前缀 | 产品名 | 备注 |
|------|--------|------|
| GR | 感染抗体评估 | meta 中有样本 (GR888888)，可尝试提取 |
| GY | 感染抗原评估 | 无样本数据 |
| ND | 内分泌代谢疾病风险评估 | 无样本数据 |
| CR | 心血管疾病风险评估 | 可能是 DR 子报告 |
| EM | 内分泌代谢系统健康评估 | 可能是 DR 子报告 |
| TR | 肿瘤风险筛查 | 可能是 DR 子报告 |
| szkl | 衰老与肿瘤风险精准检测评估报告 | meta 中有样本 (SZKL2603131106002)，综合型报告 |

生成新维度示例：

```bash
# 1. 提取样本数据
python skills/extract_data_v2.py GR888888 -d skills/data/

# 2. 自动生成维度 Agent
python generator.py --key "gr" --display-name "感染抗体评估" --prefixes "GR" \
    --data-file skills/data/GR888888_data.json
```

完整报告类型对照表见 [docs/report_types.md](docs/report_types.md)。

## 测试

```bash
python -m pytest tests/ -v   # 33 tests, all passing
```
