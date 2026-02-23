# Stock Screener 项目技术分析文档

## 1. 项目概述

**项目名称**: Stock Screener
**GitHub**: https://github.com/amladik/Stock-Screener
**许可证**: MIT

Stock Screener 是一个**基于魔法公式的量化选股工具**。

---

## 2. 项目结构

```
stock-screener/
├── Stock Screener.py   # 主程序 (~142行)
└── README.md
```

---

## 3. 核心功能

### 3.1 数据爬取
- **数据源**: MarketWatch.com
- **指标**: 市值、ROIC、P/E、P/B、P/S

### 3.2 评分系统
实现 Joel Greenblatt 的"魔法公式":

| 指标 | 评分方式 |
|------|----------|
| Market Cap | 降序排名 |
| ROIC | 降序排名 |
| EBIT | 降序排名 |
| P/B | 升序排名 |
| P/S | 升序排名 |

**综合评分**: Kunal Score = 各指标排名之和

---

## 4. 技术架构

- **语言**: Python 3
- **爬虫**: requests + BeautifulSoup
- **数据处理**: pandas + numpy
- **输出**: Excel

---

## 5. 特点

| 特点 | 说明 |
|------|------|
| 轻量级 | 单文件脚本 |
| 算法简单 | 排名评分易于理解 |
| 局限性 | 无并发、无缓存、易失效 |

---

*文档生成时间: 2026-02-22*
