# 微服务异常检测系统 - FluxEV在SockShop与Online-Boutique的应用

本项目为**软件测试与维护课程期末大作业**，实现基于FluxEV算法的微服务异常检测系统，在SockShop和Online-Boutique双系统上进行完整验证。

## 📂 项目结构概览

```bash
13_SoftwareTest/
├── data-online-boutique/      # Online-Boutique监控数据集
├── data-sockshop/             # SockShop监控数据集
├── test_jmeter/               # JMeter性能测试套件
├── test_selenium/             # Selenium功能测试套件
├── v1.0/                      # 初始版本：论文源码分析
├── v2.0/                      # 改进版本：算法复现
├── v3.0/                      # 优化版本：监控数据采集
└── Final_version/             # 最终交付版本（含完整结果）
'''

## 🔍 详细目录说明

```bash
1. 数据集目录
​​data-online-boutique/​​ - Online-Boutique监控数据集
├── data_process.py            # 数据处理脚本
├── enhanced_crawler.py        # 强化爬虫脚本
├── improved.csv               # 优化后数据集
└── standard_data.py           # 数据标准化脚本

​​data-sockshop/​​ - SockShop监控数据集
├── data_process.py            # 数据处理脚本
├── newcrawler.py              # 新型爬虫脚本
├── standard_data.py           # 数据标准化脚本
└── standard_dataset.csv       # 标准化数据集

2. 测试套件
​​test_jmeter/​​ - JMeter性能测试
├── Online-Boutique.jmx       # Online-Boutique测试方案
├── SockShopTest1.jmx          # SockShop测试场景1
└── SockShopTest2.jmx          # SockShop测试场景2

​​test_selenium/​​ - Selenium功能测试
├── selenium_test1.mp4         # 功能测试录像
├── selenium_test_performance.mp4 # 性能测试录像
├── test_online.py            # Online-Boutique测试脚本
└── test_online_performance.py # 性能测试脚本

3. 版本演进
版本	  位置	                  内容	              主要贡献
v1.0	  /v1.0	             论文源码分析与注释	   理解FluxEV算法核心思想
v2.0	  /v2.0	             使用原始数据集复现	   完成首次算法复现
v3.0	  /v3.0	             监控数据采集实现	   开发Prometheus数据抓取脚本
​​Final​​	  /Final_version	   完整解决方案	       双系统算法验证

​​最终版本内容 (Final_version/)​​：
├── confusion_matrix.png       # 混淆矩阵可视化
├── detection_results.csv      # 异常检测结果
├── evaluation_report_20250615_183606.html # HTML评估报告
├── kpi_performance.png        # KPI性能图表
├── online-main.py             # 主算法实现
└── readme.md                  # 项目说明文档
