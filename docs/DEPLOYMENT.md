# DigitalMe 部署文档

> 版本: 0.1.0 | 更新日期: 2026-03-24

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [环境要求](#3-环境要求)
4. [安装步骤](#4-安装步骤)
5. [配置说明](#5-配置说明)
6. [部署模式](#6-部署模式)
7. [运行与启动](#7-运行与启动)
8. [测试与验证](#8-测试与验证)
9. [目录结构参考](#9-目录结构参考)
10. [故障排查](#10-故障排查)
11. [安全注意事项](#11-安全注意事项)
12. [附录](#12-附录)

---

## 1. 项目概述

DigitalMe 是一套医学检测数据处理系统，包含两个核心子系统:

| 子系统 | 入口 | 协议 | 说明 |
|--------|------|------|------|
| **多 Agent 分析引擎** | `main.py` | CLI | 基于 LangGraph 的 12 维度并行分析，输出 Markdown 健康报告 |
| **健康对话 Web 服务** | `server.py` | HTTP + WebSocket | FastAPI 驱动的交互式健康问诊，引导用户完成多轮检测分析 |

**数据流:**

```
用户/样本 → 内部 API (v1/v2) → 维度 Agent (并行) → Claude LLM 分析 → 标准化健康报告
```

---

## 2. 系统架构

### 2.1 多 Agent 引擎 (LangGraph)

```
                         ┌──────────┐
                         │  用户输入  │
                         └─────┬────┘
                               ▼
                      ┌────────────────┐
                      │   Supervisor   │  ← 获取 meta、解析样本前缀、路由维度
                      └────────┬───────┘
                               │ Send() 并行扇出
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ aging    │    │   cd     │    │   zl     │  ... (共 12 个维度 Worker)
        └─────┬────┘    └─────┬────┘    └─────┬────┘
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                     ┌────────────────┐
                     │   Synthesize   │  ← 汇总所有维度结果，生成最终报告
                     └────────────────┘
```

### 2.2 Web 服务 (FastAPI + WebSocket)

```
浏览器 ──WebSocket──► FastAPI server.py
                         │
                         ├─ 状态机驱动对话流程
                         │   GREETING → WAIT_DESCRIPTION → HEALTH_INTERVIEW
                         │   → SYMPTOM_ANALYSIS → SUGGEST_DIMS → RUNNING
                         │   → ROUND_RESULT → FINAL_REPORT → DONE
                         │
                         ├─ Mock 模式: mock_data.py (无需外部 API)
                         └─ Real 模式: 调用 LangGraph 引擎
```

### 2.3 12 个维度 Agent

| 维度 | 文件夹 | 样本前缀 | API 版本 | 检测领域 |
|------|--------|----------|----------|----------|
| 衰老/亚健康 | `dimensions/aging/` | KS, TY | v1 | 衰老机制、器官衰老 |
| 肠道微生物 | `dimensions/cd/` | CD | v2 | 肠道菌群多样性 |
| 皮肤微生物 | `dimensions/pf/` | PF | v2 | 皮肤菌群 |
| 肿瘤 ct-DNA | `dimensions/zl/` | ZL | v2 | ctDNA 肿瘤标志物 |
| 抗体免疫力 | `dimensions/my/` | MY | v2 | 免疫功能 |
| 自身免疫抗体 | `dimensions/zm/` | ZM | v2 | 自身免疫 |
| 过敏原 IgE | `dimensions/gm/` | GM | v1 | 过敏原检测 |
| 食物不耐受 IgG | `dimensions/sw/` | SW | v1 | 食物不耐受 |
| 5大疾病风险 | `dimensions/dr/` | DR | v2 | 疾病风险筛查 |
| 体细胞遗传突变 | `dimensions/yc/` | YC | v2 | 遗传突变检测 |
| 女性私密微生物 | `dimensions/smx/` | SMX | v2 | 女性菌群 |
| 男性私密微生物 | `dimensions/smy/` | SMY | v2 | 男性菌群 |

每个维度是自包含文件夹，通过 `config.yaml` 自动发现注册，**新增维度无需修改主图代码**。

---

## 3. 环境要求

### 3.1 运行环境

| 项目 | 要求 |
|------|------|
| **操作系统** | Linux (Ubuntu 22.04 推荐) / macOS |
| **Python** | >= 3.10 (推荐 3.12) |
| **内存** | >= 2 GB |
| **网络** | 需访问 Anthropic API (`api.anthropic.com`) |
| **内部 API** | 需访问 `http://10.1.20.128:30080` (Real 模式) |

### 3.2 外部服务依赖

| 服务 | 用途 | 必须? |
|------|------|-------|
| Anthropic Claude API | LLM 推理 (多 Agent 分析) | Real 模式必须 |
| 内部样本 API (v1/v2) | 拉取原始检测数据和用户元数据 | Real 模式必须 |

> Mock 模式下两者均不需要，可用于演示和测试。

---

## 4. 安装步骤

### 4.1 获取代码

```bash
git clone https://github.com/Fanjaro/digitalme.git
cd digitalme
```

### 4.2 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4.3 安装依赖

```bash
# 生产依赖
pip install -r requirements.txt

# 如需运行测试 (含 pytest + Playwright)
pip install -e ".[test]"
playwright install chromium
```

### 4.4 完整依赖清单

**生产依赖:**

| 包 | 版本 | 用途 |
|----|------|------|
| `langgraph` | >= 0.2.0 | 多 Agent 图编排 |
| `langchain` | >= 1.2.0 | LLM 工具链 |
| `langchain-core` | >= 0.3.0 | LLM 抽象层 |
| `langchain-anthropic` | >= 0.3.0 | Claude 模型集成 |
| `fastapi` | >= 0.115.0 | Web 框架 |
| `uvicorn[standard]` | >= 0.30.0 | ASGI 服务器 |
| `websockets` | >= 12.0 | WebSocket 支持 |
| `requests` | >= 2.31.0 | 同步 HTTP 客户端 |
| `httpx` | >= 0.27.0 | 异步 HTTP 客户端 |
| `python-dotenv` | >= 1.0.0 | 环境变量管理 |
| `pydantic` | >= 2.0 | 数据模型验证 |
| `pyyaml` | >= 6.0 | YAML 配置解析 |

**测试依赖:**

| 包 | 版本 | 用途 |
|----|------|------|
| `pytest` | >= 8.0 | 测试框架 |
| `pytest-asyncio` | >= 0.24.0 | 异步测试支持 |
| `responses` | >= 0.25.0 | HTTP Mock |
| `playwright` | latest | 浏览器自动化 E2E 测试 |

---

## 5. 配置说明

### 5.1 环境变量

复制模板并填写:

```bash
cp .env.example .env
```

`.env` 文件内容:

```bash
# [必填] Anthropic API 密钥
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxx

# [必填-Real模式] 内部数据 API 地址
INTERNAL_API_BASE_URL=http://10.1.20.128:30080

# [可选] 覆盖默认模型 (默认: claude-sonnet-4-20250514)
# ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | (无) | Anthropic API 密钥，Real 模式必填 |
| `INTERNAL_API_BASE_URL` | `http://10.1.20.128:30080` | 内部样本数据 API 基地址 |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude 模型 ID |

### 5.2 配置文件层级

```
.env                          ← 环境变量 (密钥、API 地址)
config.py                     ← 全局配置 (读取 .env，构造 API URL，初始化 LLM)
dimensions/{key}/config.yaml  ← 各维度独立配置 (前缀、数据路径、医学领域)
```

### 5.3 维度配置 (config.yaml) 示例

```yaml
dimension:
  key: cd
  display_name: 肠道微生物
  description: 肠道菌群多样性与健康分析

sample_id:
  prefixes: [CD]
  pattern: "^CD\\d+"

api:
  version: v2
  extractor_class: DataExtractor

data_extraction:
  structure_type: appendix_sections
  paths: [...]

medical_expertise:
  domain: 肠道微生物学
  keywords: [菌群, 多样性, 益生菌]
```

---

## 6. 部署模式

### 6.1 本地开发 (Mock 模式)

**适用场景:** 本地开发、演示、无外部 API 访问

```bash
# Web 服务 (Mock 数据，无需 API 密钥)
python server.py --mock --port 8000

# CLI (Mock 模式自动使用内置数据)
python main.py --sample-id CD888888
```

Mock 模式使用 `mock_data.py` 中的预设数据:
- 用户: 张明远 (42岁，男)
- 9 个样本 (KS888888, CD888888, DR888888 等)
- 预写的分析结果 Markdown

### 6.2 服务器部署 (Real 模式)

**适用场景:** 连接真实内部 API 和 Claude LLM 进行生产分析

**前置条件:**
- `.env` 中已配置 `ANTHROPIC_API_KEY`
- 服务器可访问 `INTERNAL_API_BASE_URL` (内部 API)
- 服务器可访问 `api.anthropic.com` (Claude API)

```bash
# Web 服务 (Real 模式)
python server.py --real --host 0.0.0.0 --port 8000

# CLI (指定真实样本 ID)
python main.py --sample-id SZKL2603161324001
```

### 6.3 使用 systemd 做持久化服务 (Linux)

创建 `/etc/systemd/system/digitalme.service`:

```ini
[Unit]
Description=DigitalMe Health Analysis Web Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/digitalme
EnvironmentFile=/opt/digitalme/.env
ExecStart=/opt/digitalme/.venv/bin/python server.py --real --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable digitalme
sudo systemctl start digitalme
sudo systemctl status digitalme
```

### 6.4 配合 ALB 的生产部署 (AWS)

按照团队安全规范，生产环境需走 ALB + Cognito 认证:

```
用户 → ALB (HTTPS + Cognito 认证) → EC2:8000 (DigitalMe server.py)
```

**关键要求:**
- EC2 安全组仅允许来自 ALB 安全组的 8000 端口流量，**禁止对 0.0.0.0/0 开放**
- ALB HTTPS 监听器配置 `authenticate-cognito` action
- 使用 SSM Session Manager 连接 EC2，**禁止开放 SSH 22 端口**
- Cognito callback URL: `https://<domain>/oauth2/idpresponse`

**部署步骤概要:**

```bash
# 1. 通过 SSM 连接 EC2
aws ssm start-session --target <instance-id>

# 2. 上传代码 (通过 S3 中转)
aws s3 cp s3://your-bucket/digitalme.tar.gz /opt/
cd /opt && tar xzf digitalme.tar.gz && cd digitalme

# 3. 安装依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY

# 5. 启动服务
python server.py --real --host 127.0.0.1 --port 8000

# 6. 配置 systemd (见 6.3 节) 做持久化
```

---

## 7. 运行与启动

### 7.1 Web 服务 (server.py)

```bash
# 完整参数
python server.py [--mock|--real] [--host HOST] [--port PORT]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--mock` | (默认) | 使用内置 Mock 数据，无需外部 API |
| `--real` | - | 连接真实 API 进行分析 |
| `--host` | `0.0.0.0` | 监听地址 |
| `--port` | `8000` | 监听端口 |

启动后访问:
- 页面: `http://<host>:<port>/`
- WebSocket: `ws://<host>:<port>/ws`

### 7.2 CLI 模式 (main.py)

```bash
# 列出所有已注册维度
python main.py --list-dimensions

# 指定样本 ID 运行分析
python main.py --sample-id CD888888

# 交互式模式
python main.py --interactive
```

### 7.3 数据提取工具 (skills/)

```bash
# 提取 v1 详细数据
python skills/extract_data_v1.py SAMPLE_ID [-d 输出目录]

# 提取 v2 附录数据
python skills/extract_data_v2.py SAMPLE_ID [-d 输出目录]

# 提取用户元数据
python skills/extract_meta.py SAMPLE_ID [-d 输出目录]

# 批量提取
python skills/extract_data_v1.py -f sample_ids.txt -w 8 --delay 0.2
```

### 7.4 自动生成新维度 Agent

```bash
python generator.py \
  --key "newdim" \
  --display-name "新维度" \
  --prefixes "ND" \
  --data-file skills/data/新维度_data.json \
  --meta-file skills/data/新维度_META.json
```

生成后自动注册，无需修改主图代码。

---

## 8. 测试与验证

### 8.1 单元测试 + 集成测试

```bash
# 运行全部测试 (约 115 个用例)
python -m pytest tests/ -v

# 运行指定模块
python -m pytest tests/test_server.py -v
python -m pytest tests/test_graph.py -v
python -m pytest tests/test_integration.py -v

# 查看测试覆盖率
python -m pytest tests/ -v --tb=short
```

**测试矩阵:**

| 测试文件 | 覆盖范围 |
|----------|----------|
| `test_graph.py` | Graph 编译、状态结构、维度路由 |
| `test_supervisor.py` | 前缀解析、合成逻辑 |
| `test_dimension_agents.py` | 各维度 Agent 构建 |
| `test_dimension_tools.py` | 数据提取 (Mock HTTP) |
| `test_registry.py` | 自动发现、前缀映射 |
| `test_tools.py` | Tool 函数调用 |
| `test_integration.py` | 端到端 Graph 调用 |
| `test_server.py` | WebSocket 协议、会话状态、异步处理 |
| `test_no_hardcoded_urls.py` | 回归测试: 无硬编码 IP |

### 8.2 Playwright E2E 测试 (UAT)

```bash
# 前置: 安装 Playwright
pip install playwright
playwright install chromium

# 先启动 Web 服务 (Mock 模式)
python server.py --mock --port 8765 &

# 运行 20 个 UAT 用例
python tests/uat_playwright.py
```

**UAT 测试用例 (20 个):**

| ID | 测试内容 | 预期耗时 |
|----|----------|----------|
| T01 | 页面加载与布局 | ~1s |
| T02 | WebSocket 问候消息 | ~1s |
| T03 | 症状输入与问诊卡片 | ~1s |
| T04 | 问诊回答与维度推荐 | ~2s |
| T05 | 选项芯片预选与切换 | ~3s |
| T06 | 确认与进度指示器 | ~10s |
| T07 | 第一轮结果展示 | ~13s |
| T08 | 追问输入与第二轮推荐 | ~16s |
| T09 | 第二轮确认与进度 | ~24s |
| T10 | 第三轮完整流程 | ~39s |
| T11 | 最终报告卡片 | ~39s |
| T12 | DONE 状态回复 | ~42s |
| T13 | Demo 模式切换与自动播放 | ~4s |
| T14 | Demo 暂停 (wait_for_input) | ~4s |
| T15 | Demo 用户交互恢复 | ~8s |
| T16 | 响应式布局 (移动端) | ~1s |
| T17 | Markdown 渲染 | ~2s |
| T18 | 空输入忽略 | ~2s |
| T19 | 多进度卡片共存 | ~8s |
| T20 | 报告卡片关键章节 | ~39s |

**产出物:**
- `UAT_REPORT.md` — 测试报告
- `uat_screenshots/` — 29 张截图

### 8.3 部署后冒烟测试

部署完成后，执行以下快速验证:

```bash
# 1. 检查服务是否启动
curl -s http://localhost:8000/ | head -5

# 2. WebSocket 连通性 (需要 wscat)
# npm install -g wscat
wscat -c ws://localhost:8000/ws
# 连接后应收到 greeting 消息

# 3. 检查维度注册
python main.py --list-dimensions
# 应输出 12 个维度

# 4. Mock 模式端到端
python main.py --sample-id CD888888
# 应输出分析报告
```

---

## 9. 目录结构参考

```
digitalme/
├── .env.example                  # 环境变量模板
├── .gitignore
├── pyproject.toml                # 项目元数据 & 依赖声明
├── requirements.txt              # pip 依赖
├── CLAUDE.md                     # 项目开发指引
├── README.md
│
├── config.py                     # 全局配置 (LLM、API URL)
├── main.py                       # CLI 入口
├── graph.py                      # LangGraph StateGraph 定义
├── supervisor.py                 # Supervisor + Synthesize 节点
├── server.py                     # FastAPI + WebSocket 服务
├── generator.py                  # 维度 Agent 代码生成器
├── mock_data.py                  # Mock 用户 & 结果数据
│
├── dimensions/                   # 12 个维度 Agent (自动发现)
│   ├── __init__.py               # 注册中心 & 自动发现
│   ├── aging/
│   │   ├── __init__.py           # build_agent(llm)
│   │   ├── config.yaml           # 维度配置
│   │   ├── tools.py              # @tool 数据提取函数
│   │   └── prompt.md             # 系统提示词
│   ├── cd/                       # (同上结构)
│   ├── pf/
│   ├── zl/
│   ├── my/
│   ├── zm/
│   ├── gm/
│   ├── sw/
│   ├── dr/
│   ├── yc/
│   ├── smx/
│   └── smy/
│
├── skills/                       # 数据提取工具
│   ├── extract_data_v1.py        # v1 API 提取
│   ├── extract_data_v2.py        # v2 API 提取
│   ├── extract_meta.py           # 用户元数据提取
│   ├── data/                     # 示例数据 JSON
│   └── meta/                     # 元数据示例
│
├── static/                       # Web 前端
│   ├── chat.html                 # 聊天界面
│   └── mock_conversation.json    # Demo 对话数据
│
├── tests/                        # 测试套件
│   ├── conftest.py               # 测试 fixtures
│   ├── test_graph.py
│   ├── test_supervisor.py
│   ├── test_dimension_agents.py
│   ├── test_dimension_tools.py
│   ├── test_registry.py
│   ├── test_tools.py
│   ├── test_integration.py
│   ├── test_server.py
│   ├── test_no_hardcoded_urls.py
│   └── uat_playwright.py         # Playwright E2E (20 用例)
│
├── docs/
│   ├── DEPLOYMENT.md             # 本文档
│   └── report_types.md           # 25 种报告类型定义
│
├── uat_screenshots/              # UAT 截图
└── UAT_REPORT.md                 # UAT 测试报告
```

---

## 10. 故障排查

### 10.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ModuleNotFoundError: No module named 'langgraph'` | 依赖未安装 | `pip install -r requirements.txt` |
| `AuthenticationError: Invalid API Key` | ANTHROPIC_API_KEY 未配置或无效 | 检查 `.env` 文件中的密钥 |
| `ConnectionRefusedError: 10.1.20.128:30080` | 内部 API 不可达 | 确认网络连通性，或使用 `--mock` 模式 |
| 页面打开空白 | `static/` 目录缺失 | 确认 `static/chat.html` 存在 |
| WebSocket 连接失败 | 端口被占用或防火墙拦截 | `lsof -i :8000` 检查端口; 检查安全组规则 |
| `asyncio` 相关错误 | Python 版本过低 | 确认 Python >= 3.10 |
| 维度 Agent 未注册 | `config.yaml` 缺失或格式错误 | `python main.py --list-dimensions` 验证 |

### 10.2 日志排查

```bash
# server.py 使用 Python logging，默认输出到 stdout
# 可通过环境变量或代码调整日志级别

# 查看 LangGraph 执行详情
export LANGCHAIN_VERBOSE=true
python main.py --sample-id CD888888

# 查看 HTTP 请求详情
export HTTPX_LOG_LEVEL=debug
python server.py --real
```

### 10.3 健康检查

```bash
# 进程存活
pgrep -f "server.py" && echo "Running" || echo "Stopped"

# 端口监听
ss -tlnp | grep 8000

# HTTP 可达
curl -sf http://localhost:8000/ > /dev/null && echo "OK" || echo "FAIL"
```

---

## 11. 安全注意事项

### 11.1 密钥管理

- `.env` 文件已在 `.gitignore` 中排除，**绝不提交到 Git**
- `ANTHROPIC_API_KEY` 建议使用 AWS Secrets Manager 或 SSM Parameter Store 管理
- 生产环境通过 `EnvironmentFile` (systemd) 或 AWS SSM 注入，避免明文存储

### 11.2 网络安全 (AWS 部署)

- EC2 服务端口 (8000) **仅允许 ALB 安全组入站**，禁止 0.0.0.0/0
- SSH (22) **禁止开放**，统一使用 SSM Session Manager
- ALB 强制 HTTPS + Cognito 认证
- 文件传输使用 S3 中转，不使用 scp

### 11.3 应用安全

- WebSocket 消息使用 JSON 格式校验
- 内部 API 地址不硬编码在维度 tools.py 中 (通过 `test_no_hardcoded_urls.py` 回归测试保证)
- Mock 模式不暴露真实用户数据

---

## 12. 附录

### 12.1 WebSocket 消息协议

**服务端 → 客户端:**

```jsonc
// 聊天消息
{"type": "message", "role": "assistant", "content": "您好..."}

// 问诊问题
{"type": "interview", "questions": ["您的睡眠情况如何?", ...]}

// 维度选择
{"type": "options", "question": "推荐以下检测维度", "options": [...], "multi_select": true}

// 分析进度
{"type": "progress", "dimension": "cd", "label": "肠道微生物", "status": "running|done|error"}

// 最终报告
{"type": "report", "content": "# 健康分析报告\n..."}

// 错误
{"type": "error", "message": "..."}
```

**客户端 → 服务端:**

```jsonc
// 用户消息
{"type": "message", "content": "我最近总是感觉疲劳..."}

// 问诊回答
{"type": "interview", "answers": ["睡眠质量差", ...]}

// 确认分析
{"type": "confirm", "value": true}

// 手动选择维度
{"type": "select", "selected": ["cd", "dr", "aging"]}
```

### 12.2 支持的模型

| 模型 ID | 说明 |
|---------|------|
| `claude-sonnet-4-20250514` | 默认，平衡性能与成本 |
| `claude-opus-4-6` | 最强推理能力 |
| `claude-haiku-4-5-20251001` | 最快响应速度 |

通过 `.env` 中 `ANTHROPIC_MODEL` 切换。

### 12.3 快速启动 Cheatsheet

```bash
# 一键本地启动 (Mock 模式)
git clone https://github.com/Fanjaro/digitalme.git && cd digitalme
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py --mock
# 浏览器访问 http://localhost:8000

# 一键运行测试
python -m pytest tests/ -v

# 一键 UAT
python server.py --mock --port 8765 &
python tests/uat_playwright.py
```
