import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re

# 配置参数
INPUT_FILE = "data2\prometheus_metrics_20250607_090250.csv"
OUTPUT_FILE = "cleaned_prometheus_data.csv"
EXPERIMENT_START = "2025-06-07 05:36:00"  # 实际监测开始时间
FAULT_START = "2025-06-07 06:10:33"       # 故障开始时间
FAULT_DURATION = timedelta(minutes=5)     # 故障持续5分钟
FAULT_END = (datetime.strptime(FAULT_START, "%Y-%m-%d %H:%M:%S") + FAULT_DURATION).strftime("%Y-%m-%d %H:%M:%S")
RECOVERY_PERIOD = 20                      # 故障后保留时间(分钟)

def main():
    # 1. 读取原始数据
    print(f"📊 读取数据集: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    print(f"原始数据: {len(df)}行 × {len(df.columns)}列")
    print(f"列名示例: {list(df.columns)[:10]}...")
    
    # 2. 时间处理与过滤
    # 确保时间戳格式正确
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    
    # 过滤有效时间段
    print(f"⏱ 过滤时间范围: {EXPERIMENT_START} 至故障结束+{RECOVERY_PERIOD}分钟")
    end_time = (datetime.strptime(FAULT_END, "%Y-%m-%d %H:%M:%S") + 
               timedelta(minutes=RECOVERY_PERIOD)).strftime("%Y-%m-%d %H:%M:%S")
    df = df[(df['timestamp'] >= EXPERIMENT_START) & (df['timestamp'] <= end_time)]
    print(f"过滤后数据: {len(df)}行")
    
    # 3. 故障标记 (基于实验数据)
    print(f"⚠️ 标记故障时间段: {FAULT_START} 至 {FAULT_END}")
    df['is_fault'] = np.where(
        (df['timestamp'] >= FAULT_START) & (df['timestamp'] <= FAULT_END), 1, 0
    )
    
    # 4. 数据清洗 - 基于提供的数据结构
    print("🧹 执行数据清洗...")
    
    # 4.1 处理标签异常（如"cpu_usage_%!<"）
    if 'metric' in df.columns:
        df['metric'] = df['metric'].str.replace(r'%!<$MISSING$', '', regex=True)
        df['metric'] = df['metric'].str.replace('_%!', '%', regex=False)
    
    # 4.2 标记关键服务 (payment-service)
    payment_flags = ['payment', 'pay-service', 'payments', 'payment-svc']
    if 'pod' in df.columns:
        df['is_payment'] = df['pod'].apply(
            lambda x: 1 if any(flag in str(x).lower() for flag in payment_flags) else 0
        )
    elif 'app' in df.columns:
        df['is_payment'] = df['app'].apply(
            lambda x: 1 if any(flag in str(x).lower() for flag in payment_flags) else 0
        )
    
    # 4.3 处理数值类型异常
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    
    # 4.4 数据分组填充
    if 'series_id' in df.columns:
        df.sort_values(by=['series_id', 'timestamp'], inplace=True)
        df['value'] = df.groupby('series_id')['value'].ffill()
    
    # 4.5 移除冗余列
    redundant_columns = [
        'beta_kube', 'beta_kube_id', 'kube___name', 
        'controller_revision_hash', 'pod_template_hash',
        'annotation_prometheus_io_scrape', 'k8s_app',
        'helm_sh_chart', 'app_kuberr', 'app_kuber',
        'kubernetes', 'k8s_io_component', 'k8s_io_instance'
    ]
    redundant_columns = [col for col in redundant_columns if col in df.columns]
    
    if redundant_columns:
        print(f"🗑️ 移除冗余列: {', '.join(redundant_columns)}")
        df.drop(columns=redundant_columns, inplace=True)
    
    # 4.5.1 第二阶段冗余列清理
    print("🧹 第二阶段冗余列清理")
    phase2_redundant = [
        'beta_kubernetes_io_arch', 'beta_kubernetes_io_os', 'id',
        'kubernetes_io_arch', 'kubernetes_io_os', 
        'minikube_k8s_io_commit', 'minikube_k8s_io_name', 'minikube_k8s_io_primary',
        'minikube_k8s_io_updated_at', 'minikube_k8s_io_version',
        'kubernetes_namespace', 'kubernetes_pod_name', 'pod_template_generation',
        'kubernetes_name', 'name', 'kubernetes_io_cluster_service',
        'kubernetes_io_name', 'is_train', '_name_', 'abnormal'
    ]
    phase2_redundant = [col for col in phase2_redundant if col in df.columns]

    if phase2_redundant:
        print(f"🗑️ 移除冗余列: {', '.join(phase2_redundant)}")
        df.drop(columns=phase2_redundant, inplace=True)

    
    # 4.6 重命名和规范列名
    print("✏️ 规范化列名")
    df.columns = [col.lower().replace(':', '_').replace('.', '_') for col in df.columns]
    df.columns = [re.sub(r'__+', '_', col) for col in df.columns]  # 移除多余下划线
    
    # 5. 数据集划分
    print("📊 划分训练集和测试集")
    
    # 5.1 优先使用现有标记
    if 'is_train' in df.columns:
        print("🔄 使用现有的is_train标记")
        train_df = df[df['is_train'] == 1].copy()
        test_df = df[df['is_train'] == 0].copy()
    # 5.2 如果没有标记，按时间划分
    else:
        print("🕒 按时间划分: 故障前为训练集，故障及恢复期为测试集")
        train_df = df[df['timestamp'] < FAULT_START].copy()
        test_df = df[df['timestamp'] >= FAULT_START].copy()
    
    train_df['dataset'] = 'train'
    test_df['dataset'] = 'test'
    processed_df = pd.concat([train_df, test_df])
    
    # 6. 特征增强
    print("✨ 特征增强")
    
    # 6.1 时间特征
    processed_df['hour'] = processed_df['timestamp'].dt.hour
    processed_df['minute'] = processed_df['timestamp'].dt.minute
    processed_df['day_of_week'] = processed_df['timestamp'].dt.dayofweek
    
    # 6.2 数值特征
    if 'value' in processed_df.columns:
        processed_df['value_diff'] = processed_df.groupby('series_id')['value'].diff()
    
    # 7. 保存结果
    print(f"💾 保存处理后的数据: {OUTPUT_FILE}")
    processed_df.to_csv(OUTPUT_FILE, index=False)
    
    # 数据统计
    print("\n✅ 数据处理完成!")
    print(f"总记录数: {len(processed_df)}")
    print(f"训练集大小: {len(train_df)} ({len(train_df)/len(processed_df):.1%})")
    print(f"测试集大小: {len(test_df)}")
    print(f"故障数据点: {processed_df['is_fault'].sum()}")
    print(f"检测到支付服务的数据点: {processed_df['is_payment'].sum() if 'is_payment' in processed_df else 0}")

if __name__ == "__main__":
    main()