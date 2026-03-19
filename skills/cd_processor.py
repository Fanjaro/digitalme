#!/usr/bin/env python3
"""
CD肠道菌群数据处理Skill实现
处理肠道菌群检测大JSON数据，提取关键指标并转换为标准化直测数据模板
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

class CDProcessorSkill:
    """CD肠道菌群数据处理Skill"""
    
    def __init__(self, ai_config: Dict[str, Any]):
        self.skill_name = "CD肠道菌群数据处理"
        self.data_type = "CD"
        self.ai_config = ai_config
        self.trans_module = "trans_json/CD.py"
        
    def preprocess_data(self, json_file: str) -> Optional[str]:
        """
        调用trans_json模块进行数据预处理
        将大JSON转换为小JSON
        """
        print(f"🔄 开始预处理CD数据: {json_file}")
        
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
                extracted_file = os.path.join(file_dir, "CD_extracted.json")
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
        生成专门的CD肠道菌群AI转换提示词
        """
        prompt = f"""
你是一位专业的肠道微生物组学专家，请将以下肠道菌群检测数据转换为标准化的直测数据模板。

## 医学背景知识
肠道菌群通过16S rRNA基因测序技术分析，包含：
- **门水平**: 最高分类层级，反映菌群大类分布（如厚壁菌门、拟杆菌门）
- **属水平**: 中等分类层级，反映具体菌属丰度（如双歧杆菌属、乳杆菌属）
- **种水平**: 最细分类层级，反映特定菌种存在

## 临床意义
- **菌群多样性**：反映肠道生态系统稳定性，正常范围通常在4-7之间
- **有益菌比例**：影响消化、免疫、代谢功能，如双歧杆菌、乳杆菌
- **致病菌水平**：可能导致肠道疾病风险，需要重点关注
- **肠型分析**：个体化营养和治疗指导依据

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
        "name": "分类层级 | 菌群名称",
        "value": "丰度值%",
        "range": "参考范围",
        "abnormal": "异常状态（高/正常/低）",
        "unit": "%",
        "category": "分类层级（门水平/属水平/种水平）",
        "clinical_significance": "临床意义说明"
      }}
    ],
    "report_index": {{
      "diversity": "多样性指数",
      "enterotype": "肠型类型",
      "beneficial_ratio": "有益菌比例",
      "pathogenic_ratio": "致病菌比例"
    }}
  }}
]
```

## 转换规则
1. 保留所有菌群分类层级信息，格式为"门水平 | 厚壁菌门丰度"
2. 丰度值保持原始精度，统一添加%单位
3. 基于参考范围进行异常状态判断：高/正常/低
4. 重点标注临床意义较大的菌群
5. 提取多样性、肠型等核心指标
6. 添加每个菌群的临床意义说明

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
        完整的CD数据处理流程
        """
        print(f"🚀 开始CD肠道菌群数据处理")
        
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
    
    skill = CDProcessorSkill(test_config)
    print(f"CD Skill初始化完成: {skill.skill_name}")