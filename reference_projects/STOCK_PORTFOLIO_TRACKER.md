# Stock Portfolio Tracker 项目技术分析文档

## 1. 项目概述

**项目名称**: Stock Portfolio Tracker
**GitHub**: https://github.com/eftekin/stock-portfolio-tracker
**许可证**: MIT

Stock Portfolio Tracker 是一个**轻量级投资组合追踪工具**。

---

## 2. 项目结构

```
stock-portfolio-tracker/
├── main.py           # 主程序入口
└── README.md
```

---

## 3. 核心功能

| 函数 | 功能 |
|------|------|
| `getStockValue(symbol, quantity)` | 获取单只股票价值 |
| `getPortfolioValue(stocks)` | 计算组合总价值 |

---

## 4. 技术架构

- **语言**: Python 3.x
- **数据源**: Yahoo Finance (`yfinance`)
- **架构**: 简单脚本式

---

## 5. 总结

这是一个**入门级示例项目**，功能简单，仅用于演示：
- 如何使用 `yfinance` 获取股价
- 如何计算投资组合价值

**局限性**: 无持久化、无错误处理、无模块化设计

---

*文档生成时间: 2026-02-22*
