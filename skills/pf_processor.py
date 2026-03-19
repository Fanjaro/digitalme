#!/usr/bin/env python3
"""
PF蛋白质功能数据处理Skill实现
处理蛋白质功能检测大JSON数据，提取菌群多样性、结构分析等关键指标并转换为标准化直测数据模板
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

class PFProcessorSkill:
    """PF蛋白质功能数据处理Skill"""
    
    def __init__(self, ai_config: Dict[str, Any]):
        self.skill_name = "PF蛋白质功能数据处理"
        self.data_type = "PF"
        self.ai_config = ai_config
        self.trans_module = "trans_json/PF.py"
        
    def preprocess_data(self, json_file: str) -> Optional[str]:
        """
        调用trans_json模块进行数据预处理
        将大JSON转换为小JSON
        """
        print(f"🔄 开始预处理PF数据: {json_file}")
        
        try:
            # 切换到文件所在目录执行预处理
            file_dir = os.path.dirname(os.path.abspath(json_file))
            file_name = os.path.basename(json_file)
            
            # 构建命令
            cmd = [sys.executable, self.trans_module, file_name]
            
            # 在文件目录中执行
            result = subprocess.run(
                cmd, 
                cwd=file_dir,
                capture_output=True, 
                text=True, 
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                # 预处理成功，返回生成的小JSON文件路径
                base_name = os.path.splitext(file_name)[0]
                extracted_file = os.path.join(file_dir, f"{base_name}_extracted.json")
                if os.path.exists(extracted_file):
                    print(f"✅ 预处理完成: {extracted_file}")
                    return extracted_file
                else:
                    print(f"❌ 预处理文件未生成: {extracted_file}")
                    return None
            else:
                print(f"❌ 预处理失败: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ 预处理异常: {e}")
            return None
    
    def get_ai_prompt(self, small_json_data: Dict[str, Any]) -> str:
        """
        生成专门的PF蛋白质功能AI转换提示词
        """
        prompt = f"""
你是一位专业的宏基因组学和功能基因组学专家，请将以下蛋白质功能相关的肠道菌群检测数据转换为标准化的直测数据模板。

## 医学背景知识
基于宏基因组学技术分析肠道菌群的功能基因，包含：
- **多样性指数**: 反映菌群生态系统的复杂性和稳定性
  - Shannon指数：经典多样性指标，正常范围4.0-7.0
  - Simpson指数：均匀度指标，正常范围0.7-0.95
- **菌群结构**: 门水平和属水平的菌群组成分析
  - 门水平：最高分类层级（厚壁菌门、拟杆菌门等）
  - 属水平：中等分类层级（双歧杆菌属、乳杆菌属等）
- **功能基因**: 与蛋白质合成、代谢相关的基因功能分析
- **关键菌群**: 有益菌、条件致病菌、有害菌的分类分析

## 临床意义
- **Shannon指数**：菌群多样性的经典指标，值越高表示多样性越好
- **Simpson指数**：反映菌群均匀度，补充Shannon指数的不足
- **有益菌比例**：如双歧杆菌、乳杆菌等对健康有益的菌群
- **条件致病菌**：在特定条件下可能致病的菌群，需要监控
- **有害菌水平**：直接对健康有害的病原菌水平，应保持低水平

## 输入数据
```json
{json.dumps(small_json_data, ensure_ascii=False, indent=2)}
```

## 转换要求
请严格按照以下JSON格式输出，不要添加任何解释文字：

```json
[
  {{
    "sample_date": "采样日期（ISO格式）",
    "measurement": [
      {{
        "name": "指标类型 | 具体指标名称",
        "value": "数值（带单位）",
        "range": "参考范围",
        "abnormal": "异常状态（高/正常/低）",
        "unit": "单位（指数/%等）",
        "category": "分类（多样性指数/门水平/属水平/关键菌群）",
        "clinical_significance": "临床意义说明"
      }}
    ],
    "report_index": {{
      "diversity_shannon": "Shannon指数值",
      "diversity_simpson": "Simpson指数值",
      "beneficial_ratio": "有益菌比例",
      "conditional_pathogen_ratio": "条件致病菌比例",
      "harmful_ratio": "有害菌比例"
    }}
  }}
]
```

## 转换规则
1. 多样性指数：保留所有多样性指数信息，格式为"多样性指数 | Shannon指数"
2. 菌群结构：按照门水平、属水平分别组织，格式为"门水平 | 厚壁菌门"
3. 数值处理：保持原始精度，根据数据类型添加相应单位（指数、%等）
4. 异常判断：基于lowTh和hiTh阈值范围进行异常状态判断
5. 临床意义：为每个指标添加详细的临床意义和健康建议
6. 关键菌群：重点处理有益菌、条件致病菌、有害菌的信息
7. 统计指标：计算各类菌群的比例统计

## 特别注意
- PF数据包含更详细的功能基因信息，需要重点关注
- 多样性指数种类丰富，每个都有独特的临床意义
- 菌群分类精细，需要准确区分门、属、种三级
- 附录数据包含重要的菌群功能说明，不要遗漏

请直接输出JSON格式的结果，不要包含任何其他文字。
"""
        return prompt
    
    async def call_ai_api(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        调用AI API进行数据转换
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.ai_config['access_token']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "bot_id": self.ai_config["bot_id"],
                "user_id": "medical_processor",
                "stream": False,
                "auto_save_history": False,
                "additional_messages": [
                    {
                        "role": "user",
                        "content": prompt,
                        "content_type": "text"
                    }
                ]
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.ai_config["api_url"],
                    headers=headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # 提取AI回复内容
                    messages = result.get("data", {}).get("messages", [])
                    if messages:
                        content = messages[-1].get("content", "")
                        # 尝试解析JSON
                        try:
                            # 提取JSON部分（去除可能的markdown格式）
                            if "```json" in content:
                                json_start = content.find("```json") + 7
                                json_end = content.find("```", json_start)
                                json_content = content[json_start:json_end].strip()
                            elif content.strip().startswith('[') or content.strip().startswith('{'):
                                json_content = content.strip()
                            else:
                                print(f"❌ AI返回内容不是有效JSON格式")
                                return None
                            
                            return json.loads(json_content)
                        except json.JSONDecodeError as e:
                            print(f"❌ AI返回JSON解析失败: {e}")
                            print(f"原始内容: {content}")
                            return None
                    else:
                        print(f"❌ AI返回消息为空")
                        return None
                else:
                    print(f"❌ AI API调用失败: {response.status_code}")
                    print(f"错误信息: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ AI API调用异常: {e}")
            return None
    
    def process(self, json_file: str) -> Optional[Dict[str, Any]]:
        """
        完整的PF数据处理流程
        """
        print(f"🚀 开始PF蛋白质功能数据处理")
        
        # 1. 预处理：大JSON -> 小JSON
        small_json_file = self.preprocess_data(json_file)
        if not small_json_file:
            return None
        
        # 2. 读取小JSON数据
        try:
            with open(small_json_file, 'r', encoding='utf-8') as f:
                small_json_data = json.load(f)
            print(f"✅ 读取预处理数据成功")
        except Exception as e:
            print(f"❌ 读取预处理数据失败: {e}")
            return None
        
        # 3. 生成AI提示词
        prompt = self.get_ai_prompt(small_json_data)
        
        # 4. 调用AI进行转换
        import asyncio
        try:
            result = asyncio.run(self.call_ai_api(prompt))
            if result:
                print(f"✅ AI转换完成")
                return result
            else:
                print(f"❌ AI转换失败")
                return None
        except Exception as e:
            print(f"❌ AI转换异常: {e}")
            return None

# 测试函数
if __name__ == "__main__":
    # 测试配置
    test_config = {
        "api_url": "https://api.coze.cn/v3/chat",
        "access_token": "test_token",
        "bot_id": "test_bot"
    }
    
    skill = PFProcessorSkill(test_config)
    print(f"PF Skill初始化完成: {skill.skill_name}")