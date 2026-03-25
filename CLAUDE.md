# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

DigitalMe 是一套医学检测数据处理流水线，从内部 API（`http://180.184.28.174:30080`）提取原始 JSON 数据，经过预处理和 AI 转换，生成标准化的直测数据模板（measurement template），用于健康检测报告。

项目以 Python "Skill" 为单位组织，每个 Skill 负责一类医学检测数据的处理。

## 架构

### 数据流

```
内部 API (v1/v2) → 提取脚本 → 原始 JSON → Processor Skill (trans_json 预处理 + AI 转换) → 标准化 JSON
```

两个阶段：
1. **数据提取**：从内部样本/用户 API 拉取原始数据，保存为 `{sample_id}_data.json` 或 `{sample_id}_meta.json`
2. **数据转换**：通过 `trans_json/` 模块预处理大 JSON 为小 JSON，再用 Coze AI API（`api.coze.cn/v3/chat`）配合医学领域提示词转换为标准化模板

### 核心模块

| 文件 | 类名 | 用途 |
|------|------|------|
| `skills/extract_data_v1.py` | `DetailedDataExtractor` | 从 `/api/v1/samples/{id}` 提取 v13_results（衰老机制、器官衰老、系统衰老、uniprot 蛋白数据） |
| `skills/extract_data_v2.py` | `DataExtractor` | 从 `/api/v2/samples/{id}` 提取附录/补充数据（肿瘤、免疫、消化等） |
| `skills/extract_meta.py` | `MetaExtractor` | 从 `/api/v1/users/by-sample/{id}` 提取用户人口学信息和关联样品列表 |
| `skills/cd_processor.py` | `CDProcessorSkill` | 处理 CD（肠道菌群）数据，预处理模块 `trans_json/CD.py` |
| `skills/pf_processor.py` | `PFProcessorSkill` | 处理 PF（蛋白质功能/菌群多样性）数据，预处理模块 `trans_json/PF.py` |
| `skills/zl_processor.py` | `ZLProcessorSkill` | 处理 ZL（ctDNA 肿瘤标志物）数据，预处理模块 `trans_json/ZL.py` |

### Processor Skill 统一模式

所有 Processor Skill（CD、PF、ZL）遵循相同的处理流程：
1. `preprocess_data()` — 调用 `trans_json/{TYPE}.py` 将大 JSON 转为小 JSON
2. `get_ai_prompt()` — 生成包含医学背景知识的领域提示词，内嵌小 JSON 数据
3. `call_ai_api()` — 通过 httpx 异步调用 Coze API，解析返回的 JSON
4. `process()` — 串联完整流程

### Skill 文档约定

每个 `.py` Skill 都有同名 `.md` 文件，包含 YAML frontmatter（`name`、`description`、`data_type`、`trans_module`）和详细的医学背景说明。

### 数据目录

- `skills/data/` — 各检测类型的示例输出（`*_META.json` 为元数据结构定义，`*_data.json` 为检测数据）
- `skills/data/多模态图文对/` — 多模态图文对数据（如肺部 MRI 影像描述）
- `skills/meta/` — 用户元数据示例

## 常用命令

```bash
# 提取详细数据（v1 API）
python skills/extract_data_v1.py SAMPLE_ID [-d 输出目录]
python skills/extract_data_v1.py -f sample_ids.txt -w 8 --delay 0.2

# 提取附录数据（v2 API）
python skills/extract_data_v2.py SAMPLE_ID [-d 输出目录]

# 提取用户元数据
python skills/extract_meta.py SAMPLE_ID [-d 输出目录]
python skills/extract_meta.py -f sample_list.txt -d ./metadata
```

所有提取脚本通用参数：`-s`（单个）、`-m`（逗号分隔多个）、`-f`（从文件读取）、`-w`（并发线程数）、`--delay`（请求间隔）、`-b`（自定义 API 地址）。

## 依赖

- `requests` — 提取脚本的 HTTP 客户端
- `httpx` — Processor Skill 异步调用 Coze API
- 标准库：`json`、`argparse`、`concurrent.futures`、`asyncio`

## 约定

- 样本 ID 格式：字母前缀 + 数字编号（如 `CD888888`、`PF999999`、`SZKL2603161324001`）
- 字母前缀决定使用哪个 Processor Skill（CD→肠道菌群、PF→蛋白质功能、ZL→肿瘤标志物）
- 标准化输出模板统一字段：`name`、`value`、`range`、`abnormal`、`unit`、`category`、`clinical_significance`
- 中文医学术语在输出中原样保留
- `trans_json/` 预处理模块在代码中被引用，但尚未纳入仓库

## 多 Agent 系统（LangGraph）

### 框架

基于 LangGraph 的多 Agent 系统，Supervisor 负责对话/路由/汇总，12 个维度 Agent 各自独立处理一类检测数据。

### 架构

```
User → Supervisor (meta 获取 + 路由) → [Send 并行扇出] → 12 个 dimension worker → synthesize → END
```

### dimensions/ 文件夹结构

每个维度 Agent 是 `dimensions/{key}/` 下的自包含文件夹：

```
dimensions/{key}/
├── __init__.py      # build_agent(llm) → CompiledGraph
├── config.yaml      # 结构化配置（前缀、API、数据路径、医学领域等）
├── tools.py         # 该 Agent 专属的 @tool 函数（自包含 HTTP session）
└── prompt.md        # 系统提示词（医学背景 + 输出格式）
```

### 自动发现机制

`dimensions/__init__.py` 扫描所有含 `config.yaml` 的子文件夹自动注册。`_base/` 以 `_` 开头被跳过。添加新维度 = 添加新文件夹，无需修改主图代码。

### 12 个维度

| 文件夹 | 维度 | 前缀 | API |
|--------|------|------|-----|
| `cd/` | 肠道微生物 | CD | v2 |
| `pf/` | 皮肤微生物 | PF | v2 |
| `zl/` | 肿瘤ct-DNA | ZL | v2 |
| `my/` | 抗体免疫力 | MY | v2 |
| `zm/` | 自身免疫抗体 | ZM | v2 |
| `aging/` | 衰老/亚健康 | KS, TY | v1 |
| `gm/` | 过敏原IgE | GM | v1 |
| `sw/` | 食物不耐受IgG | SW | v1 |
| `dr/` | 5大疾病风险 | DR | v2 |
| `yc/` | 体细胞遗传突变 | YC | v2 |
| `smx/` | 女性私密微生物 | SMX | v2 |
| `smy/` | 男性私密微生物 | SMY | v2 |

### generator.py 自动生成

```bash
python generator.py --key "newdim" --display-name "新维度" --prefixes "ND" \
    --data-file skills/data/新维度_data.json --meta-file skills/data/新维度_META.json
```

### 常用命令

```bash
# 运行主系统（交互式）
python main.py

# 指定样本ID运行
python main.py --sample-id CD888888

# 自动生成新 Agent
python generator.py --key "gr" --display-name "肠道生态" --prefixes "GR" \
    --data-file skills/data/肠道生态_data.json --meta-file skills/data/肠道生态_META.json
```

### 新增依赖

- `langgraph` — 多 Agent 图编排
- `langchain-core` — LLM 抽象和 tool 定义
- `langchain-anthropic` — Claude 模型集成
- `python-dotenv` — 环境变量管理
- `pyyaml` — config.yaml 解析
- `pydantic` — 数据模型验证
