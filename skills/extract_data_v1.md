---
name: 碳云V1框架数据处理
description: 处理碳云v1版本大JSON数据，提取每个指标数据块中uniprot蛋白的正常上下边界与检测值
data_type: JSON
---
# Skill: 提取样本详细检测数据 (Detailed Data Extractor)

## 技能描述
这是一个用于从指定API接口异步获取样本详细检测结果数据的技能。该技能会调用 `v1` 版本的样本接口，主要提取并结构化处理`v13_results`中的各类老化机制、器官老化、系统老化等详细数据，并输出为结构化的JSON文件。

## 核心功能
1.  **获取详细数据**: 访问 `http://10.1.20.128:30080/api/v1/samples/{sample_id}` 获取原始JSON数据。
2.  **结构化提取**: 从原始数据的 `data.v13_results` 路径中提取数据，并按`大类 -> 子类 -> 字段`的层次重新组织。
3.  **数据丰富**: 为每个子类数据添加类型标识（如 `organ_aging`, `system_aging`, `aging_mechanism`），并计算字段长度、风险蛋白比例等统计信息。
4.  **批量处理**: 支持通过列表、文件等方式输入多个样本ID，进行并发提取，提升效率。
5.  **结果输出**: 为每个成功处理的样本生成一个独立的 `{sample_id}_data.json` 文件。

## 输入/输出格式

### 输入参数
技能支持多种参数组合来指定要处理的样本ID：
*   `sample_ids` (列表): 直接提供多个样本ID，用空格分隔。
*   `-s, --single` (字符串): 指定单个样本ID。
*   `-m, --multiple` (字符串): 指定逗号分隔的多个样本ID（如 `id1,id2,id3`）。
*   `-f, --file` (字符串): 提供一个文本文件路径，文件每行包含一个样本ID。

**其他配置参数：**
*   `-b, --base-url` (字符串): API基础URL，默认值为 `http://10.1.20.128:30080/api/v1/samples/`。
*   `-d, --output-dir` (字符串): 指定JSON文件的输出目录，默认为当前目录。
*   `-w, --workers` (整数): 设置最大并发工作线程数，默认为5。
*   `--delay` (浮点数): 设置请求之间的延迟（秒），默认为0.1，用于控制请求频率。
*   `--timeout` (整数): 设置单个请求的超时时间（秒），默认为30。

### 输出格式
成功执行后，会在指定输出目录生成名为 `{sample_id}_data.json` 的文件。
文件内容结构示例：
***json
{
  "sample_id": "SZKL2603161324001",
  "extraction_time": "2024-01-01 12:00:00",
  "source_url": "http://10.1.20.128:30080/api/v1/samples/SZKL2603161324001",
  "report_type": "standard",
  "collected_at": "2023-12-31",
  "status": "success",
  "data": {
    "aging_mechanisms": {
      "cellular_senescence": {
        "type": "aging_mechanism",
        "pred_quantile": 0.75,
        "pred_raw": 0.023,
        "uniprot": ["P12345", "Q67890"],
        "value": [1.2, 0.8],
        "uniprot_count": 2,
        "value_count": 2,
        "risk_ratio": "1/2"
      }
    },
    "organ_aging": {
      "pa_organ_brain": {
        "type": "organ_aging",
        "pred_quantile": 0.6,
        "pred_raw": 0.015
      }
    }
  }
}
***

## 使用场景/示例
**场景**：需要批量获取一批样本的详细检测数据，用于后续的分析、报告生成或模型训练。

**示例命令**：
1.  **处理单个样本**:
    ***bash
    python extract_data_V1.py SZKL2603161324001
    ***
2.  **处理单个样本并指定输出目录**:
    ***bash
    python extract_data_V1.py SZKL2603161324001 -d ./detailed_output
    ***
3.  **处理多个样本（直接输入）**:
    ***bash
    python extract_data_V1.py SZKL2603161324001 SZKL2603161324002 SZKL2603161324003
    ***
4.  **从文件读取样本ID列表进行批量处理**:
    ***bash
    python extract_data_V1.py -f sample_ids.txt -d ./detailed_results -w 8 --delay 0.2
    ***
    (`sample_ids.txt` 内容示例: 每行一个ID，空行或以`#`开头的行会被忽略)
5.  **在Python代码中调用**:
    ***python
    from extract_data_V1 import DetailedDataExtractor
    extractor = DetailedDataExtractor(base_url=“你的API地址”)
    # 处理单个样本
    success = extractor.process_single_sample(“SZKL2603161324001”, “./output“)
    # 批量处理
    results = extractor.process_multiple_samples([“id1“, “id2“], “./output“, max_workers=5)
    ***
