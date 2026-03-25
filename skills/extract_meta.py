#!/usr/bin/env python3
"""
元数据提取脚本
用于从API接口提取用户元数据信息
接口: http://180.184.28.174:30080/api/v1/users/by-sample/{sample_id}
输出: {sample_id}_meta.json
"""

import json
import requests
import argparse
import sys
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import time

class MetaExtractor:
    def __init__(self, base_url: str = "http://180.184.28.174:30080/api/v1/users/by-sample/"):
        """
        初始化元数据提取器
        
        Args:
            base_url: API基础URL
        """
        self.base_url = base_url
        self.session = requests.Session()
        # 设置超时和重试策略
        self.session.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
        self.session.headers.update({
            'User-Agent': 'MetaExtractor/1.0',
            'Accept': 'application/json'
        })
    
    def fetch_metadata(self, sample_id: str) -> Dict[str, Any]:
        """
        获取单个样本的元数据
        
        Args:
            sample_id: 样本ID
            
        Returns:
            元数据字典，如果失败则返回None
        """
        try:
            url = f"{self.base_url}{sample_id}"
            print(f"📥 正在获取样本 {sample_id} 的元数据...")
            
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            data = response.json()
            
            # 验证数据格式
            if not isinstance(data, dict):
                print(f"⚠️  样本 {sample_id} 返回的数据格式不正确")
                return None
            
            # 提取数据部分
            result = data.get('result', {})
            response_data = result.get('Response', {})
            user_data = response_data.get('Data', {})
            
            if not user_data:
                print(f"⚠️  样本 {sample_id} 没有用户数据")
                return None
            
            print(f"✅ 样本 {sample_id} 元数据获取成功")
            
            # 【新增】: 检查并记录samples字段信息
            samples_data = user_data.get('samples', [])
            if samples_data:
                print(f"📊 发现用户关联的 {len(samples_data)} 个样品信息")
                # 找到当前样本在samples列表中的位置
                for i, sample_info in enumerate(samples_data):
                    if sample_info.get('sample_id') == sample_id:
                        print(f"  当前样本在列表中的位置: 第{i+1}个")
                        # 记录当前样本的报告状态
                        report_status = sample_info.get('report_status', '未知')
                        report_type = sample_info.get('report_type', '未知')
                        print(f"  当前样本报告状态: {report_status}, 报告类型: {report_type}")
                        break
            
            return user_data
            
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
    
    def process_user_data(self, user_data: Dict[str, Any], sample_id: str) -> Dict[str, Any]:
        """
        处理用户数据，提取关键信息
        
        Args:
            user_data: 原始用户数据
            sample_id: 样本ID
            
        Returns:
            处理后的元数据
        """
        meta = {
            "sample_id": sample_id,
            "extraction_time": self._get_current_timestamp(),
            "source_url": f"{self.base_url}{sample_id}",
            "status": "success"
        }
        
        # 直接添加所有用户数据
        meta.update(user_data)
        
        # 添加解析后的生日信息
        if '_birthday' in user_data:
            birthday = user_data['_birthday']
            # 尝试从时间戳中提取日期部分
            if 'T' in birthday:
                meta['birthday_date'] = birthday.split('T')[0]
        
        # 添加解析后的时间信息
        timestamp_fields = ['_UpdatedAt', '_UserCreatedAt', '_sampleCollectedAt']
        for field in timestamp_fields:
            if field in user_data:
                timestamp = user_data[field]
                if 'T' in timestamp:
                    meta[f'{field}_date'] = timestamp.split('T')[0]
        
        # 【新增】: 处理样品信息中的时间戳字段
        if 'samples' in user_data and isinstance(user_data['samples'], list):
            for i, sample_info in enumerate(user_data['samples']):
                collected_at = sample_info.get('collected_at')
                if collected_at and isinstance(collected_at, int) and collected_at > 0:
                    # 将毫秒时间戳转换为日期字符串
                    try:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(collected_at / 1000)
                        meta['samples'][i]['collected_at_date'] = dt.strftime('%Y-%m-%d')
                        meta['samples'][i]['collected_at_datetime'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, OSError):
                        pass
        
        return meta
    
    def save_metadata(self, metadata: Dict[str, Any], output_dir: str = None) -> str:
        """
        保存元数据到文件
        
        Args:
            metadata: 元数据
            output_dir: 输出目录
            
        Returns:
            保存的文件路径
        """
        if not metadata or 'sample_id' not in metadata:
            return None
        
        sample_id = metadata['sample_id']
        
        # 准备输出目录
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
        else:
            output_path = Path(".")
        
        # 生成文件名
        filename = f"{sample_id}_meta.json"
        filepath = output_path / filename
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
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
        # 获取用户数据
        user_data = self.fetch_metadata(sample_id)
        
        if not user_data:
            return False
        
        # 处理用户数据
        metadata = self.process_user_data(user_data, sample_id)
        
        # 保存到文件
        filepath = self.save_metadata(metadata, output_dir)
        
        if filepath:
            print(f"💾 元数据已保存到: {filepath}")
            print(f"   文件大小: {os.path.getsize(filepath) / 1024:.2f} KB")
            
            # 显示关键信息
            self._print_summary_info(metadata)
            
            return True
        else:
            print(f"❌ 保存文件失败: {sample_id}")
            return False
    
    def _print_summary_info(self, metadata: Dict[str, Any]) -> None:
        """
        打印元数据摘要信息
        
        Args:
            metadata: 元数据字典
        """
        print("\n📋 元数据摘要:")
        print(f"   样本ID: {metadata.get('sample_id', '未知')}")
        print(f"   姓名: {metadata.get('name', '未知')}")
        
        # 性别映射
        sex = metadata.get('sex')
        if sex == 1:
            print("   性别: 男")
        elif sex == 0:
            print("   性别: 女")
        else:
            print(f"   性别: {sex}")
        
        # 生日信息
        birthday = metadata.get('_birthday', metadata.get('birthday_date', '未知'))
        if birthday and birthday != '未知':
            print(f"   生日: {birthday[:10] if len(birthday) > 10 else birthday}")
        
        # 身高体重
        height = metadata.get('height')
        weight = metadata.get('weight')
        bmi = metadata.get('bmi')
        
        if height:
            print(f"   身高: {height} cm")
        if weight:
            print(f"   体重: {weight} kg")
        if bmi:
            print(f"   BMI: {bmi:.2f}")
        
        # 联系方式
        mobile = metadata.get('mobile')
        if mobile:
            print(f"   手机: {mobile}")
        
        # 采集时间
        collected_at = metadata.get('_sampleCollectedAt_date', metadata.get('_sampleCollectedAt', '未知'))
        if collected_at and collected_at != '未知':
            print(f"   采集时间: {collected_at[:10] if len(collected_at) > 10 else collected_at}")
        
        # 【新增】: 显示样品信息汇总
        if 'samples' in metadata and isinstance(metadata['samples'], list):
            samples = metadata['samples']
            print(f"   关联样品总数: {len(samples)}")
            
            # 找到当前样本的信息
            for i, sample in enumerate(samples):
                if sample.get('sample_id') == metadata.get('sample_id'):
                    report_type = sample.get('report_type', '未知')
                    report_status = sample.get('report_status', '未知')
                    report_path = sample.get('report_path', '无')
                    collected_at = sample.get('collected_at', 0)
                    
                    print(f"   当前样品信息:")
                    print(f"     - 报告类型: {report_type}")
                    print(f"     - 报告状态: {report_status}")
                    if report_path and report_path != '无':
                        print(f"     - 报告路径: {report_path}")
                    
                    # 如果有收集时间戳，显示格式化时间
                    if collected_at and isinstance(collected_at, int) and collected_at > 0:
                        try:
                            from datetime import datetime
                            dt = datetime.fromtimestamp(collected_at / 1000)
                            print(f"     - 收集时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        except (ValueError, OSError):
                            pass
                    
                    # 显示其他样品简要信息
                    if len(samples) > 1:
                        print(f"   其他样品 ({len(samples)-1}个):")
                        other_samples = [s for s in samples if s.get('sample_id') != metadata.get('sample_id')]
                        for other in other_samples[:3]:  # 最多显示3个
                            other_id = other.get('sample_id', '未知')
                            other_status = other.get('report_status', '未知')
                            print(f"     - {other_id}: {other_status}")
                        
                        if len(other_samples) > 3:
                            print(f"     ... 还有 {len(other_samples)-3} 个")
                    break
        else:
            print(f"   关联样品信息: 无")
    
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
        
        print(f"🚀 开始批量处理 {len(sample_ids)} 个样本的元数据")
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
        self._print_summary(results, "元数据")
        
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
        user_data = self.fetch_metadata(sample_id)
        
        if not user_data:
            return False
        
        metadata = self.process_user_data(user_data, sample_id)
        filepath = self.save_metadata(metadata, output_dir)
        
        return filepath is not None
    
    def _print_summary(self, results: Dict[str, bool], data_type: str = "元数据") -> None:
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
        print(f"  【新增】: 输出文件现在包含用户的全部样品信息(samples字段)")
    
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
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    """主函数：解析命令行参数并执行"""
    parser = argparse.ArgumentParser(
        description='元数据提取器 - 从API接口提取用户元数据信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理单个样本
  python extract_meta.py SZKL2603161324001
  
  # 处理单个样本并指定输出目录
  python extract_meta.py SZKL2603161324001 -d ./meta_output
  
  # 处理多个样本
  python extract_meta.py SZKL2603161324001 SZKL2603161324002 SZKL2603161324003
  
  # 从文件读取样本ID
  python extract_meta.py -f sample_ids.txt
  
  # 批量处理，指定并发数和延迟
  python extract_meta.py -f samples.txt -d ./results -w 8 --delay 0.2
  
  # 使用不同的API地址
  python extract_meta.py -b "http://api.example.com/v1/users/by-sample/" SZKL2603161324001
        """
    )
    
    # 添加参数
    parser.add_argument('sample_ids', nargs='*', help='样本ID列表（可多个，空格分隔）')
    
    parser.add_argument('-s', '--single', help='单个样本ID')
    parser.add_argument('-m', '--multiple', help='逗号分隔的多个样本ID')
    parser.add_argument('-f', '--file', help='包含样本ID列表的文件路径')
    
    parser.add_argument('-b', '--base-url', default="http://180.184.28.174:30080/api/v1/users/by-sample/",
                       help='API基础URL（默认: %(default)s）')
    parser.add_argument('-d', '--output-dir', help='输出目录（默认为当前目录）')
    parser.add_argument('-w', '--workers', type=int, default=5,
                       help='并发工作线程数（默认: %(default)s）')
    parser.add_argument('--delay', type=float, default=0.1,
                       help='请求之间的延迟（秒，默认: 0.1）')
    parser.add_argument('--timeout', type=int, default=20,
                       help='请求超时时间（秒，默认: 20）')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细输出')
    
    args = parser.parse_args()
    
    # 如果没有提供任何参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    
    # 创建提取器实例
    extractor = MetaExtractor(base_url=args.base_url)
    
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