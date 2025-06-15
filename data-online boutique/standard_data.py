import pandas as pd
import numpy as np
import uuid
from datetime import datetime

# 配置参数
INPUT_FILE = "cleaned_prometheus_data.csv"  # 上一个脚本的输出文件
OUTPUT_FILE = "standard_dataset.csv"

def generate_kpi_id(series_id, metric, instance):
    """
    生成稳定的KPI ID (UUID格式)
    使用关键字段的哈希值确保相同的时间序列获得相同的ID
    """
    unique_string = f"{series_id}_{metric}_{instance}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

def main():
    print(f"📊 读取清洗后的数据集: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    print(f"原始数据: {len(df)}行 × {len(df.columns)}列")
    
    # 1. 时间戳转换 (转换为Unix时间戳)
    print("⏱ 转换时间戳格式...")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['timestamp'] = df['timestamp'].astype('int64') // 10**9  # 转换为Unix时间戳(秒)
    
    # 2. 创建论文标准列
    print("📝 创建论文标准列结构...")
    
    # 2.1 异常标签 (label)
    df['label'] = df['is_fault'].astype(float)
    
    # 2.2 KPI ID (基于关键字段生成稳定UUID)
    print("🔑 生成KPI ID...")
    df['KPI ID'] = df.apply(
        lambda x: generate_kpi_id(x['series_id'], x['metric'], x['instance']), 
        axis=1
    )
    
    # 2.3 缺失值标记 (全部设为0，表示无缺失)
    df['missing'] = 0
    
    # 2.4 数据集类型 (is_test)
    df['is_test'] = df['dataset'].apply(lambda x: 1 if x == 'test' else 0)
    
    # 3. 列重命名与选择
    print("🔄 选择论文所需列...")
    # 创建最终的论文格式DataFrame
    paper_df = pd.DataFrame({
        'timestamp': df['timestamp'],
        'value': df['value'],
        'label': df['label'],
        'KPI ID': df['KPI ID'],
        'missing': df['missing'],
        'is_test': df['is_test']
    })
    
    # 4. 数据排序 (按KPI ID和时间戳)
    print("🔍 按KPI和时间排序数据...")
    paper_df = paper_df.sort_values(by=['KPI ID', 'timestamp'])
    
    # 5. 保存结果
    print(f"💾 保存论文格式数据: {OUTPUT_FILE}")
    paper_df.to_csv(OUTPUT_FILE, index=False)
    
    # 数据统计
    print("\n✅ 转换完成! 论文格式数据集统计:")
    print(f"总记录数: {len(paper_df)}")
    print(f"唯一KPI数量: {paper_df['KPI ID'].nunique()}")
    print(f"训练集比例: {1 - paper_df['is_test'].mean():.2%}")
    print(f"异常点比例: {paper_df['label'].mean():.2%}")
    print(f"时间范围: {datetime.fromtimestamp(paper_df['timestamp'].min())} 至 {datetime.fromtimestamp(paper_df['timestamp'].max())}")

if __name__ == "__main__":
    main()