#!/usr/bin/env python3
"""
增强版Prometheus数据收集器 - 专注于收集有数值波动的指标
解决数据波动过小的问题
"""

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
import random

# 忽略特定警告
warnings.filterwarnings("ignore", category=DeprecationWarning)

# === 配置项 ===
PROM_URL = "http://127.0.0.1:61675"
STEP = "15s"
OUTPUT_DIR = "data"
LOG_FILE = "enhanced_collection.log"
COLLECTION_HOURS = 4  # 减少采集时长以获得更密集的数据

# === 高波动性指标配置 ===
# 这些指标通常具有连续变化的数值，适合异常检测
HIGH_VARIATION_METRICS = {
    # JVM内存指标 - 通常有很好的波动性
    'jvm_memory_bytes_used': {
        'alias': 'jvm_memory_used_bytes',
        'unit': 'bytes',
        'expected_range': (1000000, 1000000000),  # 1MB到1GB
        'conversion': lambda x: x
    },
    
    'jvm_memory_bytes_committed': {
        'alias': 'jvm_memory_committed_bytes',
        'unit': 'bytes',
        'expected_range': (1000000, 2000000000),
        'conversion': lambda x: x
    },
    
    'jvm_memory_pool_bytes_used': {
        'alias': 'jvm_memory_pool_used_bytes',
        'unit': 'bytes',
        'expected_range': (100000, 1000000000),
        'conversion': lambda x: x
    },
    
    # 进程内存指标
    'process_resident_memory_bytes': {
        'alias': 'process_memory_bytes',
        'unit': 'bytes',
        'expected_range': (1000000, 500000000),
        'conversion': lambda x: x
    },
    
    'process_virtual_memory_bytes': {
        'alias': 'process_virtual_memory_bytes',
        'unit': 'bytes',
        'expected_range': (10000000, 2000000000),
        'conversion': lambda x: x
    },
    
    # CPU时间指标（累积值，会持续增长）
    'process_cpu_seconds_total': {
        'alias': 'process_cpu_total_seconds',
        'unit': 'seconds',
        'expected_range': (0, 100000),
        'conversion': lambda x: x
    },
    
    'process_cpu_user_seconds_total': {
        'alias': 'process_cpu_user_seconds',
        'unit': 'seconds',
        'expected_range': (0, 50000),
        'conversion': lambda x: x
    },
    
    'process_cpu_system_seconds_total': {
        'alias': 'process_cpu_system_seconds',
        'unit': 'seconds',
        'expected_range': (0, 50000),
        'conversion': lambda x: x
    },
    
    # Go运行时指标
    'go_memstats_alloc_bytes': {
        'alias': 'go_memory_allocated_bytes',
        'unit': 'bytes',
        'expected_range': (100000, 100000000),
        'conversion': lambda x: x
    },
    
    'go_memstats_heap_alloc_bytes': {
        'alias': 'go_heap_memory_bytes',
        'unit': 'bytes',
        'expected_range': (100000, 100000000),
        'conversion': lambda x: x
    },
    
    'go_memstats_heap_inuse_bytes': {
        'alias': 'go_heap_inuse_bytes',
        'unit': 'bytes',
        'expected_range': (100000, 100000000),
        'conversion': lambda x: x
    },
    
    'go_memstats_stack_inuse_bytes': {
        'alias': 'go_stack_memory_bytes',
        'unit': 'bytes',
        'expected_range': (10000, 10000000),
        'conversion': lambda x: x
    },
    
    # GC统计
    'go_memstats_gc_sys_bytes': {
        'alias': 'go_gc_system_bytes',
        'unit': 'bytes',
        'expected_range': (100000, 10000000),
        'conversion': lambda x: x
    },
    
    'go_gc_duration_seconds_sum': {
        'alias': 'go_gc_duration_total_seconds',
        'unit': 'seconds',
        'expected_range': (0, 1000),
        'conversion': lambda x: x
    },
    
    'go_gc_duration_seconds_count': {
        'alias': 'go_gc_count_total',
        'unit': 'count',
        'expected_range': (0, 100000),
        'conversion': lambda x: x
    },
    
    # JVM GC指标
    'jvm_gc_collection_seconds_sum': {
        'alias': 'jvm_gc_time_total_seconds',
        'unit': 'seconds',
        'expected_range': (0, 1000),
        'conversion': lambda x: x
    },
    
    'jvm_gc_collection_seconds_count': {
        'alias': 'jvm_gc_count_total',
        'unit': 'count',
        'expected_range': (0, 100000),
        'conversion': lambda x: x
    },
    
    # 线程相关
    'jvm_threads_current': {
        'alias': 'jvm_threads_active',
        'unit': 'count',
        'expected_range': (1, 1000),
        'conversion': lambda x: x
    },
    
    'jvm_threads_daemon': {
        'alias': 'jvm_threads_daemon_count',
        'unit': 'count',
        'expected_range': (1, 500),
        'conversion': lambda x: x
    },
    
    # 文件描述符
    'process_open_fds': {
        'alias': 'process_open_file_descriptors',
        'unit': 'count',
        'expected_range': (10, 10000),
        'conversion': lambda x: x
    },
    
    'process_max_fds': {
        'alias': 'process_max_file_descriptors',
        'unit': 'count',
        'expected_range': (1000, 100000),
        'conversion': lambda x: x
    },
    
    # 类加载指标
    'jvm_classes_loaded': {
        'alias': 'jvm_classes_currently_loaded',
        'unit': 'count',
        'expected_range': (1000, 50000),
        'conversion': lambda x: x
    },
    
    'jvm_classes_loaded_total': {
        'alias': 'jvm_classes_loaded_total',
        'unit': 'count',
        'expected_range': (1000, 100000),
        'conversion': lambda x: x
    },
    
    'jvm_classes_unloaded_total': {
        'alias': 'jvm_classes_unloaded_total',
        'unit': 'count',
        'expected_range': (0, 50000),
        'conversion': lambda x: x
    },
    
    # HTTP请求指标（如果存在）
    'http_requests_total': {
        'alias': 'http_requests_total_count',
        'unit': 'count',
        'expected_range': (0, 1000000),
        'conversion': lambda x: x
    },
    
    'http_request_duration_seconds_sum': {
        'alias': 'http_request_duration_total_seconds',
        'unit': 'seconds',
        'expected_range': (0, 10000),
        'conversion': lambda x: x
    },
    
    'http_request_duration_seconds_count': {
        'alias': 'http_request_count_total',
        'unit': 'count',
        'expected_range': (0, 1000000),
        'conversion': lambda x: x
    },
    
    # 定时器和计数器
    'prometheus_tsdb_head_samples_appended_total': {
        'alias': 'prometheus_samples_appended_total',
        'unit': 'count',
        'expected_range': (0, 10000000),
        'conversion': lambda x: x
    },
    
    'prometheus_http_requests_total': {
        'alias': 'prometheus_http_requests_total',
        'unit': 'count',
        'expected_range': (0, 1000000),
        'conversion': lambda x: x
    }
}

def test_prometheus_connection():
    """测试Prometheus连接"""
    try:
        print(f"🔌 测试连接: {PROM_URL}")
        response = requests.get(f"{PROM_URL}/api/v1/query?query=up", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                print(f"✅ Prometheus连接正常")
                return True
        print(f"❌ Prometheus连接失败: HTTP {response.status_code}")
        return False
    except Exception as e:
        print(f"❌ 无法连接到Prometheus: {str(e)}")
        return False

def get_available_metrics():
    """获取可用的指标列表"""
    try:
        response = requests.get(f"{PROM_URL}/api/v1/label/__name__/values", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return data['data']
    except Exception as e:
        print(f"❌ 获取指标列表失败: {e}")
    return []

def query_single_value(metric_name):
    """查询单个指标的当前值，用于快速验证数据范围"""
    try:
        response = requests.get(f"{PROM_URL}/api/v1/query", 
                              params={'query': metric_name}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success' and data['data']['result']:
                values = []
                for result in data['data']['result']:
                    if 'value' in result and len(result['value']) > 1:
                        values.append(float(result['value'][1]))
                return values
    except:
        pass
    return []

def query_prometheus_range(metric_query, start, end, step=STEP, max_retries=3):
    """查询Prometheus指标数据范围"""
    base_url = f"{PROM_URL}/api/v1/query_range"
    
    params = {
        "query": metric_query,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": step
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(base_url, params=params, timeout=60)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return data
            else:
                print(f"  HTTP错误 {response.status_code}")
        except Exception as e:
            print(f"  查询异常: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return None

def analyze_metric_variation(metric_name, metric_info, current_values):
    """分析指标的数值变化范围"""
    if not current_values:
        return False, "无当前值数据"
    
    min_val = min(current_values)
    max_val = max(current_values)
    range_val = max_val - min_val
    unique_count = len(set(current_values))
    
    expected_min, expected_max = metric_info.get('expected_range', (0, float('inf')))
    
    # 检查是否在预期范围内
    in_expected_range = expected_min <= min_val and max_val <= expected_max
    
    # 检查变化范围
    has_variation = unique_count > 1 and range_val > 0
    
    # 对于累积指标，即使当前值相同也可能随时间变化
    is_cumulative = 'total' in metric_name or 'count' in metric_name or 'seconds' in metric_name
    
    score = 0
    reasons = []
    
    if has_variation:
        score += 3
        reasons.append(f"有数值变化(范围:{range_val:.2f})")
    
    if in_expected_range:
        score += 2
        reasons.append("在预期范围内")
    
    if is_cumulative:
        score += 1
        reasons.append("累积类型指标")
    
    if unique_count > 2:
        score += 1
        reasons.append(f"多样性好({unique_count}个唯一值)")
    
    is_good = score >= 3
    reason = "; ".join(reasons) if reasons else "无明显特征"
    
    return is_good, f"评分:{score}, {reason}"

def create_synthetic_anomalies(df, fault_start, fault_end):
    """在故障期间创建合成异常，增加数据的波动性"""
    if df.empty or 'value' not in df.columns:
        return df
    
    # 在故障期间添加一些变化
    fault_mask = (df['timestamp'] >= fault_start) & (df['timestamp'] <= fault_end)
    fault_points = fault_mask.sum()
    
    if fault_points > 0:
        print(f"  为 {fault_points} 个故障期间数据点添加变化")
        
        # 获取正常期间的统计信息
        normal_values = df[~fault_mask]['value']
        if len(normal_values) > 0:
            normal_mean = normal_values.mean()
            normal_std = normal_values.std()
            
            # 为故障期间的数据添加变化
            fault_indices = df[fault_mask].index
            
            for idx in fault_indices:
                original_value = df.loc[idx, 'value']
                
                # 根据指标类型添加不同的变化
                metric_name = df.loc[idx, 'metric']
                
                if 'memory' in metric_name or 'bytes' in metric_name:
                    # 内存指标：增加10-30%的使용量
                    multiplier = random.uniform(1.1, 1.3)
                    df.loc[idx, 'value'] = original_value * multiplier
                elif 'cpu' in metric_name or 'seconds' in metric_name:
                    # CPU时间：稍微增加增长速度
                    increment = random.uniform(0.1, 0.5)
                    df.loc[idx, 'value'] = original_value + increment
                elif 'count' in metric_name or 'total' in metric_name:
                    # 计数器：增加一些额外的计数
                    increment = random.randint(1, 10)
                    df.loc[idx, 'value'] = original_value + increment
                else:
                    # 其他指标：添加一些噪声
                    noise = random.uniform(-0.1, 0.1) * original_value
                    df.loc[idx, 'value'] = max(0, original_value + noise)
    
    return df

def process_metric_data(data, metric_info, start_time, end_time):
    """处理指标数据"""
    if not data or not data.get('data') or not data['data'].get('result'):
        return pd.DataFrame()
    
    all_rows = []
    
    for result in data['data']['result']:
        labels = result.get('metric', {})
        values = result.get('values', [])
        
        for timestamp, value in values:
            try:
                dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
                float_value = float(value)
                
                # 应用转换函数
                converted_value = metric_info['conversion'](float_value)
                
                row = {
                    'timestamp': dt,
                    'value': converted_value,
                    'metric': metric_info['alias'],
                    'unit': metric_info['unit']
                }
                
                # 添加标签
                for k, v in labels.items():
                    row[k] = v
                
                # 确保有instance标识
                if 'instance' not in row:
                    row['instance'] = f"default_{hash(str(labels))}"
                
                all_rows.append(row)
                
            except (ValueError, TypeError):
                continue
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        return df
    
    return pd.DataFrame()

def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("🚀 增强版Prometheus数据收集器 - 专注高波动性指标")
    print("=" * 70)
    
    # 时间配置
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(hours=COLLECTION_HOURS)
    end_time = now
    
    print(f"📅 采集时间范围: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")
    print(f"⏱️  采集时长: {COLLECTION_HOURS} 小时")
    print(f"📊 目标指标数: {len(HIGH_VARIATION_METRICS)}")
    
    # 测试连接
    if not test_prometheus_connection():
        return
    
    # 获取可用指标
    available_metrics = get_available_metrics()
    if not available_metrics:
        print("❌ 无法获取指标列表")
        return
    
    print(f"🔍 发现 {len(available_metrics)} 个可用指标")
    
    # 智能选择高质量指标
    selected_metrics = {}
    
    print("\n📈 分析指标质量...")
    for metric_name, metric_info in HIGH_VARIATION_METRICS.items():
        if metric_name in available_metrics:
            print(f"🔍 检查指标: {metric_name}")
            
            # 获取当前值来评估数据质量
            current_values = query_single_value(metric_name)
            is_good, reason = analyze_metric_variation(metric_name, metric_info, current_values)
            
            if is_good:
                selected_metrics[metric_name] = metric_info
                print(f"  ✅ 选中: {reason}")
            else:
                print(f"  ❌ 跳过: {reason}")
        else:
            print(f"⚠️ 指标不存在: {metric_name}")
    
    if not selected_metrics:
        print("❌ 没有找到合适的高波动指标")
        return
    
    print(f"\n🎯 最终选择 {len(selected_metrics)} 个高质量指标")
    
    # 配置故障注入时间
    fault_duration = timedelta(minutes=20)
    fault_end = end_time - timedelta(minutes=10)
    fault_start = fault_end - fault_duration
    
    print(f"🚨 故障注入时段: {fault_start.strftime('%H:%M:%S')} - {fault_end.strftime('%H:%M:%S')}")
    
    # 收集数据
    collected_data = []
    successful_count = 0
    
    print("\n📥 开始数据收集...")
    
    for metric_name, metric_info in selected_metrics.items():
        print(f"\n📊 收集指标: {metric_info['alias']}")
        
        try:
            data = query_prometheus_range(metric_name, start_time, end_time)
            
            if data:
                df = process_metric_data(data, metric_info, start_time, end_time)
                
                if not df.empty:
                    # 检查数据质量
                    unique_values = df['value'].nunique()
                    value_range = df['value'].max() - df['value'].min()
                    
                    print(f"  📈 数据点: {len(df)}")
                    print(f"  🔢 唯一值: {unique_values}")
                    print(f"  📏 值域范围: {value_range:.6f}")
                    
                    if unique_values > 1 or value_range > 0:
                        # 添加故障标记
                        df['is_fault'] = 0
                        fault_mask = (df['timestamp'] >= fault_start) & (df['timestamp'] <= fault_end)
                        df.loc[fault_mask, 'is_fault'] = 1
                        
                        # 添加合成异常以增加波动性
                        df = create_synthetic_anomalies(df, fault_start, fault_end)
                        
                        # 创建series_id
                        df['series_id'] = df['instance'].astype(str) + '_' + df['metric']
                        
                        collected_data.append(df)
                        successful_count += 1
                        print(f"  ✅ 成功收集")
                    else:
                        print(f"  ❌ 数据无变化，跳过")
                else:
                    print(f"  ❌ 无有效数据")
            else:
                print(f"  ❌ 查询失败")
                
        except Exception as e:
            print(f"  ❌ 处理异常: {str(e)}")
    
    # 保存数据
    if collected_data:
        print(f"\n💾 保存数据集...")
        
        combined_df = pd.concat(collected_data, ignore_index=True)
        
        # 添加训练/测试分割
        train_split = 0.7
        total_time = end_time - start_time
        train_end = start_time + total_time * train_split
        combined_df['is_train'] = (combined_df['timestamp'] <= train_end).astype(int)
        
        # 保存文件
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enhanced_metrics_{timestamp_str}.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        combined_df.to_csv(filepath, index=False)
        
        # 统计信息
        print(f"📄 文件保存: {filename}")
        print(f"📊 总数据行: {len(combined_df)}")
        print(f"🎯 成功指标: {successful_count}")
        print(f"🔢 总唯一值: {combined_df['value'].nunique()}")
        print(f"📏 总值域: {combined_df['value'].max() - combined_df['value'].min():.6f}")
        
        # 按指标统计
        print(f"\n📋 按指标统计:")
        for metric in combined_df['metric'].unique():
            metric_df = combined_df[combined_df['metric'] == metric]
            unique_vals = metric_df['value'].nunique()
            val_range = metric_df['value'].max() - metric_df['value'].min()
            print(f"  {metric}: {len(metric_df)} 点, {unique_vals} 唯一值, 范围: {val_range:.6f}")
        
        print(f"\n🎉 数据收集完成！文件保存在: {filepath}")
    else:
        print("❌ 没有收集到任何数据")

if __name__ == "__main__":
    main() 