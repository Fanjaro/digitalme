---
name: 碳云V2框架数据处理
description: 处理碳云v2版本大JSON数据，提取每个指标数据块中uniprot蛋白的正常上下边界与检测值
data_type: JSON
---
# Skill: 提取样本用户元数据 (Metadata Extractor)
## 技能描述
这是一个用于从指定API接口异步获取样本关联用户元数据信息的技能。该技能调用用户信息接口，提取样本所属用户的个人信息（如姓名、性别、出生日期、身高、体重、联系方式等）以及样本采集时间等元数据。

## 核心功能
1.  **获取用户元数据**: 访问 `http://10.1.20.128:30080/api/v1/users/by-sample/{sample_id}` 获取原始JSON数据，并解析出`result.Response.Data`中的有效信息。
2.  **数据解析与增强**: 对原始数据中的时间戳字段（如`_birthday`, `_UpdatedAt`）进行解析，提取可读的日期部分。
3.  **关键信息输出**: 处理完成后，会在控制台打印关键信息的摘要，如姓名、性别、生日、BMI、采集时间等。
4.  **批量处理**: 支持通过列表、文件等方式输入多个样本ID，进行并发提取。
5.  **结果输出**: 为每个成功处理的样本生成一个独立的 `{sample_id}_meta.json` 文件。

## 输入/输出格式

### 输入参数
技能支持多种参数组合来指定要处理的样本ID：
*   `sample_ids` (列表): 直接提供多个样本ID，用空格分隔。
*   `-s, --single` (字符串): 指定单个样本ID。
*   `-m, --multiple` (字符串): 指定逗号分隔的多个样本ID（如 `id1,id2,id3`）。
*   `-f, --file` (字符串): 提供一个文本文件路径，文件每行包含一个样本ID。

**其他配置参数：**
*   `-b, --base-url` (字符串): API基础URL，默认值为 `http://10.1.20.128:30080/api/v1/users/by-sample/`。
*   `-d, --output-dir` (字符串): 指定JSON文件的输出目录，默认为当前目录。
*   `-w, --workers` (整数): 设置最大并发工作线程数，默认为5。
*   `--delay` (浮点数): 设置请求之间的延迟（秒），默认为0.1。
*   `--timeout` (整数): 设置单个请求的超时时间（秒），默认为20。

### 输出格式
成功执行后，会在指定输出目录生成名为 `{sample_id}_meta.json` 的文件。
文件内容结构示例：
***json
{
  "sample_id": "SZKL2603161324001",
  "extraction_time": "2024-01-01 12:00:00",
  "source_url": "http://10.1.20.128:30080/api/v1/users/by-sample/SZKL2603161324001",
  "status": "success",
  "name": "张三",
  "sex": 1,
  "_birthday": "1970-01-01T00:00:00Z",
  "birthday_date": "1970-01-01",
  "height": 175,
  "weight": 70,
  "bmi": 22.86,
  "mobile": "13800138000",
  "_sampleCollectedAt": "2023-12-15T10:30:00Z",
  "_sampleCollectedAt_date": "2023-12-15"
}
***

## 使用场景/示例
**场景**：需要获取样本对应用户的人口统计学信息和样本采集时间，用于数据分析时的分组、筛选或作为模型特征。

**示例命令**：
1.  **处理单个样本**:
    ***bash
    python extract_meta.py SZKL2603161324001
    ***
2.  **处理单个样本并指定输出目录**:
    ***bash
    python extract_meta.py SZKL2603161324001 -d ./meta_output
    ***
3.  **处理多个样本**:
    ***bash
    python extract_meta.py SZKL2603161324001 SZKL2603161324002 SZKL2603161324003
    ***
4.  **从文件读取样本ID列表进行批量处理**:
    ***bash
    python extract_meta.py -f sample_list.txt -d ./metadata -w 8 --delay 0.2
    ***
5.  **在Python代码中调用**:
    ***python
    from extract_meta import MetaExtractor
    extractor = MetaExtractor(base_url=“你的API地址”)
    # 处理单个样本
    success = extractor.process_single_sample(“SZKL2603161324001”, “./output“)
    # 批量处理
    sample_list = [“id1”, “id2”, “id3“]
    results = extractor.process_multiple_samples(sample_list, “./output“)
    ***
