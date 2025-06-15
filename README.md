# 微服务异常检测系统 - FluxEV在SockShop与Online-Boutique的应用

本项目为**软件测试与维护课程期末大作业**，实现基于FluxEV算法的微服务异常检测系统，在SockShop和Online-Boutique双系统上进行完整验证。

## 📂 项目结构概览

```bash
13_SoftwareTest/
├── data-onlineboutique/           # Online-Boutique监控数据集
├── data-sockshop/                 # SockShop监控数据集
├── test_jmeter/                   # JMeter性能测试套件
├── test_selenium/                 # Selenium功能测试套件
├── microservices-demo-sockshop/   # SockShop微服务演示环境
├── microservices-demo-onlineboutique/ # Online-Boutique微服务演示环境
├── onlineboutique_essay/          # Online-Boutique相关文档
├── v1.0/                          # 初始版本：论文源码分析
├── v2.0/                          # 改进版本：算法复现与优化
└── v3.0/                          # 最终版本：完整系统实现
```

## 🔍 详细目录说明

### 1. 数据集目录

#### `data-sockshop/` - SockShop监控数据集
```
├── data_process.py            # 数据处理脚本
├── newcrawler.py              # Prometheus数据爬虫
├── standard_data.py           # 数据标准化脚本
└── standard_dataset.csv       # 标准化数据集 (3.2MB)
```

#### `data-onlineboutique/` - Online-Boutique监控数据集
```
├── data_process.py            # 数据处理脚本
├── enhanced_crawler.py        # 增强型数据爬虫
├── standard_data.py           # 数据标准化脚本
└── improved.csv               # 改进的数据集
```

### 2. 微服务演示环境

#### `microservices-demo-sockshop/` - SockShop演示系统
- 包含SockShop微服务系统的完整部署配置和源码

#### `microservices-demo-onlineboutique/` - Online-Boutique演示系统  
- 包含Online-Boutique微服务系统的完整部署配置和源码

### 3. 测试套件

#### `test_jmeter/` - JMeter性能测试
```
├── Online-Boutique.jmx        # Online-Boutique负载测试配置 (16KB)
├── SockShopTest1.jmx          # SockShop基准测试场景 (26KB)
└── SockShopTest2.jmx          # SockShop压力测试场景 (27KB)
```

#### `test_selenium/` - Selenium自动化测试
```
├── selenium_test1.mp4              # 基础功能测试录像 (2.2MB)
├── selenium_test_performance.mp4   # 性能测试录像 (11MB)
├── test_online.py                  # Online-Boutique功能测试脚本
└── test_online_performance.py      # 性能自动化测试脚本 (250行)
```

### 4. 项目文档

#### `onlineboutique_essay/` - Online-Boutique相关文档
- 包含与Online-Boutique系统相关的研究文档和分析报告

### 5. 版本演进历程

| 版本 | 目录 | 主要内容 | 核心贡献 |
|------|------|----------|----------|
| **v1.0** | `/v1.0/` | 论文源码分析与理解 | 🔬 深入分析FluxEV算法原理 |
| **v2.0** | `/v2.0/` | 算法复现与数据验证 | 🔄 完成算法复现与性能评估 |
| **v3.0** | `/v3.0/` | 完整系统集成实现 | 🚀 监控数据采集与实时检测 |

#### v1.0 - 算法理解阶段
```
├── main.py              # 原始算法实现
├── spot_pipe.py         # SPOT异常检测管道
├── preprocessing.py     # 数据预处理模块
├── eval_methods.py      # 评估方法集合
├── utils.py            # 工具函数库
└── readme.md           # 版本说明文档
```

#### v2.0 - 算法优化阶段
```
├── main.py              # 优化后主程序
├── new-main.py          # 新版本主程序
├── evaluate.py          # 完整评估系统
├── data/               # 测试数据集
└── readme_v2.md        # 版本更新说明
```

#### v3.0 - 系统集成阶段
```
├── main.py              # 统一主程序入口
├── sock-main.py         # SockShop专用检测程序
├── new-main.py          # 改进版检测程序
├── evaluate.py          # 完整评估框架
├── data/               # 实时监控数据
└── readme_v3.md        # 最终版本说明
```
