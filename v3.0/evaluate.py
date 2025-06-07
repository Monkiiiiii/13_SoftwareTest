"""
evaluate.py - KPI异常检测评估系统
功能：
1. 加载检测结果
2. 计算整体和每个KPI的性能指标
3. 可视化评估结果
4. 生成HTML评估报告
"""
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
import seaborn as sns
from sklearn.metrics import (precision_score, recall_score, f1_score, 
                             confusion_matrix, roc_curve, auc, 
                             precision_recall_curve, average_precision_score)
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import html
import webbrowser
from datetime import datetime

# 设置中文支持（如果需要）
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class KPIEvaluator:
    """KPI异常检测结果评估器"""
    
    def __init__(self, results_path):
        """
        初始化评估器
        :param results_path: 检测结果文件路径 (detection_results.csv)
        """
        self.results_path = results_path
        self.df = None
        self.metrics_df = None
        self.html_report = None
        self.output_dir = os.path.dirname(results_path) or "results"
        self.report_filename = f"evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_data(self):
        """加载检测结果数据"""
        print(f"加载检测结果: {self.results_path}")
        self.df = pd.read_csv(self.results_path)
        
        # 确保数据包含必要列
        required_columns = ['uuid', 'timestamp', 'value', 'true_label', 'predicted_anomaly']
        for col in required_columns:
            if col not in self.df.columns:
                raise ValueError(f"缺失必要列: {col}")
                
        # 尝试解析时间戳
        try:
            self.df['datetime'] = pd.to_datetime(self.df['timestamp'], unit='s', errors='coerce')
            if self.df['datetime'].isnull().any():
                # 如果无法转换为时间，则使用原始时间戳
                print("警告: 部分时间戳无法转换，使用原始值")
                self.df['datetime'] = self.df['timestamp']
        except:
            self.df['datetime'] = self.df['timestamp']
            
        print(f"- 加载完成, 总记录数: {len(self.df)}")
        print(f"- 总KPI数量: {self.df['uuid'].nunique()}")
        print(f"- 时间范围: {self.df['datetime'].min()} 到 {self.df['datetime'].max()}")
        print(f"- 异常点比例: {self.df['true_label'].mean():.2%}")
        
        return self.df
    
    def calculate_metrics(self):
        """计算整体和每个KPI的性能指标"""
        print("\n计算性能指标...")
        
        # 整体指标
        overall_metrics = {
            'precision': precision_score(self.df['true_label'], self.df['predicted_anomaly']),
            'recall': recall_score(self.df['true_label'], self.df['predicted_anomaly']),
            'f1_score': f1_score(self.df['true_label'], self.df['predicted_anomaly']),
            'true_anomalies': self.df['true_label'].sum(),
            'detected_anomalies': self.df['predicted_anomaly'].sum(),
            'false_alarms': ((self.df['predicted_anomaly'] == 1) & (self.df['true_label'] == 0)).sum()
        }
        
        # 计算混淆矩阵
        cm = confusion_matrix(self.df['true_label'], self.df['predicted_anomaly'])
        tn, fp, fn, tp = cm.ravel()
        overall_metrics.update({
            'confusion_matrix': cm,
            'true_negative': tn,
            'false_positive': fp,
            'false_negative': fn,
            'true_positive': tp
        })
        
        # 按KPI计算指标
        kpi_metrics = []
        for uuid, group in self.df.groupby('uuid'):
            if len(group) > 0:
                metrics = {
                    'uuid': uuid,
                    'num_points': len(group),
                    'true_anomalies': group['true_label'].sum(),
                    'detected_anomalies': group['predicted_anomaly'].sum(),
                    'precision': precision_score(group['true_label'], group['predicted_anomaly'], zero_division=0),
                    'recall': recall_score(group['true_label'], group['predicted_anomaly'], zero_division=0),
                    'f1_score': f1_score(group['true_label'], group['predicted_anomaly'], zero_division=0),
                    'false_positive': ((group['predicted_anomaly'] == 1) & (group['true_label'] == 0)).sum(),
                    'false_negative': ((group['predicted_anomaly'] == 0) & (group['true_label'] == 1)).sum(),
                    'threshold': group['threshold'].iloc[0] if 'threshold' in group.columns else np.nan
                }
                kpi_metrics.append(metrics)
        
        # 创建指标DataFrame
        self.metrics_df = pd.DataFrame(kpi_metrics)
        
        # 计算一些额外的统计信息
        self.metrics_df['anomaly_ratio'] = self.metrics_df['true_anomalies'] / self.metrics_df['num_points']
        self.metrics_df['detection_rate'] = self.metrics_df['detected_anomalies'] / self.metrics_df['num_points']
        
        # 按F1分数排序
        self.metrics_df = self.metrics_df.sort_values(by='f1_score', ascending=False)
        
        print(f"- 已计算 {len(self.metrics_df)} 个KPI的性能指标")
        print(f"- 平均F1分数: {self.metrics_df['f1_score'].mean():.4f}")
        print(f"- 最大F1分数: {self.metrics_df['f1_score'].max():.4f}")
        print(f"- 最小F1分数: {self.metrics_df['f1_score'].min():.4f}")
        
        return overall_metrics, self.metrics_df
    
    def plot_confusion_matrix(self, cm, title='混淆矩阵'):
        """绘制混淆矩阵"""
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['正常', '异常'], 
                    yticklabels=['正常', '异常'])
        plt.xlabel('预测结果')
        plt.ylabel('真实情况')
        plt.title(title)
        file_path = os.path.join(self.output_dir, 'confusion_matrix.png')
        plt.savefig(file_path, bbox_inches='tight')
        plt.close()
        return file_path
    
    def plot_metrics_distribution(self):
        """绘制指标分布图"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # F1分数分布
        sns.histplot(self.metrics_df['f1_score'], bins=20, kde=True, ax=axes[0, 0])
        axes[0, 0].set_title('F1分数分布')
        axes[0, 0].set_xlabel('F1分数')
        axes[0, 0].set_ylabel('频次')
        
        # 精确率-召回率分布
        sns.scatterplot(x='precision', y='recall', data=self.metrics_df, 
                        size='num_points', sizes=(20, 200), ax=axes[0, 1])
        axes[0, 1].set_title('精确率 vs 召回率')
        axes[0, 1].set_xlabel('精确率')
        axes[0, 1].set_ylabel('召回率')
        
        # F1与异常率关系
        sns.scatterplot(x='anomaly_ratio', y='f1_score', data=self.metrics_df, 
                        size='num_points', sizes=(20, 200), ax=axes[1, 0])
        axes[1, 0].set_title('异常率 vs F1分数')
        axes[1, 0].set_xlabel('异常率')
        axes[1, 0].set_ylabel('F1分数')
        
        # 检测率分布
        sns.kdeplot(self.metrics_df['detection_rate'], fill=True, ax=axes[1, 1])
        axes[1, 1].set_title('检测率分布')
        axes[1, 1].set_xlabel('检测率')
        axes[1, 1].set_ylabel('密度')
        
        plt.tight_layout()
        file_path = os.path.join(self.output_dir, 'metrics_distribution.png')
        plt.savefig(file_path, bbox_inches='tight')
        plt.close()
        return file_path
    
    def plot_kpi_performance(self):
        """绘制KPI性能排行榜"""
        # 筛选有足够点数的KPI
        plot_df = self.metrics_df[self.metrics_df['num_points'] > 10].sort_values('f1_score', ascending=False)
        
        if plot_df.empty:
            return None
            
        # 取前20个KPI
        plot_df = plot_df.head(20)
        
        plt.figure(figsize=(12, 8))
        bar_width = 0.25
        index = np.arange(len(plot_df))
        
        plt.bar(index, plot_df['f1_score'], bar_width, label='F1分数')
        plt.bar(index + bar_width, plot_df['precision'], bar_width, label='精确率')
        plt.bar(index + 2 * bar_width, plot_df['recall'], bar_width, label='召回率')
        
        plt.xlabel('KPI')
        plt.ylabel('得分')
        plt.title('KPI性能排行榜 (F1分数前20名)')
        plt.xticks(index + bar_width, plot_df['uuid'].str[:15] + "...", rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        
        file_path = os.path.join(self.output_dir, 'kpi_performance.png')
        plt.savefig(file_path, bbox_inches='tight')
        plt.close()
        return file_path
    
    def plot_kpi_timeseries(self, kpi_id=None):
        """绘制指定KPI的时间序列和检测结果"""
        # 如果没有指定，选择性能最好的KPI
        if kpi_id is None and not self.metrics_df.empty:
            kpi_id = self.metrics_df.iloc[0]['uuid']
        elif kpi_id is None:
            return None
            
        kpi_data = self.df[self.df['uuid'] == kpi_id]
        
        if len(kpi_data) < 10:
            print(f"警告: KPI {kpi_id} 数据点不足")
            return None
            
        # 获取KPI性能指标
        kpi_metrics = self.metrics_df[self.metrics_df['uuid'] == kpi_id].iloc[0]
        
        # 创建交互式图表
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 添加KPI值曲线
        fig.add_trace(
            go.Scatter(
                x=kpi_data['datetime'], 
                y=kpi_data['value'], 
                name='KPI值',
                mode='lines',
                line=dict(color='royalblue', width=1.5),
                hoverinfo='text',
                hovertext=kpi_data.apply(lambda row: f"时间: {row['datetime']}<br>值: {row['value']:.4f}", axis=1)
            ),
            secondary_y=False
        )
        
        # 添加真实异常点
        true_anomalies = kpi_data[kpi_data['true_label'] == 1]
        fig.add_trace(
            go.Scatter(
                x=true_anomalies['datetime'], 
                y=true_anomalies['value'], 
                name='真实异常',
                mode='markers',
                marker=dict(color='green', size=8, symbol='circle'),
                hoverinfo='text',
                hovertext=true_anomalies.apply(lambda row: f"时间: {row['datetime']}<br>值: {row['value']:.4f}<br>真实异常", axis=1)
            ),
            secondary_y=False
        )
        
        # 添加预测异常点
        pred_anomalies = kpi_data[kpi_data['predicted_anomaly'] == 1]
        fig.add_trace(
            go.Scatter(
                x=pred_anomalies['datetime'], 
                y=pred_anomalies['value'], 
                name='预测异常',
                mode='markers',
                marker=dict(color='red', size=8, symbol='x'),
                hoverinfo='text',
                hovertext=pred_anomalies.apply(lambda row: f"时间: {row['datetime']}<br>值: {row['value']:.4f}<br>预测异常", axis=1)
            ),
            secondary_y=False
        )
        
        # 添加阈值线（如果存在）
        if 'threshold' in kpi_data.columns and not kpi_data['threshold'].isnull().all():
            threshold = kpi_data['threshold'].mean()
            fig.add_trace(
                go.Scatter(
                    x=kpi_data['datetime'],
                    y=[threshold] * len(kpi_data),
                    name='异常阈值',
                    mode='lines',
                    line=dict(color='orange', width=2, dash='dash'),
                    hoverinfo='text',
                    hovertext=f"阈值: {threshold:.6f}"
                ),
                secondary_y=False
            )
        
        # 添加置信度曲线（如有）
        if 'confidence' in kpi_data.columns and not kpi_data['confidence'].isnull().all():
            fig.add_trace(
                go.Scatter(
                    x=kpi_data['datetime'],
                    y=kpi_data['confidence'],
                    name='异常置信度',
                    mode='lines',
                    line=dict(color='purple', width=1),
                    hoverinfo='text',
                    hovertext=kpi_data.apply(lambda row: f"时间: {row['datetime']}<br>置信度: {row['confidence']:.2f}", axis=1)
                ),
                secondary_y=True
            )
        
        # 设置布局
        title = f"KPI检测结果: {kpi_id[:20] + ('...' if len(kpi_id) > 20 else '')}"
        title += f"<br><sup>F1: {kpi_metrics['f1_score']:.3f}, 精确率: {kpi_metrics['precision']:.3f}, 召回率: {kpi_metrics['recall']:.3f}</sup>"
        
        fig.update_layout(
            title=title,
            xaxis_title='时间',
            yaxis_title='KPI值',
            legend_title='图例',
            hovermode='x unified',
            height=600
        )
        
        if 'confidence' in kpi_data.columns and not kpi_data['confidence'].isnull().all():
            fig.update_yaxes(title_text="置信度", secondary_y=True)
        
        # 保存为HTML文件
        file_path = os.path.join(self.output_dir, f'kpi_{kpi_id[:10]}_timeseries.html')
        fig.write_html(file_path, include_plotlyjs='cdn')
        
        return file_path
    
    def create_interactive_report(self, overall_metrics):
        """创建交互式HTML评估报告"""
        print("\n生成评估报告...")
        
        # 基本信息
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>KPI异常检测评估报告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 1200px; margin: auto; padding: 20px; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .card {{ background: #f9f9f9; border-radius: 5px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .metric-card {{ text-align: center; padding: 10px; background: #e3f2fd; border-radius: 5px; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #1976d2; margin: 10px 0; }}
                .img-container {{ text-align: center; margin: 20px 0; }}
                img {{ max-width: 100%; height: auto; }}
                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <h1>KPI异常检测评估报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>结果文件: {os.path.basename(self.results_path)}</p>
            
            <div class="card">
                <h2>数据集概览</h2>
                <p>总记录数: {len(self.df):,}</p>
                <p>KPI数量: {self.df['uuid'].nunique()}</p>
                <p>时间范围: {self.df['datetime'].min()} 至 {self.df['datetime'].max()}</p>
                <p>异常点比例: {self.df['true_label'].mean():.2%}</p>
            </div>
            
            <div class="card">
                <h2>整体性能指标</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div>F1分数</div>
                        <div class="metric-value">{overall_metrics['f1_score']:.4f}</div>
                    </div>
                    <div class="metric-card">
                        <div>精确率</div>
                        <div class="metric-value">{overall_metrics['precision']:.4f}</div>
                    </div>
                    <div class="metric-card">
                        <div>召回率</div>
                        <div class="metric-value">{overall_metrics['recall']:.4f}</div>
                    </div>
                    <div class="metric-card">
                        <div>真实异常</div>
                        <div class="metric-value">{overall_metrics['true_anomalies']:,}</div>
                    </div>
                    <div class="metric-card">
                        <div>检测异常</div>
                        <div class="metric-value">{overall_metrics['detected_anomalies']:,}</div>
                    </div>
                    <div class="metric-card">
                        <div>误报数</div>
                        <div class="metric-value">{overall_metrics['false_alarms']:,}</div>
                    </div>
                </div>
            </div>
        """
        
        # 添加混淆矩阵
        if hasattr(overall_metrics, 'confusion_matrix'):
            cm = overall_metrics['confusion_matrix']
            html_content += f"""
            <div class="card">
                <h2>混淆矩阵</h2>
                <div class="img-container">
                    <img src="confusion_matrix.png" alt="混淆矩阵">
                </div>
                <table>
                    <tr><th>真实 \ 预测</th><th>正常 (0)</th><th>异常 (1)</th></tr>
                    <tr><th>正常 (0)</th><td>{cm[0, 0]}</td><td>{cm[0, 1]}</td></tr>
                    <tr><th>异常 (1)</th><td>{cm[1, 0]}</td><td>{cm[1, 1]}</td></tr>
                </table>
            </div>
            """
        
        # 添加KPI性能排行榜
        html_content += """
        <div class="card">
            <h2>KPI性能排行榜</h2>
        """
        
        if self.metrics_df is not None and not self.metrics_df.empty:
            top_kpis = self.metrics_df.head(10)
            html_content += """
            <div class="img-container">
                <img src="kpi_performance.png" alt="KPI性能排行榜">
            </div>
            
            <table>
                <tr>
                    <th>KPI ID</th>
                    <th>数据点数</th>
                    <th>异常点数</th>
                    <th>检测点数</th>
                    <th>F1分数</th>
                    <th>精确率</th>
                    <th>召回率</th>
                </tr>
            """
            
            for _, row in top_kpis.iterrows():
                html_content += f"""
                <tr>
                    <td>{html.escape(str(row['uuid']))[:30] + ('...' if len(str(row['uuid'])) > 30 else '')}</td>
                    <td>{row['num_points']}</td>
                    <td>{row['true_anomalies']}</td>
                    <td>{row['detected_anomalies']}</td>
                    <td>{row['f1_score']:.4f}</td>
                    <td>{row['precision']:.4f}</td>
                    <td>{row['recall']:.4f}</td>
                </tr>
                """
            
            html_content += """
            </table>
            """
        
        html_content += """
        </div>
        
        <div class="card">
            <h2>指标分布</h2>
            <div class="img-container">
                <img src="metrics_distribution.png" alt="指标分布">
            </div>
        </div>
        
        <div class="card">
            <h2>详细检测结果示例</h2>
        """
        
        # 添加示例KPI时间序列
        if self.metrics_df is not None and not self.metrics_df.empty:
            best_kpi = self.metrics_df.iloc[0]['uuid']
            worst_kpi = self.metrics_df.iloc[-1]['uuid']
            mid_kpi = self.metrics_df.iloc[len(self.metrics_df)//2]['uuid']
            
            html_content += f"""
            <h3>最佳性能KPI (F1={self.metrics_df.iloc[0]['f1_score']:.3f})</h3>
            <iframe src="{os.path.basename(self.plot_kpi_timeseries(best_kpi))}" width="100%" height="600" frameborder="0"></iframe>
            
            <h3>中等性能KPI (F1={self.metrics_df.iloc[len(self.metrics_df)//2]['f1_score']:.3f})</h3>
            <iframe src="{os.path.basename(self.plot_kpi_timeseries(mid_kpi))}" width="100%" height="600" frameborder="0"></iframe>
            
            <h3>最差性能KPI (F1={self.metrics_df.iloc[-1]['f1_score']:.3f})</h3>
            <iframe src="{os.path.basename(self.plot_kpi_timeseries(worst_kpi))}" width="100%" height="600" frameborder="0"></iframe>
            """
        
        html_content += """
        </div>
        </body>
        </html>
        """
        
        # 保存HTML报告
        report_path = os.path.join(self.output_dir, self.report_filename)
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"- 评估报告已保存至: {report_path}")
        self.html_report = report_path
        return report_path
    
    def open_report(self):
        """在默认浏览器中打开报告"""
        if self.html_report:
            webbrowser.open('file://' + os.path.abspath(self.html_report))
    
    def run_evaluation(self):
        """运行完整评估流程"""
        try:
            # 加载数据
            self.load_data()
            
            # 计算指标
            overall_metrics, metrics_df = self.calculate_metrics()
            
            # 创建可视化
            self.plot_confusion_matrix(overall_metrics['confusion_matrix'])
            self.plot_metrics_distribution()
            self.plot_kpi_performance()
            
            # 生成报告
            self.create_interactive_report(overall_metrics)
            
            # 打开报告
            self.open_report()
            return True
        except Exception as e:
            print(f"评估过程中出错: {str(e)}")
            return False

# 主程序
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='KPI异常检测评估系统')
    parser.add_argument('--results', type=str, default='./results/detection_results.csv',
                        help='检测结果文件路径 (detection_results.csv)')
    
    args = parser.parse_args()
    
    print("\n===== KPI异常检测评估系统 =====")
    evaluator = KPIEvaluator(args.results)
    if evaluator.run_evaluation():
        print("\n评估完成!")
    else:
        print("\n评估失败!")