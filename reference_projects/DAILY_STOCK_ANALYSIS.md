# Daily Stock Analysis 项目技术分析文档

## 1. 项目概述

**项目名称**: Daily Stock Analysis
**GitHub**: https://github.com/ZhuLinsen/daily_stock_analysis
**主要语言**: Python + TypeScript
**许可证**: MIT

Daily Stock Analysis 是一个**自动化股票分析系统**，支持每日自动分析、GitHub Actions 部署、多渠道通知。

---

## 2. 项目结构

```
daily-stock-analysis/
├── src/                    # 核心业务逻辑
│   ├── analyzer.py        # AI分析层
│   ├── config.py          # 配置管理
│   ├── storage.py         # 数据存储
│   ├── notification.py    # 多渠道通知
│   ├── search_service.py  # 新闻搜索
│   ├── stock_analyzer.py # 技术分析
│   ├── market_analyzer.py # 大盘分析
│   └── core/             # 核心模块
├── data_provider/          # 数据源 (6个)
│   ├── akshare_fetcher.py
│   ├── tushare_fetcher.py
│   ├── yfinance_fetcher.py
│   ├── baostock_fetcher.py
│   ├── efinance_fetcher.py
│   └── pytdx_fetcher.py
├── api/                    # FastAPI
├── bot/                    # 机器人平台
├── apps/
│   ├── dsa-web/          # React前端
│   └── dsa-desktop/      # Electron桌面
└── .github/workflows/     # 自动化
```

---

## 3. 核心功能模块

### 3.1 数据获取层
| 数据源 | 功能 |
|--------|------|
| AkShare | 东方财富数据 |
| Tushare Pro | 专业A股数据 |
| Baostock | 证券宝数据 |
| YFinance | Yahoo Finance |
| eFinance | eFinance数据 |
| Pytdx | 通达信数据 |

### 3.2 AI分析层
- 封装 Gemini、Claude、OpenAI 兼容API
- 股票分析能力

### 3.3 技术分析
- MA均线多头排列检测
- 乖离率计算
- 筹码分布分析

### 3.4 通知渠道 (11+)
- 企业微信、飞书、Telegram
- 邮件、Discord、钉钉
- Server酱、PushPlus

---

## 4. 技术架构

### 4.1 技术栈

| 类别 | 技术 |
|------|------|
| 后端 | Python 3.10+ / FastAPI |
| 前端 | React 19 + TypeScript + Vite |
| 状态管理 | Zustand |
| 数据库 | SQLite + SQLAlchemy |
| AI | Gemini / Claude / OpenAI |
| CI/CD | GitHub Actions |
| 容器 | Docker |

### 4.2 架构模式
- **分层架构**: 数据层 → 服务层 → 业务层 → API层
- **单例模式**: 配置管理
- **工厂模式**: 数据获取、通知服务
- **流水线模式**: 股票分析流程
- **多源策略**: 数据源优先级配置、故障转移

---

## 5. 自动化机制

### 5.1 GitHub Actions

| 工作流 | 触发 | 功能 |
|--------|------|------|
| daily_analysis.yml | 定时(18:00) + 手动 | 每日股票分析 |
| ci.yml | PR | 代码检查、Docker构建 |
| docker-publish.yml | 推送 | 镜像构建发布 |

### 5.2 自动化特性
- 定时任务: 周一至周五北京时间18:00
- 随机延迟: 0-60秒避免API限流
- 并发控制: 同一时间只运行一个任务
- 多渠道推送: 分析完成后自动推送

---

## 6. 技术特点

| 特点 | 说明 |
|------|------|
| **多源数据** | 6个数据源，按优先级自动切换 |
| **多AI模型** | Gemini/Claude/OpenAI兼容 |
| **多通知渠道** | 11+推送方式 |
| **无服务器** | GitHub Actions免费运行 |
| **完整CI/CD** | 代码检查、测试、部署 |
| **现代前端** | React 19 + TypeScript |

---

## 7. 可借鉴的设计

1. **多源数据策略** - 故障自动转移
2. **多AI模型支持** - 按优先级选择
3. **流水线模式** - 清晰的分析流程
4. **GitHub Actions** - 零成本自动化

---

*文档生成时间: 2026-02-22*
