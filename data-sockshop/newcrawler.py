import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
import os
import warnings
import time
import re
import logging
import traceback
import math

# 忽略特定警告
warnings.filterwarnings("ignore", category=DeprecationWarning)

# === 配置项 ===
PROM_URL = "http://127.0.0.1:51384"  # Prometheus端口
STEP = "15s"  # 数据采集步长
OUTPUT_DIR = "data"  # 输出目录
LOG_FILE = "data_collection.log"  # 日志文件路径

# === 核心监控指标 ===
METRICS = {
    # 使用container_cpu_usage_seconds_total原始数据
    'container_cpu_usage_seconds_total': {
        'alias': 'cpu_usage_seconds',
        'unit': 'seconds',
        'normal_max': None,
        'conversion': lambda x: x
    },
    
    # 内存使用（字节转换为MB）
    'container_memory_usage_bytes': {
        'alias': 'mem_usage',
        'unit': 'MB',
        'normal_max': None,
        'conversion': lambda x: x / (1024 * 1024)
    },
    
    # 运行的进程数
    'processes_total': {
        'alias': 'process_count',
        'unit': 'count',
        'normal_max': None,
        'conversion': lambda x: x
    }
}

# === 辅助函数 ===
def test_prometheus_connection():
    """测试Prometheus连接"""
    try:
        print(f"🔌 测试连接: {PROM_URL}")
        start_time = time.time()
        response = requests.get(f"{PROM_URL}/api/v1/query?query=up", timeout=10)
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                print(f"✅ Prometheus连接正常 (响应时间: {elapsed:.2f}s)")
                # 添加健康检查
                result = data.get('data', {}).get('result', [])
                if result:
                    print(f"  检测到 {len(result)} 个活跃服务")
                else:
                    print("⚠️ 无活跃服务报告 - 配置可能存在问题")
                return True
            
        print(f"❌ Prometheus连接失败: HTTP {response.status_code}")
        # 尝试获取版本信息作为备选
        try:
            version_res = requests.get(f"{PROM_URL}/api/v1/status/buildinfo", timeout=5)
            if version_res.status_code == 200:
                version = version_res.json().get('data', {}).get('version', '未知')
                print(f"  检测到Prometheus版本: {version}")
        except:
            pass
        return False
    except Exception as e:
        print(f"❌ 无法连接到Prometheus: {str(e)}")
        return False

def query_prometheus(metric_query, start, end, step=STEP, max_retries=5):
    """查询Prometheus指标数据（带重试机制）- 修复版本"""
    base_url = f"{PROM_URL}/api/v1/query_range"
    
    # 如果查询包含CPU指标，切换到原始指标查询
    if "cpu_usage_seconds_total" in metric_query:
        # 使用原始数据查询而不是聚合查询
        metric_query = "container_cpu_usage_seconds_total"
        print("🔧 已修改CPU查询为原始指标: container_cpu_usage_seconds_total")
    
    params = {
        "query": metric_query,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": step
    }
    
    print(f"  查询语句: {metric_query}")
    duration = (end - start).total_seconds() / 3600
    print(f"  时间范围: {start.strftime('%Y-%m-%d %H:%M:%S')} → {end.strftime('%Y-%m-%d %H:%M:%S')} ({duration:.2f}小时)")
    print(f"  请求步长: {step}")
    
    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params=params, timeout=60)
            
            # 检查HTTP状态码
            if response.status_code != 200:
                error_info = f"HTTP {response.status_code} 错误"
                try:
                    error_data = response.json()
                    error_info += f": {error_data.get('errorType', '未知类型')} - {error_data.get('error', '无错误详情')}"
                except:
                    error_info += f": {response.text[:200]}"
                print(f"⚠️ 查询失败: {error_info}")
                return None
                
            data = response.json()
            
            # 检查Prometheus返回的状态
            if data.get('status') != 'success':
                error_msg = data.get('error', '未知错误')
                print(f"⚠️ Prometheus返回错误: {error_msg}")
                return None
                
            # 检查实际返回的数据点数量
            total_points = sum(len(series.get('values', [])) for series in data['data'].get('result', []))
            print(f"  返回数据点数量: {total_points}")
            
            # 检查时间范围覆盖
            if data['data'].get('result'):
                values = data['data']['result'][0].get('values', [])
                if values:
                    first_ts = datetime.fromtimestamp(float(values[0][0]), tz=timezone.utc)
                    last_ts = datetime.fromtimestamp(float(values[-1][0]), tz=timezone.utc)
                    actual_duration = (last_ts - first_ts).total_seconds() / 3600
                    coverage = actual_duration / duration * 100 if duration > 0 else 100
                    print(f"  实际时间覆盖: {actual_duration:.2f}h/{duration:.2f}h ({coverage:.1f}%)")
            
            return data
            
        except (requests.RequestException, requests.ConnectionError) as e:
            wait_time = 2 ** attempt
            print(f"⚠️ 网络错误，{wait_time}秒后重试: {str(e)}")
            time.sleep(wait_time)
        except Exception as e:
            print(f"⚠️ 查询异常: {str(e)}")
            time.sleep(3)
    
    print(f"❌ 查询失败，超过最大重试次数({max_retries})")
    return None

def normalize_label_name(name):
    """规范化标签名称"""
    try:
        # 移除特殊字符
        name = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
        # 确保不以数字开头
        if name[0].isdigit():
            name = f'label_{name}'
        return name.lower()
    except Exception as e:
        print(f"  标签名称规范化错误: {str(e)}")
        return f"error_{hash(str(e))}"

def parse_metric_data(data, metric_info, req_start, req_end):
    """解析Prometheus响应数据"""
    if not data or not data.get('data') or not data['data'].get('result'):
        print(f"⚠️ 无有效数据返回: {metric_info['alias']}")
        return pd.DataFrame(), req_start, req_end
    
    try:
        results = data['data']['result']
        total_points = sum(len(series.get('values', [])) for series in results)
        print(f"✅ 获取到 {len(results)} 个时间序列，共 {total_points} 个数据点")
    except Exception as e:
        print(f"❌ 解析结果失败: {str(e)}")
        return pd.DataFrame(), req_start, req_end
    
    all_dfs = []
    min_timestamp = req_end
    max_timestamp = req_start
    
    # 记录每个序列的数据点数和时间范围
    series_stats = []
    
    for result in results:
        labels = result.get('metric', {})
        values = result.get('values', [])
        
        # 追踪实际时间范围
        if values:
            try:
                series_min = datetime.fromtimestamp(float(values[0][0]), tz=timezone.utc)
                series_max = datetime.fromtimestamp(float(values[-1][0]), tz=timezone.utc)
                min_timestamp = min(min_timestamp, series_min)
                max_timestamp = max(max_timestamp, series_max)
                
                # 计算该系列的时间覆盖率和点间隔
                series_duration = (series_max - series_min).total_seconds()
                avg_interval = series_duration / (len(values) - 1) if len(values) > 1 else 0
                
                # 存储系列统计信息
                series_stats.append({
                    'series': list(labels.values())[0] if labels else "unknown",
                    'points': len(values),
                    'duration_min': series_duration / 60,
                    'avg_interval': avg_interval
                })
                
                # 打印每个系列的基本信息
                label_str = ", ".join([f"{k}={v}" for k, v in labels.items()])
                print(f"  标签: {label_str} | 数据点: {len(values)}个 | 持续时间: {series_duration/60:.1f}分钟 | 平均间隔: {avg_interval:.1f}秒")
                
            except Exception as e:
                print(f"  时间戳转换错误: {str(e)}")
        
        points = []
        for point in values:
            try:
                timestamp, value = point
                dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
                float_value = metric_info['conversion'](float(value))
                
                row = {'timestamp': dt, 'value': float_value}
                for label_name, label_value in labels.items():
                    row[normalize_label_name(label_name)] = label_value
                
                points.append(row)
            except (ValueError, TypeError) as e:
                print(f"  数据点解析错误: {str(e)}")
                continue
        
        if points:
            try:
                ts_df = pd.DataFrame(points)
                all_dfs.append(ts_df)
            except Exception as e:
                print(f"  创建DataFrame失败: {str(e)}")

    if not all_dfs:
        return pd.DataFrame(), min_timestamp, max_timestamp
    
    try:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        combined_df['metric'] = metric_info['alias']
        combined_df['unit'] = metric_info['unit']
    except Exception as e:
        print(f"  合并数据失败: {str(e)}")
        return pd.DataFrame(), min_timestamp, max_timestamp
    
    # 打印详细的系列统计信息
    if series_stats:
        total_points = sum(s['points'] for s in series_stats)
        avg_interval = sum(s['avg_interval'] for s in series_stats) / len(series_stats)
        min_duration = min(s['duration_min'] for s in series_stats)
        max_duration = max(s['duration_min'] for s in series_stats)
        
        print(f"  时间序列统计:")
        print(f"    总数据点: {total_points}")
        print(f"    最小持续时间: {min_duration:.1f}分钟 | 最大持续时间: {max_duration:.1f}分钟")
        print(f"    平均间隔: {avg_interval:.1f}秒")
    
    # 返回实际时间范围
    return combined_df, min_timestamp, max_timestamp

def mark_fault_period(df, metric_info, fault_start, fault_end):
    """标记故障注入期间的数据点"""
    if df.empty:
        return df
    
    # 添加故障标记
    df['is_fault'] = 0
    
    # 确保有时间序列标识
    if 'instance' not in df.columns:
        df['instance'] = 'default'
    
    # 创建实例+指标的复合键
    if 'instance' in df.columns and 'metric' in df.columns:
        df['series_id'] = df['instance'].astype(str) + '_' + df['metric']
    else:
        print("⚠️ 无法创建series_id，缺少必要的列")
        return df
    
    # 标记故障期间的数据点
    fault_mask = (df['timestamp'] >= fault_start) & (df['timestamp'] <= fault_end)
    df.loc[fault_mask, 'is_fault'] = 1
    
    return df

def save_combined_data(all_data, fault_start, fault_end):
    """保存合并的数据集"""
    if not all_data:
        print("⚠️ 无有效数据可保存")
        return None, {}
    
    combined_df = pd.concat(all_data, ignore_index=True)
    
    if combined_df.empty:
        print("⚠️ 空数据集无法保存")
        return None, {}
    
    # 确保所有时间序列都有series_id
    if 'series_id' not in combined_df.columns:
        if 'instance' in combined_df.columns and 'metric' in combined_df.columns:
            combined_df['series_id'] = combined_df['instance'].astype(str) + '_' + combined_df['metric']
        else:
            print("⚠️ 无法创建series_id")
            return None, {}
    
    # 科学划分训练集和测试集
    earliest = combined_df['timestamp'].min()
    latest = combined_df['timestamp'].max()
    train_end = earliest + (latest - earliest) * 0.75
    combined_df['is_train'] = (combined_df['timestamp'] <= train_end).astype(int)
    
    # 创建文件名
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"prometheus_metrics_{timestamp_str}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # 保存并添加时间范围信息
    time_range_note = f"实际数据范围: {earliest.strftime('%Y-%m-%d %H:%M:%S')} 至 {latest.strftime('%Y-%m-%d %H:%M:%S')}\n"
    time_range_note += f"请求时间范围: {fault_start.strftime('%Y-%m-%d %H:%M:%S')} 至 {fault_end.strftime('%Y-%m-%d %H:%M:%S')}\n"
    time_range_note += f"故障注入: {fault_start.strftime('%H:%M:%S')} - {fault_end.strftime('%H:%M:%S')}"
    
    with open(filepath.replace('.csv', '.note.txt'), 'w') as f:
        f.write(time_range_note)
    
    combined_df.to_csv(filepath, index=False)
    print(f"💾 已保存数据集: {filepath} ({len(combined_df)}行)")
    
    # 详细的统计数据
    stats = {}
    total_samples = 0
    min_samples = float('inf')
    max_samples = 0
    
    print("\n📊 详细指标统计:")
    for metric, info in METRICS.items():
        alias = info['alias']
        metric_df = combined_df[combined_df['metric'] == alias]
        if not metric_df.empty:
            # 分组统计每个系列
            series_stats = metric_df.groupby('series_id').agg(
                points=('value', 'count'),
                min_value=('value', 'min'),
                max_value=('value', 'max'),
                start_time=('timestamp', 'min'),
                end_time=('timestamp', 'max')
            )
            
            series_stats['duration_h'] = (series_stats['end_time'] - series_stats['start_time']).dt.total_seconds() / 3600
            series_stats['avg_interval'] = series_stats['duration_h'] * 3600 / (series_stats['points'] - 1)
            
            min_duration = series_stats['duration_h'].min()
            max_duration = series_stats['duration_h'].max()
            avg_interval = series_stats['avg_interval'].mean()
            
            stats[alias] = {
                'samples': len(metric_df),
                'series': len(series_stats),
                'min_value': metric_df['value'].min(),
                'max_value': metric_df['value'].max(),
                'min_duration': min_duration,
                'max_duration': max_duration,
                'avg_interval': avg_interval
            }
            
            total_samples += len(metric_df)
            min_samples = min(min_samples, len(metric_df))
            max_samples = max(max_samples, len(metric_df))
            
            print(f"  {alias}:")
            print(f"    样本数: {len(metric_df)} | 系列数: {len(series_stats)}")
            print(f"    值范围: {metric_df['value'].min():.2f} - {metric_df['value'].max():.2f}")
            print(f"    时间覆盖: {min_duration:.2f}h - {max_duration:.2f}h")
            print(f"    平均采样间隔: {avg_interval:.1f}秒")
    
    # 整体统计信息
    overall_coverage = earliest.strftime('%H:%M:%S') + " - " + latest.strftime('%H:%M:%S')
    print(f"\n📊 整体统计:")
    print(f"  总样本数: {total_samples}")
    print(f"  最小样本指标: {min_samples} | 最大样本指标: {max_samples}")
    print(f"  时间范围覆盖: {overall_coverage}")
    
    return filepath, stats

def main():
    """主函数：执行数据采集流程"""
    try:
        # 计算时间范围：当前时间前8小时到现在
        now = datetime.now(timezone.utc)
        print(f"\n🕒 当前时间 (UTC): {now} ({now.timestamp()})")
        
        # 提前开始时间（增加5分钟缓冲）
        start_time = now - timedelta(hours=8, minutes=5)
        print(f"🕒 开始时间 (UTC): {start_time} ({start_time.timestamp()})")
        
        # 结束时间为当前时间
        end_time = now
        
        print("\n" + "=" * 70)
        print("Prometheus 数据采集工具 (最终优化版)")
        print("=" * 70)
        print(f"精确时间范围: {start_time.strftime('%Y-%m-%d %H:%M:%S')} 至 {end_time.strftime('%Y-%m-%d %H:%M:%S')} (UTC)")
        duration = (end_time - start_time).total_seconds() / 3600
        print(f"总时长: {duration:.2f} 小时")
        print(f"采集步长: {STEP}")
        print(f"监控指标数: {len(METRICS)}")
        print(f"Prometheus URL: {PROM_URL}")
        print(f"输出目录: {OUTPUT_DIR}")
        
        # 测试连接
        if not test_prometheus_connection():
            print("请检查Prometheus URL和连接设置")
            return
        
        # 配置故障注入时间段
        fault_duration = timedelta(minutes=15)
        fault_end = end_time - timedelta(minutes=5)
        fault_start = fault_end - fault_duration
        print(f"故障注入时段: {fault_start.strftime('%H:%M:%S')} - {fault_end.strftime('%H:%M:%S')}")
        
        collected_data = []
        print("\n开始采集指标数据...\n")
        
        for promql_query, metric_info in METRICS.items():
            print(f"\n🔍 正在采集: {metric_info['alias']}")
            print(f"  查询指标: {metric_info['alias']}")
            
            # 使用原始查询
            data = query_prometheus(promql_query, start_time, end_time)
            
            # 解析数据
            if data:
                df, min_ts, max_ts = parse_metric_data(data, metric_info, start_time, end_time)
                
                # 检查数据范围
                if not df.empty:
                    # 添加故障标记
                    df = mark_fault_period(df, metric_info, fault_start, fault_end)
                    collected_data.append(df)
                    print(f"✅ {metric_info['alias']} 采集完成: {len(df)} 行数据\n")
                else:
                    print(f"❌ {metric_info['alias']} 无有效数据\n")
            else:
                print(f"❌ {metric_info['alias']} 查询失败，跳过此指标\n")
        
        # 保存数据
        if collected_data:
            filepath, stats = save_combined_data(collected_data, fault_start, fault_end)
            print(f"\n💾 数据集已保存到: {filepath}")
        else:
            print("⚠️ 没有采集到任何数据")
        
        print("\n" + "=" * 50)
        print("✅ 数据采集完成!")
        print("=" * 50)
    
    except Exception as e:
        print(f"\n❌ 严重错误: {str(e)}")
        print(traceback.format_exc())
        
        # 调试建议
        print("\n💡 调试建议:")
        print(f"1. 手动测试查询:")
        print(f"   curl -G '{PROM_URL}/api/v1/query_range'")
        print(f"     --data-urlencode 'query=container_cpu_usage_seconds_total'")
        print(f"     --data-urlencode 'start={start_time.timestamp()}'")
        print(f"     --data-urlencode 'end={end_time.timestamp()}'")
        print(f"     --data-urlencode 'step=15s'")
        print(f"2. 检查Prometheus日志中的错误信息")

if __name__ == "__main__":
    # 确保输出目录存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        filename=os.path.join(OUTPUT_DIR, LOG_FILE),
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 开始采集
    main()