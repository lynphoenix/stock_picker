# 参考项目分析汇总文档

> 项目参考文件夹路径: `/Users/linyining/Documents/code/stock_picker/reference_projects/`

---

## 文档列表

| # | 文档名 | 项目名 | 用途 |
|---|--------|--------|------|
| 1 | [LEAN_ANALYSIS.md](./LEAN_ANALYSIS.md) | Lean (QuantConnect) | 量化交易引擎 |
| 2 | [JESSE_ANALYSIS.md](./JESSE_ANALYSIS.md) | Jesse | 加密货币交易框架 |
| 3 | [ALPHALENS_ANALYSIS.md](./ALPHALENS_ANALYSIS.md) | Alphalens | 因子分析 |
| 4 | [BACKTRADER_ANALYSIS.md](./BACKTRADER_ANALYSIS.md) | Backtrader | 回测框架 |
| 5 | [QUANTSTATS_ANALYSIS.md](./QUANTSTATS_ANALYSIS.md) | QuantStats | 绩效分析 |
| 6 | [AKSHARE_ANALYSIS.md](./AKSHARE_ANALYSIS.md) | AKShare | 数据源 (A股) |
| 7 | [PYOD_ANALYSIS.md](./PYOD_ANALYSIS.md) | PyOD | 异常检测 |
| 8 | [RISKFOLIO_ANALYSIS.md](./RISKFOLIO_ANALYSIS.md) | Riskfolio-Lib | 组合优化 |
| 9 | [BAOSTOCK_ANALYSIS.md](./BAOSTOCK_ANALYSIS.md) | Baostock | 数据源 (A股) |
| 10 | [AWESOME_QUANT_ANALYSIS.md](./AWESOME_QUANT_ANALYSIS.md) | Awesome-Quant | 资源汇总 |
| 11 | [TRADINGAGENTS_ANALYSIS.md](./TRADINGAGENTS_ANALYSIS.md) | TradingAgents | AI多智能体交易 |
| 12 | [FINGPT_ANALYSIS.md](./FINGPT_ANALYSIS.md) | FinGPT | 金融大语言模型 |
| 13 | [DAILY_STOCK_ANALYSIS.md](./DAILY_STOCK_ANALYSIS.md) | Daily Stock Analysis | 自动化股票分析 |
| 14 | [SITUATION_MONITOR.md](./SITUATION_MONITOR.md) | Situation Monitor | 全球新闻监控 |
| 15 | [VALUECELL.md](./VALUECELL.md) | ValueCell | 金融多智能体平台 |
| 16 | [STOCK_PORTFOLIO_TRACKER.md](./STOCK_PORTFOLIO_TRACKER.md) | Stock Portfolio Tracker | 投资组合追踪 |
| 17 | [FIBOOKS.md](./FIBOOKS.md) | Fibooks | 财务报表分析 |
| 18 | [STOCK_MONITOR.md](./STOCK_MONITOR.md) | Stock Monitor | 实时监控告警 |
| 19 | [STOCK_SCREENER.md](./STOCK_SCREENER.md) | Stock Screener | 量化选股 |

---

## 仓库状态

| 项目 | 状态 | 说明 |
|------|------|------|
| Lean | ✅ 完整 | 508M, 专业级量化引擎 |
| Jesse | ✅ 完整 | 72M, 加密货币交易框架 |
| Alphalens | ✅ 完整 | 55M, 因子分析 |
| PyOD | ✅ 完整 | 18M, 异常检测 |
| AKShare | ✅ 完整 | 12M, 数据源 |
| Backtrader | ✅ 完整 | 9.9M, 回测框架 |
| QuantStats | ✅ 完整 | 80K, 绩效分析 |
| Riskfolio-Lib | ✅ 完整 | 80K, 组合优化 |
| Baostock | ✅ 完整 | 80K, 数据源 |
| Awesome-Quant | ✅ 完整 | 80K, 资源列表 |
| FinGPT | ✅ 完整 | 金融大模型 |
| TradingAgents | ✅ 完整 | AI交易系统 |
| daily-stock-analysis | ❌ 空 | 远程仓库为空 |
| ESN | ❌ 空 | 仓库损坏 |
| financial-statements | ❌ 空 | 远程仓库不存在 |
| situation-monitor | ❌ 空 | 仓库损坏 |

---

## 功能对比矩阵

| 功能 | Lean | Jesse | Alphalens | Backtrader | QuantStats | AKShare | PyOD | Riskfolio | TradingAgents | FinGPT |
|------|------|-------|-----------|------------|------------|---------|------|-----------|---------------|--------|
| **数据采集** | ✅ | ✅ | - | - | - | ✅ | - | - | ✅ | ✅ |
| **回测引擎** | ✅ | ✅ | - | ✅ | - | - | - | - | - | - |
| **因子分析** | - | - | ✅ | - | - | - | - | - | - | - |
| **绩效分析** | ✅ | ✅ | - | ✅ | ✅ | - | - | - | - | - |
| **组合优化** | ✅ | - | - | - | - | - | - | ✅ | - | - |
| **异常检测** | - | - | - | - | - | - | ✅ | - | - | - |
| **AI/ML** | - | - | - | - | - | - | - | - | ✅ | ✅ |
| **技术指标** | 150+ | 175+ | - | 122+ | - | - | - | - | - | - |
| **多资产** | ✅ | 加密货币 | - | ✅ | - | A股 | - | - | - | - |

---

## 快速参考

### 数据源
- **A股**: AKShare, Baostock (项目已在用)

### 回测框架
- **专业级**: Lean
- **Python经典**: Backtrader
- **加密货币**: Jesse

### 分析工具
- **绩效分析**: QuantStats
- **因子分析**: Alphalens
- **组合优化**: Riskfolio-Lib

### AI/ML
- **多智能体交易**: TradingAgents
- **金融大模型**: FinGPT

### 辅助工具
- **异常检测**: PyOD (可用于价格异常监控)

---

*文档生成时间: 2026-02-21*
