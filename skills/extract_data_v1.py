#!/usr/bin/env python3
"""
详细数据提取脚本
用于从API接口提取样本的详细检测结果数据
接口: http://10.1.20.128:30080/api/v1/samples/{sample_id}
输出: {sample_id}_data.json
"""

import json
import requests
import argparse
import sys
import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time
from datetime import datetime

class DetailedDataExtractor:
    def __init__(self, base_url: str = "http://10.1.20.128:30080/api/v1/samples/"):
        """
        初始化详细数据提取器
        
        Args:
            base_url: API基础URL
        """
        self.base_url = base_url
        self.session = requests.Session()
        # 设置超时和重试策略
        self.session.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
        self.session.headers.update({
            'User-Agent': 'DetailedDataExtractor/1.0',
            'Accept': 'application/json'
        })
    
    def fetch_detailed_data(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """
        获取单个样本的详细数据
        
        Args:
            sample_id: 样本ID
            
        Returns:
            详细数据字典，如果失败则返回None
        """
        try:
            url = f"{self.base_url}{sample_id}"
            print(f"📥 正在获取样本 {sample_id} 的详细数据...")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 验证数据格式
            if not isinstance(data, dict):
                print(f"⚠️  样本 {sample_id} 返回的数据格式不正确")
                return None
            
            print(f"✅ 样本 {sample_id} 详细数据获取成功")
            return data
            
        except requests.exceptions.Timeout:
            print(f"⏰ 样本 {sample_id} 请求超时")
            return None
        except requests.exceptions.ConnectionError:
            print(f"🔌 样本 {sample_id} 连接错误")
            return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"🔍 样本 {sample_id} 未找到")
            else:
                print(f"❌ 样本 {sample_id} HTTP错误: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 样本 {sample_id} 请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ 样本 {sample_id} JSON解析失败: {e}")
            return None
        except Exception as e:
            print(f"❌ 样本 {sample_id} 处理失败: {e}")
            return None
    
    def extract_v13_results(self, data: Dict[str, Any], sample_id: str) -> Dict[str, Any]:
        """
        提取v13_results数据，按照指定格式重新组织
        
        Args:
            data: 原始数据
            sample_id: 样本ID
            
        Returns:
            提取后的数据字典
        """
        result = {
            "sample_id": sample_id,
            "extraction_time": self._get_current_timestamp(),
            "source_url": f"{self.base_url}{sample_id}",
            "status": "success"
        }
        
        # 复制基本字段
        basic_fields = ['report_type', 'collected_at']
        for field in basic_fields:
            if field in data:
                result[field] = data[field]
        
        # 提取v13_results数据
        if 'data' in data and 'v13_results' in data['data']:
            v13_results = data['data']['v13_results']
            processed_data = self._process_v13_results(v13_results)
            result['data'] = processed_data
        else:
            result['status'] = "no_v13_data"
            result['available_keys'] = list(data.keys())
            if 'data' in data:
                result['data_keys'] = list(data['data'].keys()) if isinstance(data['data'], dict) else str(type(data['data']))
        
        return result
    
    def _process_v13_results(self, v13_results: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        处理v13_results数据，提取大类、小类、字段信息
        
        Args:
            v13_results: v13_results数据
            
        Returns:
            处理后的数据结构
        """
        processed = {}
        
        for category, category_data in v13_results.items():
            if not isinstance(category_data, dict):
                continue
            
            processed[category] = {}
            
            for subcategory, subcategory_data in category_data.items():
                if not isinstance(subcategory_data, dict):
                    continue
                
                # 提取核心字段
                subcategory_info = {}
                
                # 基础字段
                base_fields = ['pred_quantile', 'pred_raw']
                for field in base_fields:
                    if field in subcategory_data:
                        subcategory_info[field] = subcategory_data[field]
                
                # 数组字段
                array_fields = ['uniprot', 'value', 'lower', 'upper', 'importance_score', 'risk']
                for field in array_fields:
                    if field in subcategory_data:
                        subcategory_info[field] = subcategory_data[field]
                
                # 添加字段长度信息
                for field in array_fields:
                    if field in subcategory_info:
                        subcategory_info[f'{field}_count'] = len(subcategory_info[field])
                
                # 计算风险蛋白质数量
                if 'risk' in subcategory_info and 'uniprot' in subcategory_info:
                    risk_count = len(subcategory_info['risk'])
                    uniprot_count = len(subcategory_info['uniprot'])
                    subcategory_info['risk_ratio'] = f"{risk_count}/{uniprot_count}"
                
                # 添加子类别类型标识
                if subcategory.startswith('pa_organ'):
                    subcategory_info['type'] = 'organ_aging'
                elif subcategory.endswith('_system'):
                    subcategory_info['type'] = 'system_aging'
                else:
                    subcategory_info['type'] = 'aging_mechanism'
                
                processed[category][subcategory] = subcategory_info
        
        return processed
    
    def save_detailed_data(self, extracted_data: Dict[str, Any], output_dir: str = None) -> str:
        """
        保存详细数据到文件
        
        Args:
            extracted_data: 提取的数据
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        if not extracted_data or 'sample_id' not in extracted_data:
            return None
        
        sample_id = extracted_data['sample_id']
        
        # 准备输出目录
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = Path(".")
        
        # 生成文件名
        filename = f"{sample_id}_data.json"
        filepath = output_path / filename
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def process_single_sample(self, sample_id: str, output_dir: str = None) -> bool:
        """
        处理单个样本
        
        Args:
            sample_id: 样本ID
            output_dir: 输出目录
            
        Returns:
            处理是否成功
        """
        # 获取原始数据
        raw_data = self.fetch_detailed_data(sample_id)
        
        if not raw_data:
            return False
        
        # 提取v13_results数据
        extracted_data = self.extract_v13_results(raw_data, sample_id)
        
        # 保存到文件
        filepath = self.save_detailed_data(extracted_data, output_dir)
        
        if filepath:
            print(f"💾 详细数据已保存到: {filepath}")
            
            # 显示数据统计信息
            self._print_data_summary(extracted_data)
            
            return True
        else:
            print(f"❌ 保存文件失败: {sample_id}")
            return False
    
    def _print_data_summary(self, extracted_data: Dict[str, Any]) -> None:
        """
        打印数据摘要信息
        
        Args:
            extracted_data: 提取的数据
        """
        if 'data' not in extracted_data:
            print(f"⚠️  样本 {extracted_data.get('sample_id', '未知')} 无v13_results数据")
            return
        
        data = extracted_data['data']
        
        print(f"\n📊 数据摘要:")
        print(f"   样本ID: {extracted_data.get('sample_id', '未知')}")
        print(f"   报告类型: {extracted_data.get('report_type', '未知')}")
        print(f"   采集时间: {extracted_data.get('collected_at', '未知')}")
        
        # 统计各类别信息
        categories = list(data.keys())
        print(f"   数据类别: {len(categories)} 个")
        
        for category in categories:
            if category in data and isinstance(data[category], dict):
                subcategories = list(data[category].keys())
                print(f"   - {category}: {len(subcategories)} 个子类别")
                
                # 显示前几个子类别的类型
                for i, subcat in enumerate(subcategories[:3]):
                    if i < 3 and 'type' in data[category][subcat]:
                        subcat_type = data[category][subcat]['type']
                        print(f"     * {subcat}: {subcat_type}")
                
                if len(subcategories) > 3:
                    print(f"     ... 还有 {len(subcategories) - 3} 个子类别")
        
        # 统计蛋白质总数
        total_proteins = 0
        for category in categories:
            if isinstance(data[category], dict):
                for subcat, subcat_data in data[category].items():
                    if isinstance(subcat_data, dict) and 'uniprot' in subcat_data:
                        total_proteins += len(subcat_data['uniprot'])
        
        if total_proteins > 0:
            print(f"   总蛋白质数量: {total_proteins}")
    
    def process_multiple_samples(self, sample_ids: List[str], output_dir: str = None, 
                                max_workers: int = 5, delay: float = 0.1) -> Dict[str, bool]:
        """
        批量处理多个样本
        
        Args:
            sample_ids: 样本ID列表
            output_dir: 输出目录
            max_workers: 最大并发数
            delay: 请求延迟（秒）
            
        Returns:
            每个样本的处理结果字典
        """
        results = {}
        
        print(f"🚀 开始批量处理 {len(sample_ids)} 个样本的详细数据")
        print(f"📁 输出目录: {output_dir or '当前目录'}")
        print(f"⚙️  最大并发数: {max_workers}")
        print(f"⏱️  请求延迟: {delay}秒")
        print("=" * 60)
        
        # 创建输出目录
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 使用线程池并发处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_sample = {}
            for idx, sample_id in enumerate(sample_ids):
                # 添加延迟以避免请求过于频繁
                if idx > 0 and delay > 0:
                    time.sleep(delay)
                
                future = executor.submit(self._process_single_thread, sample_id, output_dir)
                future_to_sample[future] = sample_id
            
            # 处理完成的任务
            completed_count = 0
            for future in as_completed(future_to_sample):
                sample_id = future_to_sample[future]
                completed_count += 1
                
                try:
                    success = future.result()
                    results[sample_id] = success
                    
                    if success:
                        print(f"[{completed_count}/{len(sample_ids)}] ✅ {sample_id}: 成功")
                    else:
                        print(f"[{completed_count}/{len(sample_ids)}] ❌ {sample_id}: 失败")
                        
                except Exception as e:
                    print(f"[{completed_count}/{len(sample_ids)}] ❌ {sample_id}: 异常 - {e}")
                    results[sample_id] = False
        
        # 统计结果
        self._print_summary(results, "详细数据")
        
        return results
    
    def _process_single_thread(self, sample_id: str, output_dir: str = None) -> bool:
        """
        线程安全的单个样本处理函数
        
        Args:
            sample_id: 样本ID
            output_dir: 输出目录
            
        Returns:
            处理是否成功
        """
        raw_data = self.fetch_detailed_data(sample_id)
        
        if not raw_data:
            return False
        
        extracted_data = self.extract_v13_results(raw_data, sample_id)
        filepath = self.save_detailed_data(extracted_data, output_dir)
        
        return filepath is not None
    
    def _print_summary(self, results: Dict[str, bool], data_type: str = "详细数据") -> None:
        """
        打印处理结果摘要
        
        Args:
            results: 处理结果字典
            data_type: 数据类型描述
        """
        success_count = sum(results.values())
        total_count = len(results)
        
        print("\n" + "="*60)
        print(f"📊 {data_type}提取完成摘要:")
        print("="*60)
        print(f"📈 总样本数: {total_count}")
        print(f"✅ 成功处理: {success_count}")
        print(f"❌ 处理失败: {total_count - success_count}")
        
        if total_count > 0:
            success_rate = success_count / total_count * 100
            print(f"📊 成功率: {success_rate:.1f}%")
        
        print("="*60)
        
        # 显示失败样本（如果有）
        failed_samples = [sid for sid, success in results.items() if not success]
        if failed_samples:
            print(f"\n❌ 失败的样本ID ({len(failed_samples)}个):")
            for sample_id in failed_samples[:10]:  # 只显示前10个
                print(f"  - {sample_id}")
            
            if len(failed_samples) > 10:
                print(f"  ... 还有 {len(failed_samples) - 10} 个")
        
        # 显示输出文件说明
        print(f"\n📁 输出文件: 每个样本生成一个 {data_type.lower()} 文件")
        print(f"  格式: {{sample_id}}_{data_type.lower()}.json")
        print(f"  内容结构: 包含v13_results的详细解析，按大类、小类、字段组织")
    
    def process_from_file(self, file_path: str, output_dir: str = None, 
                         max_workers: int = 5, delay: float = 0.1) -> Dict[str, bool]:
        """
        从文件读取样本ID列表并处理
        
        Args:
            file_path: 包含样本ID的文件路径
            output_dir: 输出目录
            max_workers: 最大并发数
            delay: 请求延迟（秒）
            
        Returns:
            每个样本的处理结果字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 读取所有行，过滤空行和注释行
                sample_ids = []
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # 清理样本ID
                    sample_id = line.split()[0] if ' ' in line else line
                    sample_ids.append(sample_id)
            
            if not sample_ids:
                print("❌ 文件中没有有效的样本ID")
                return {}
            
            print(f"📄 从文件 {file_path} 读取到 {len(sample_ids)} 个样本ID")
            return self.process_multiple_samples(sample_ids, output_dir, max_workers, delay)
            
        except FileNotFoundError:
            print(f"❌ 文件不存在: {file_path}")
            return {}
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return {}
    
    def _get_current_timestamp(self) -> str:
        """
        获取当前时间戳
        
        Returns:
            格式化时间戳字符串
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """主函数：解析命令行参数并执行"""
    parser = argparse.ArgumentParser(
        description='详细数据提取器 - 从API接口提取样本的详细检测结果数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单个样本
  python extract_detailed_data.py SZKL2603161324001
  
  # 处理单个样本并指定输出目录
  python extract_detailed_data.py SZKL2603161324001 -d ./detailed_output
  
  # 处理多个样本
  python extract_detailed_data.py SZKL2603161324001 SZKL2603161324002 SZKL2603161324003
  
  # 从文件读取样本ID
  python extract_detailed_data.py -f sample_ids.txt
  
  # 批量处理，指定并发数和延迟
  python extract_detailed_data.py -f samples.txt -d ./detailed_results -w 8 --delay 0.2
  
  # 使用不同的API地址
  python extract_detailed_data.py -b "http://api.example.com/v1/samples/" SZKL2603161324001
        """
    )
    
    # 添加参数
    parser.add_argument('sample_ids', nargs='*', help='样本ID列表（可多个，空格分隔）')
    
    parser.add_argument('-s', '--single', help='单个样本ID')
    parser.add_argument('-m', '--multiple', help='逗号分隔的多个样本ID')
    parser.add_argument('-f', '--file', help='包含样本ID列表的文件路径')
    
    parser.add_argument('-b', '--base-url', default="http://10.1.20.128:30080/api/v1/samples/",
                       help='API基础URL（默认: %(default)s）')
    parser.add_argument('-d', '--output-dir', help='输出目录（默认为当前目录）')
    parser.add_argument('-w', '--workers', type=int, default=5,
                       help='并发工作线程数（默认: %(default)s）')
    parser.add_argument('--delay', type=float, default=0.1,
                       help='请求之间的延迟（秒，默认: 0.1）')
    parser.add_argument('--timeout', type=int, default=30,
                       help='请求超时时间（秒，默认: 30）')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细输出')
    parser.add_argument('--flat-structure', action='store_true', 
                       help='使用扁平结构输出（不进行深度处理）')
    
    args = parser.parse_args()
    
    # 如果没有提供任何参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    # 创建提取器实例
    extractor = DetailedDataExtractor(base_url=args.base_url)
    
    # 处理样本ID
    sample_ids_to_process = []
    
    # 根据参数确定要处理的样本ID
    if args.single:
        sample_ids_to_process = [args.single]
    elif args.multiple:
        sample_ids_to_process = [sid.strip() for sid in args.multiple.split(',')]
    elif args.file:
        # 从文件处理
        extractor.process_from_file(args.file, args.output_dir, args.workers, args.delay)
        return
    elif args.sample_ids:
        sample_ids_to_process = args.sample_ids
    else:
        print("❌ 请提供样本ID或使用相应参数")
        parser.print_help()
        sys.exit(1)
    
    # 处理样本
    if len(sample_ids_to_process) == 1:
        # 单样本模式
        sample_id = sample_ids_to_process[0]
        success = extractor.process_single_sample(sample_id, args.output_dir)
        
        if not success:
            print(f"❌ 样本 {sample_id} 处理失败")
            sys.exit(1)
    else:
        # 多样本模式
        extractor.process_multiple_samples(sample_ids_to_process, args.output_dir, args.workers, args.delay)


if __name__ == "__main__":
    main()
