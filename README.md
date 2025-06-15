# 微服务异常检测系统 - FluxEV在SockShop与Online-Boutique的应用

本项目为**软件测试与维护课程期末大作业**，实现基于FluxEV算法的微服务异常检测系统，在SockShop和Online-Boutique双系统上进行完整验证。

## 项目结构

```bash
13_SoftwareTest/
├── data-onlineboutique/           # Online-Boutique监控数据采集及数据集
├── data-sockshop/                 # SockShop监控数据采集及数据集
├── test_jmeter/                   # JMeter性能测试
├── test_selenium/                 # Selenium功能测试代码及演示视频
├── microservices-demo-sockshop/   # SockShop微服务演示环境
├── microservices-demo-onlineboutique/ # Online-Boutique微服务演示环境
├── SockShop_FluxEV复现代码/        # SockShop系统FluxEV算法实现
├── OnlineBoutique_FluxEV复现代码/  # OnlineBoutique系统FluxEV算法实现
├── v1.0/                          # 初始版本：论文源码分析
└── v2.0/                          # 改进版本：算法复现与优化
```

## 详细目录说明

### 1. 数据

#### `data-sockshop/` - SockShop监控数据采集及数据集
```
├── data_process.py            # 数据处理脚本
├── newcrawler.py              # Prometheus数据爬虫
├── standard_data.py           # 数据标准化脚本
└── standard_dataset.csv       # 标准化数据集 
```

#### `data-onlineboutique/` - Online-Boutique监控数据采集及数据集
```
├── data_process.py            # 数据处理脚本
├── enhanced_crawler.py        # 增强型Prometheus数据
├── standard_data.py           # 数据标准化脚本
└── improved.csv               # 改进的数据集
```

### 2. 微服务演示环境

#### `microservices-demo-sockshop/` - SockShop演示系统
- 包含SockShop微服务系统的完整部署配置和源码

#### `microservices-demo-onlineboutique/` - Online-Boutique演示系统  
- 包含Online-Boutique微服务系统的完整部署配置和源码

### 3. FluxEV算法复现代码

#### `SockShop_FluxEV复现代码/` - SockShop系统异常检测实现
```
├── main.py              # 统一主程序入口 
├── sock-main.py         # SockShop专用检测程序 
├── new-main.py          # 改进版检测程序
├── evaluate.py          # 完整评估框架 
├── spot_pipe.py         # SPOT异常检测管道 
├── preprocessing.py     # 数据预处理模块 
├── eval_methods.py      # 评估方法集合 
├── utils.py            # 工具函数库
├── data/               # 实时监控数据
└── readme_v3.md       
```

#### `OnlineBoutique_FluxEV复现代码/` - OnlineBoutique系统异常检测实现
```
├── online-main.py                        # 主算法实现
├── detection_results.csv                 # 异常检测结果
├── evaluation_report_20250615_183606.html # HTML评估报告
├── confusion_matrix.png                  # 混淆矩阵可视化 
├── kpi_performance.png                   # KPI性能图表 
└── readme.md                             
```
### 4. 测试

#### `test_jmeter/` - JMeter性能测试
```
├── Online-Boutique.jmx        # Online-Boutique负载测试配置 
├── SockShopTest1.jmx          # 基准测试场景 
└── SockShopTest2.jmx          # 压力测试场景 
```

#### `test_selenium/` - Selenium自动化测试
```
├── selenium_test1.mp4              # 基础功能测试录像 
├── selenium_test_performance.mp4   # 性能测试录像 
├── test_online.py                  # Online-Boutique功能测试脚本
└── test_online_performance.py      # 性能自动化测试脚本
```



#### v1.0 - 算法理解
```
├── main.py              
├── spot_pipe.py         
├── preprocessing.py     
├── eval_methods.py      
├── utils.py            
└── readme.md           
```

#### v2.0 - 算法优化
```
├── main.py             
├── new-main.py         
├── evaluate.py          
├── data/              
└── readme_v2.md       
```
