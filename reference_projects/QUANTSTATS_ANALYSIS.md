# QuantStats 项目技术分析文档

## 1. 项目概述

**项目名称**: QuantStats
**GitHub**: https://github.com/ranaroussi/quantstats
**主要语言**: Python
**Star**: 6,700+
**许可证**: Apache 2.0

QuantStats 是专业的**量化投资组合绩效分析库**，生成专业级的HTML回测报告，支持80+种绩效指标。

---

## 2. 项目结构

```
quantstats/
├── quantstats/               # 核心包
│   ├── stats.py             # 统计引擎
│   ├── plots.py             # 可视化模块
│   ├── reports.py           # 报告生成器
│   ├── utils.py             # 工具函数
│   └── _plotting/           # 绘图子模块
├── tests/                   # 测试 (~125个)
├── docs/                    # 文档
└── setup.py                 # 项目配置
```

---

## 3. 核心功能模块

### 3.1 quantstats.stats - 统计引擎

**收益指标**:
- `cagr` / `ror` - 复合年增长率
- `avg_return` / `avg_win` / `avg_loss` - 平均收益
- `best` / `worst` - 最佳/最差收益

**风险指标**:
- `volatility` - 年化波动率
- `max_drawdown` - 最大回撤
- `drawdown_details` - 回撤详情
- `var` / `cvar` - VaR / CVaR
- `ulcer_index` - 溃疡指数

**风险调整收益**:
- `sharpe` - 夏普比率
- `sortino` - 索提诺比率
- `calmar` - 卡玛比率
- `information_ratio` - 信息比率
- `kelly_criterion` - 凯利准则

**其他指标**:
- `win_rate` / `win_loss_ratio` - 胜率
- `profit_factor` - 盈利因子
- `skew` / `kurtosis` - 偏度/峰度

### 3.2 quantstats.plots - 可视化
- `snapshot` - 收益快照
- `drawdown` - 回撤图
- `rolling_sharpe` - 滚动夏普比率
- `monthly_heatmap` - 月度热力图
- `monte_carlo` - 蒙特卡洛分布

### 3.3 quantstats.reports - 报告生成
- `qs.reports.basic()` - 基础指标和图表
- `qs.reports.full()` - 完整指标和图表
- `qs.reports.html()` - 生成HTML报告

---

## 4. 技术架构

### 4.1 数据模型
- 接受 Pandas Series/DataFrame（每日/每周/每月收益率）
- 扩展 pandas 方法 (`qs.extend_pandas()`)

### 4.2 核心依赖
```
pandas >= 1.5.0    # 核心数据结构
numpy >= 1.24.0    # 数值计算
scipy >= 1.11.0    # 统计函数
matplotlib >= 3.7.0  # 图表渲染
seaborn >= 0.13.0  # 图表美化
yfinance >= 0.2.40  # 数据下载
plotly (可选)       # 交互式图表
```

### 4.3 设计模式
- **Facade 模式**: 高层次API封装底层复杂性
- **延迟导入**: reports.py延迟导入stats/plots

---

## 5. 使用示例

```python
import quantstats as qs

# 扩展 pandas 方法
qs.extend_pandas()

# 下载收益率数据
returns = qs.utils.download_returns('AAPL')
benchmark = qs.utils.download_returns('SPY')

# 计算指标
sharpe = qs.stats.sharpe(returns)
max_dd = qs.stats.max_drawdown(returns)

# 生成完整报告
qs.reports.html(returns, benchmark=benchmark,
                title='AAPL vs S&P500',
                output='report.html')
```

---

## 6. 绩效指标详解

| 指标 | 计算方法 | 用途 |
|------|----------|------|
| **Sharpe** | (Rp-Rf)/σp | 风险调整收益 |
| **Sortino** | (Rp-Rf)/σd | 下行风险调整收益 |
| **Calmar** | CAGR/MDD | 收益/回撤比 |
| **VaR** | 置信区间损失 | 风险度量 |
| **CVaR** | 尾部期望损失 | 极端风险 |
| **Kelly** | 2p-1 | 最优仓位 |

---

## 7. 技术特点

| 特点 | 评价 |
|------|------|
| **易用性** | 高 - 简洁API，支持链式调用 |
| **指标丰富度** | 高 - 50+ 绩效和风险指标 |
| **可视化** | 中 - 静态图表为主，可选Plotly |
| **集成能力** | 高 - 可与backtrader、zipline无缝对接 |

---

## 8. 可借鉴的设计

1. **指标系统** - 完整的风险调整收益指标
2. **HTML报告** - 一键生成专业报告
3. **Facade模式** - 简洁的API设计
4. **Pandas扩展** - 链式调用支持

---

*文档生成时间: 2026-02-21*
