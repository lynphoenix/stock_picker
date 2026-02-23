# Awesome-Quant 项目技术分析文档

## 1. 项目概述

**项目名称**: Awesome-Quant
**GitHub**: https://github.com/awesomeq/awesome-quant
**许可证**: Apache-2.0

Awesome-Quant 是一个**量化投资资源汇总列表**，收录了业界最佳的量化投资开源项目和工具。

---

## 2. 资源分类体系

### 按编程语言
- Python、R、Matlab、Julia、Java、JavaScript、Haskell、Scala、Ruby、Elixir/Erlang、Golang、C++、C#、Rust

### 功能分类
- **Numerical Libraries** - 数值库与数据结构
- **Financial Instruments** - 金融工具与定价
- **Trading & Backtesting** - 交易与回测
- **Risk Analysis** - 风险分析
- **Factor Analysis** - 因子分析
- **Time Series** - 时间序列
- **Data Sources** - 数据源
- **Visualization** - 可视化
- **Frameworks** - 框架

---

## 3. 核心资源列表

| 资源 | 主要功能 | 许可证 |
|------|----------|--------|
| **QuantLib** | 金融衍生品定价行业标准 | BSD 3-Clause |
| **TA-Lib** | 技术指标库 | BSD |
| **PyPortfolioOpt** | 现代投资组合优化 | MIT |
| **mlfinlab** | 金融机器学习 | Apache-2.0 |
| **Qlib** | AI量化投资平台 (微软) | Apache-2.0 |
| **zvt** | 统一数据/因子/回测平台 | MIT |
| **freqtrade** | 加密货币交易机器人 | MIT |
| **Lean (QuantConnect)** | 全栈量化引擎 | Apache-2.0 |
| **yfinance** | Yahoo Finance 数据 | MIT |
| **akshare** | 国内金融数据 | MIT |
| **nautilus_trader** | 高性能交易框架 | MIT |
| **jesse** | 加密货币回测框架 | MIT |
| **pysystemtrade** | 系统化交易 | - |

---

## 4. Python 生态重点推荐

### 4.1 数据源
```python
# 国内
akshare      # A股、期货、宏观数据
baostock     # A股数据，无需注册

# 海外
yfinance     # Yahoo Finance
tushare      # A股数据 (需注册)
```

### 4.2 回测框架
```python
backtrader   # 经典回测框架
jesse        # 加密货币回测
zvt          # 统一回测平台
QuantConnect Lean  # 专业级引擎
```

### 4.3 分析工具
```python
quantstats   # 绩效分析
alphalens    # 因子分析
Riskfolio    # 组合优化
PyOD         # 异常检测
```

### 4.4 AI/ML
```python
Qlib         # 微软AI量化平台
FinGPT       # 金融大语言模型
mlfinlab     # 金融ML算法
```

---

## 5. 技术特点

| 特点 | 说明 |
|------|------|
| **语言覆盖** | 12+ 种编程语言 |
| **分类清晰** | 语言+功能双层分类 |
| **资源质量** | 收录行业标准库和前沿项目 |
| **社区活跃** | 定期更新维护 |

---

## 6. 对 stock_picker 项目的价值

### 建议引用
1. **akshare** - 项目已在用
2. **PyPortfolioOpt** - 组合优化
3. **Qlib** - AI量化平台
4. **quantstats** - 绩效分析
5. **alphalens** - 因子分析

---

*文档生成时间: 2026-02-21*
