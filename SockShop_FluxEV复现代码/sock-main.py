import os
import os.path as osp
import time
import numpy as np
import pandas as pd
from glob import glob
from sklearn.metrics import f1_score, recall_score, precision_score
import argparse
import numba
import sys

# 添加父目录到系统路径，以便导入spot_pipe
sys.path.append('..')
from spot_pipe import SPOT
from eval_methods import adjust_predicts

# ===== 全局变量 =====
detection_results = []  # 用于收集所有KPI的详细检测结果
thresholds_dict = {}   # 用于存储每个KPI的阈值

# ===== 辅助函数 =====

def calc_ewma(input_arr, alpha=0.2, adjust=True):
    arr_len = len(input_arr)

    if adjust:
        power_arr = np.array(range(len(input_arr)-1, -1, -1))
        a = np.full(arr_len, 1-alpha)
        weight_arr = np.power(a, power_arr)
        ret = np.sum(input_arr * weight_arr) / np.sum(weight_arr)

    else:
        ret_arr = [input_arr[0]]
        for i in range(1, arr_len):
            temp = alpha * input_arr[i] + (1 - alpha) * ret_arr[-1]
            ret_arr.append(temp)
        ret = ret_arr[-1]
    return ret

@numba.jit(nopython=True)
def calc_ewma_v2(input_arr, alpha=0.2):
    arr_len = len(input_arr)
    ret_arr = [input_arr[0]]
    for i in range(1, arr_len):
        temp = alpha * input_arr[i] + (1 - alpha) * ret_arr[-1]
        ret_arr.append(temp)
    ret = ret_arr[-1]
    return ret

def calc_first_smooth(input_arr):
    return max(np.nanstd(input_arr) - np.nanstd(input_arr[:-1]), 0)

def calc_second_smooth(input_arr):
    return max(np.nanmax(input_arr) - np.nanmax(input_arr[:-1]), 0)

# ===== 检测函数 =====
def detect(data_arr, train_len, period, smoothing=2,
           s_w=10, p_w=7, half_d_w=2, q=0.001,
           estimator="MOM", kpi_id="default"):
    """异常检测函数，修复了全局变量声明问题"""
    global thresholds_dict  # 在函数开头声明全局变量
    
    data_len = len(data_arr)  # 数据总长度
    spot = SPOT(q, estimator=estimator)  # 创建一个SPOT检测器

    d_w = half_d_w * 2  # d_w 是完整的数据漂移窗口大小（对称的）

    # 计算提取异常特征的起始索引
    fs_idx = s_w * 2  # 一次平滑的起始索引
    fs_lm_idx = fs_idx + d_w  # 一次平滑局部最大值数组的起始索引
    ss_idx = fs_idx + half_d_w + period * (p_w - 1)  # 二次平滑的起始索引

    # 初始化数组
    pred_err = np.full(data_len, np.nan)  # 预测误差数组
    fs_err = np.full(data_len, np.nan)    # 一次平滑误差数组
    fs_err_lm = np.full(data_len, np.nan) # 一次平滑误差的局部最大值数组
    ss_err = np.full(data_len, np.nan)    # 二次平滑误差数组
    
    # 报警结果 & 阈值列表
    th, alarms = [], []
    init_threshold = None  # 初始化阈值

    # 模式一：一级平滑
    if smoothing == 1:
        for i in range(s_w, data_len):
            # 计算预测值Pi和预测误差Ei
            Pi = calc_ewma_v2(data_arr[i - s_w: i])
            Ei = data_arr[i] - Pi
            pred_err[i] = Ei

            # 一次平滑
            if i >= fs_idx:
                FSEi = calc_first_smooth(pred_err[i - s_w: i + 1])
                fs_err[i] = FSEi

            # SPOT检测
            if i == train_len - 1:  # 使用训练数据初始化SPOT检测器
                init_data = fs_err[fs_idx: i + 1]
                spot.fit(init_data)
                spot.initialize()
                init_threshold = spot.init_threshold
                # 保存阈值到全局字典
                thresholds_dict[kpi_id] = init_threshold

            if i >= train_len:  # 逐个检测测试点
                th_s, alarm_s = spot.run_step(fs_err[i])
                th.append(th_s)
                alarms.append(alarm_s)

    elif smoothing == 2:
        for i in range(s_w, data_len):
            # 计算预测值Pi和预测误差Ei
            Pi = calc_ewma_v2(data_arr[i - s_w: i])
            Ei = data_arr[i] - Pi
            pred_err[i] = Ei

            if i >= fs_idx:
                # 一次平滑
                FSEi = calc_first_smooth(pred_err[i - s_w: i + 1])
                fs_err[i] = FSEi

                # 提取局部最大值
                if i >= fs_lm_idx:
                    FSEi_lm = max(fs_err[i - d_w: i + 1])
                    fs_err_lm[i - half_d_w] = FSEi_lm

                # 二次平滑
                if i >= ss_idx:
                    tem_arr = np.append(fs_err_lm[i - period * (p_w - 1): i: period], fs_err[i])
                    SSEi = calc_second_smooth(tem_arr)
                    ss_err[i] = SSEi

            # SPOT检测
            if i == train_len - 1:  # 使用训练数据初始化SPOT检测器
                init_data = ss_err[ss_idx: i + 1]
                spot.fit(init_data)
                spot.initialize()
                init_threshold = spot.init_threshold
                # 保存阈值到全局字典
                thresholds_dict[kpi_id] = init_threshold

            if i >= train_len:  # 逐个检测测试点
                th_s, alarm_s = spot.run_step(ss_err[i])

                # 如果检测到异常，更新其特征;避免影响后续点的特征提取
                if alarm_s:
                    fs_err[i] = np.nan
                    FSEi_lm = max(fs_err[i - d_w: i + 1])
                    fs_err_lm[i - half_d_w] = FSEi_lm

                th.append(th_s)
                alarms.append(alarm_s)

    alarms = np.array(alarms)
    return alarms, init_threshold

# ===== KPI主函数 =====
def main_kpi(args, base_dir, data_path):
    """修复了全局变量声明问题的KPI主函数"""
    global detection_results  # 在函数开头声明全局变量
    global thresholds_dict
    
    ret_dir = osp.join(base_dir, "1709_2results")
    ret_file_path = osp.join(ret_dir, args.ret_file).format(args.estimator,
                                                           args.s_w, args.p_w,
                                                           args.half_d_w, args.q)
    if not osp.exists(ret_dir):
        os.makedirs(ret_dir)
        print(f"- 创建输出目录: {ret_dir}")

    # 重置全局结果容
    detection_results = []
    thresholds_dict = {}
    print("- 已重置全局结果容器")

    # 读取数据并转换数据类型
    print(f"\n正在加载数据: {data_path}")
    data_df = pd.read_csv(data_path)
    # 转换数据类型
    data_df[["timestamp", "label", "missing", "is_test"]] = \
        data_df[["timestamp", "label", "missing", "is_test"]].astype(int)
    print(f"- 加载完成, 总记录数: {len(data_df)}")

    y_true, y_pred = [], []
    
    # 获取所有唯一的KPI ID
    kpi_ids = data_df["KPI ID"].unique()
    print(f"- 发现 {len(kpi_ids)} 个KPI, 即将开始处理...")
    
    for name, group in data_df.sort_values(by=["KPI ID", "timestamp"], ascending=True).groupby("KPI ID"):
        print(f"\n开始处理KPI: {name}")

        # 重置索引并获取数据
        group.reset_index(drop=True, inplace=True)
        timestamp = group["timestamp"].values
        value = group["value"].values
        label = group["label"].values
        missing = group["missing"].values
        is_test = group["is_test"].values

        # 确定训练集长度
        if not args.train_len:
            train_len = sum(is_test == 0)
            print(f"- 自动计算训练数据点: {train_len}/{len(value)}")
        else:
            train_len = args.train_len
            print(f"- 自定义训练数据点: {train_len}/{len(value)}")

        # 计算周期
        interval = timestamp[1] - timestamp[0]
        period = 1440 * 60 // interval
        print(f"- 周期: {period} (间隔: {interval}秒)")

        # 平滑方法
        smoothing = 2
        print(f"- 使用{smoothing}阶平滑方法")

        # 准备测试集标签
        label_test = label[train_len:]
        test_missing = missing[train_len:]
        print(f"- 测试数据点: {len(label_test)} (其中 {sum(label_test==1)} 个真实异常点)")

        # 调用detect函数获取报警序列和阈值
        print("- 正在计算异常阈值...")
        start_time = time.time()
        alarms, kpi_threshold = detect(
            data_arr=value,
            train_len=train_len,
            period=period,
            smoothing=smoothing,
            s_w=args.s_w,
            p_w=args.p_w,
            half_d_w=args.half_d_w,
            q=args.q,
            estimator=args.estimator,
            kpi_id=name
        )
        elapsed = time.time() - start_time
        print(f"- 阈值计算完成, 耗时: {elapsed:.2f}秒")
        print(f"- 使用的阈值: {kpi_threshold:.6f}")

        # 处理缺失点
        alarms[np.where(test_missing == 1)] = 0  # 缺失点不标记为异常
        ret_test = adjust_predicts(predict=alarms, label=label_test, delay=args.delay)
        detected_anomalies = ret_test.sum()
        print(f"- 检测到异常点数量: {detected_anomalies} (占总测试点的 {detected_anomalies/len(ret_test):.2%})")

        # 收集详细的检测结果
        print("- 正在收集详细检测结果...")
        test_indices = range(train_len, len(value))
        count = 0
        for i, idx in enumerate(test_indices):
            value_point = value[idx]
            is_anomaly = ret_test[i]
            
            detection_results.append({
                'uuid': name,
                'timestamp': timestamp[idx],
                'value': value_point,
                'true_label': label[idx],
                'predicted_anomaly': int(is_anomaly),
                'threshold': kpi_threshold,
                'is_above_threshold': int(value_point > kpi_threshold)
            })
            
            # 实时输出检测到的异常点
            if is_anomaly:
                count += 1
                print(f"  检测到异常点 @ {timestamp[idx]} (值: {value_point:.6f} > 阈值: {kpi_threshold:.6f})")
        
        print(f"- 已收集{count}个异常点和{len(label_test)}个正常点的信息")

        y_true.append(label_test)
        y_pred.append(ret_test)

    # 保存详细检测结果
    print("\n正在保存详细检测结果...")
    results_df = pd.DataFrame(detection_results)
    results_csv_path = osp.join(ret_dir, 'detection_results.csv')
    results_df.to_csv(results_csv_path, index=False)
    print(f"- 详细检测结果已保存至: {results_csv_path}")
    print(f"- 总检测点数量: {len(results_df)} (其中 {results_df['predicted_anomaly'].sum()} 个异常点)")

    # 计算整体指标
    y_true_arr, y_pred_arr = np.concatenate(y_true), np.concatenate(y_pred)
    f_score = f1_score(y_true_arr, y_pred_arr)
    recall = recall_score(y_true_arr, y_pred_arr)
    precision = precision_score(y_true_arr, y_pred_arr)

    print("\n===== KPI数据集评估结果 =====")
    print(f"F1分数: {f_score:.4f}")
    print(f"召回率: {recall:.4f}")
    print(f"精确率: {precision:.4f}")

    # 保存评估指标
    with open(ret_file_path, "w") as f:
        f.write("KPI数据集评估结果:\n")
        f.write(f"F1分数: {f_score}\n")
        f.write(f"召回率: {recall}\n")
        f.write(f"精确率: {precision}\n")
        f.write(f"KPI数量: {len(kpi_ids)}\n")
        f.write(f"总测试点数量: {len(y_true_arr)}\n")
    print(f"- 评估指标已保存至: {ret_file_path}")

# ===== 主程序入口 =====
if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="FluxEV异常检测系统")
    parser.add_argument('--dataset', type=str, default='sock', choices=['sock', 'KPI'],
                        help="要处理的数据集: KPI 或 sock (默认: KPI)")
    parser.add_argument('--delay', type=int, default=7,
                        help="评估时的延迟点数 (默认: 7)")
    parser.add_argument('--q', type=float, default=0.05,
                        help="SPOT的风险系数 (默认: 0.003)")

    parser.add_argument('--s_w', type=int, default=10,
                        help="提取局部波动并进行一步平滑的顺序窗口大小 (默认: 10)")
    parser.add_argument('--p_w', type=int, default=5,
                        help="进行二步平滑的周期性窗口大小 (默认: 5)")
    parser.add_argument('--half_d_w', type=int, default=2,
                        help="处理数据漂移的半窗口大小 (默认: 2)")

    parser.add_argument('--estimator', type=str, default="MOM", choices=["MOM", "MLE"],
                        help="SPOT的估计方法: 'MOM' 或 'MLE' (默认: MOM)")
    parser.add_argument('--train_len', type=int, default=None,
                        help="训练数据长度 (用于初始化SPOT), "
                             "默认为None时使用数据集的前半部分")

    parser.add_argument('--ret_file', type=str, default='evaluation-{}-s{}-p{}-d{}-q{}.txt',
                        help="结果文件名模板 (默认: evaluation-{}-s{}-p{}-d{}-q{}.txt)")

    # 解析参数
    flags = parser.parse_args()
    
    print("\n===== FluxEV 异常检测系统 =====")
    print(f"数据集: {flags.dataset}")
    print(f"参数: s_w={flags.s_w}, p_w={flags.p_w}, half_d_w={flags.half_d_w}")
    print(f"SPOT配置: q={flags.q}, estimator={flags.estimator}")
    print(f"评估延迟: {flags.delay}点")
    
    # 根据选择的数据集执行
    start_time = time.time()
    
    if flags.dataset == "sock":
        base_dir = "./data/sock_shop/"
        data_path = osp.join(base_dir, "17_09.csv")
        flags.delay = 7
        flags.q = 0.01
        print(f"\n处理KPI数据集: {data_path}")
        main_kpi(flags, base_dir, data_path)
        
    # elif flags.dataset == "Yahoo":
    #     data_dir = "./data/Yahoo"
    #     flags.delay = 3
    #     flags.q = 0.001
    #     print(f"\n处理Yahoo数据集: {data_dir}")
    #     main_yahoo(flags, data_dir)
    else:
        print(f"错误: 不支持的数据集 '{flags.dataset}'")
        sys.exit(1)
    
    # 计算并显示运行时间
    elapsed = time.time() - start_time
    mins, secs = divmod(elapsed, 60)
    print(f"\n===== 处理完成! =====\n总耗时: {int(mins)}分{secs:.2f}秒")