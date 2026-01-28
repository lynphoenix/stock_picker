# A股智能选股系统 - 架构设计文档

## 📋 目录

- [系统概述](#系统概述)
- [整体架构](#整体架构)
- [核心模块](#核心模块)
- [代码结构](#代码结构)
- [策略系统](#策略系统)
- [回测引擎](#回测引擎)
- [使用指南](#使用指南)
- [扩展开发](#扩展开发)

---

## 系统概述

A股智能选股系统是一个**模块化、可扩展**的量化交易框架，支持：

- ✅ **多策略支持** - 7+ 种不同类型的交易策略
- ✅ **统一回测引擎** - 策略无关的回测框架
- ✅ **完整风控系统** - 止损、止盈、仓位管理
- ✅ **历史数据管理** - 缓存机制、数据提供者模式
- ✅ **策略组合** - 支持多策略集成和轮换
- ✅ **原有逻辑保留** - 完整保留并增强原 SignalEngine

### 设计原则

1. **分层架构** - 数据层、策略层、回测层、展示层清晰分离
2. **策略无关** - 回测引擎与具体策略解耦
3. **易于扩展** - 新增策略只需继承 Strategy 基类
4. **复用为主** - 最大程度复用原有代码（src/）
5. **向后兼容** - 原有 main.py 和 UI 不受影响

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        展示层 (UI)                           │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Streamlit UI    │  │  Command Line    │                │
│  │  (ui/app.py)     │  │  (main.py)       │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application)                      │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  SignalEngine    │  │  StrategyManager │                │
│  │  (原有逻辑)       │  │  (策略管理器)     │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    策略层 (Strategy)                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │OriginalSignal│ │ MACrossover  │ │  Bollinger   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │  Momentum    │ │ MultiFactor  │ │  Ensemble    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    回测层 (Backtest)                         │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ BacktestEngine   │  │  RiskManager     │                │
│  │  (回测引擎)       │  │  (风控系统)       │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Portfolio       │  │  Trade/Position  │                │
│  │  (账户管理)       │  │  (交易记录)       │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    指标层 (Indicators)                       │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ IndicatorFactory │  │TechnicalIndicators│               │
│  │  (指标工厂)       │  │  (技术指标计算)    │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    数据层 (Data)                             │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  DataManager     │  │  CacheManager    │                │
│  │  (统一数据接口)   │  │  (缓存管理)       │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │Historical Provider│ │ Realtime Provider│                │
│  │  (历史数据)       │  │  (实时数据)       │                │
│  └──────────────────┘  └──────────────────┘                │
│            ▼                       ▼                         │
│  ┌──────────────────────────────────────────┐              │
│  │        DataFetcher (AKShare API)         │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心模块

### 1. 数据层 (core/data/)

#### DataManager - 统一数据接口
```python
# 核心功能：
- 统一的数据获取接口（历史/实时/最新）
- 自动添加技术指标
- 支持缓存机制

# 使用示例：
from core.data import DataManager

dm = DataManager()
df = dm.get_data("000001", mode="historical",
                 start_date="20240101", end_date="20241231")
df = dm.add_indicators(df, ["MA", "MACD", "RSI"])
```

#### HistoricalDataProvider - 历史数据提供者
```python
# 职责：
- 获取指定时间范围的历史数据
- 支持前复权、后复权
- 缓存管理

# 数据来源：
src/data_fetcher.py (复用原有 DataFetcher)
```

#### RealtimeDataProvider - 实时数据提供者
```python
# 职责：
- 获取最新行情数据
- 支持分钟级数据
- 实时指标计算
```

#### CacheManager - 缓存管理
```python
# 功能：
- Pickle 格式缓存
- 自动过期检测
- 缓存命中率优化

# 缓存位置：
data/cache/stock_hist_{code}_{start}_{end}_qfq.pkl
```

---

### 2. 指标层 (core/indicators/)

#### IndicatorFactory - 指标工厂
```python
# 核心特性：
- 注册机制（动态添加指标）
- 统一的计算接口
- 100% 复用原有指标逻辑

# 使用示例：
from core.indicators import IndicatorFactory

df = IndicatorFactory.calculate(df, "MA")      # 计算均线
df = IndicatorFactory.calculate(df, "MACD")    # 计算MACD
df = IndicatorFactory.calculate(df, "RSI")     # 计算RSI
```

#### TechnicalIndicators - 技术指标计算
```python
# 继承关系：
core.indicators.TechnicalIndicators
  ↓ 继承 (0修改，100%复用)
src.technical.TechnicalIndicators

# 支持指标：
- MA (5, 10, 20, 60日均线)
- MACD (DIF, DEA, MACD)
- RSI (相对强弱指标)
- BOLL (布林带)
- KDJ (随机指标)
- Volume (成交量)
```

---

### 3. 策略层 (core/strategies/)

#### Strategy - 策略基类
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class StrategyResult:
    action: str          # "buy" | "sell" | "hold"
    score: float         # 0-100 评分
    reasons: List[str]   # 信号原因
    confidence: float    # 0.0-1.0 置信度
    metadata: Dict       # 额外信息

class Strategy(ABC):
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """返回策略需要的指标列表"""
        pass

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """生成交易信号"""
        pass
```

#### 内置策略

| 策略名称 | 类型 | 适用场景 | 核心逻辑 |
|---------|------|----------|----------|
| **OriginalSignalStrategy** | 原有策略 | 震荡市 | SignalEngine 原始逻辑 |
| **MACDRSIStrategy** | 技术指标 | 趋势+超买超卖 | MACD金叉+RSI+均线 |
| **MACrossoverStrategy** | 趋势跟踪 | 明确趋势 | 双均线金叉/死叉 |
| **BollingerStrategy** | 均值回归 | 震荡市 | 布林带上下轨反转 |
| **MomentumStrategy** | 动量追踪 | 牛市/强势 | 价格动量+创新高 |
| **MultiFactorStrategy** | 多因子 | 全市场 | 趋势+动量+价值+成交量 |
| **StrategyEnsemble** | 策略集成 | 综合 | 多策略加权投票 |

#### 策略对比（2024年回测）

| 策略 | 收益率 | 胜率 | 最大回撤 | 特点 |
|------|--------|------|----------|------|
| OriginalSignalStrategy | +3.78% | 80.0% | 1.64% | ⭐ 最稳健 |
| MACrossoverStrategy | +14.15% | 75.0% | 7.18% | ⭐ 最高收益 |
| BollingerStrategy | +8.55% | 76.9% | 6.60% | 平衡型 |
| MomentumStrategy | +4.15% | 55.6% | 7.38% | 激进型 |
| MultiFactorStrategy | +8.03% | 57.1% | 6.52% | 综合型 |
| StrategyEnsemble | +12.55% | 76.9% | 4.93% | ⭐ 最优综合 |

---

### 4. 回测层 (core/backtest/)

#### BacktestEngine - 回测引擎

```python
class BacktestEngine:
    """
    策略无关的回测引擎

    核心特性：
    - 任何 Strategy 都能直接回测
    - 内置风控系统
    - 完整的交易模拟
    """

    def run(self,
            strategy: Strategy,
            stock_pool: List[str],
            start_date: str,
            end_date: str,
            check_interval: int = 5) -> BacktestResult:
        """
        运行回测

        流程：
        1. 加载历史数据
        2. 定期检查信号（每 check_interval 天）
        3. 模拟交易执行
        4. 应用风控规则
        5. 计算回测指标
        """
```

#### Portfolio - 账户管理

```python
@dataclass
class Position:
    """持仓"""
    code: str
    shares: int
    entry_price: float
    current_price: float
    peak_price: float      # 用于移动止损
    tp1_taken: bool        # 是否已触发止盈1
    tp2_taken: bool        # 是否已触发止盈2

class Portfolio:
    """
    账户管理器

    功能：
    - 现金管理
    - 持仓管理
    - 买入/卖出执行
    - P&L 计算
    """

    def buy(self, code: str, shares: int, price: float) -> bool:
        """买入股票"""

    def sell(self, code: str, shares: int, price: float, reason: str):
        """卖出股票"""

    def update_positions(self, current_prices: Dict[str, float]):
        """更新持仓盈亏"""
```

#### RiskManager - 风控系统

```python
class RiskManager:
    """
    风险管理器

    风控规则：
    1. 最大持仓数限制
    2. 单只股票仓位限制
    3. 止损规则：
       - 硬止损：-10%
       - 移动止损：从最高点回撤4%
    4. 止盈规则：
       - T1: +8% 卖出50%
       - T2: +18% 全部卖出
    """

    def check_position_limits(self) -> bool:
        """检查是否超过最大持仓数"""

    def check_stop_loss(self, position: Position) -> bool:
        """检查是否触发止损"""

    def check_take_profit(self, position: Position) -> Tuple[bool, int]:
        """检查是否触发止盈"""

    def calculate_position_size(self, cash: float) -> float:
        """计算买入金额"""
```

#### BacktestResult - 回测结果

```python
@dataclass
class BacktestResult:
    """回测结果"""
    initial_capital: float      # 初始资金
    final_capital: float        # 最终资金
    total_return: float         # 总收益率 (%)
    total_trades: int           # 交易次数
    winning_trades: int         # 盈利次数
    losing_trades: int          # 亏损次数
    win_rate: float            # 胜率 (%)
    max_drawdown: float        # 最大回撤 (%)
    profit_factor: float       # 盈亏比
    trades: List[Trade]        # 所有交易记录
```

---

## 代码结构

```
stock_picker/
│
├── core/                          # 核心模块（新架构）
│   ├── data/                      # 数据层
│   │   ├── __init__.py
│   │   ├── data_manager.py        # 统一数据接口
│   │   ├── providers.py           # 数据提供者
│   │   └── cache.py               # 缓存管理
│   │
│   ├── indicators/                # 指标层
│   │   ├── __init__.py
│   │   ├── factory.py             # 指标工厂
│   │   └── technical.py           # 技术指标（继承src/）
│   │
│   ├── strategies/                # 策略层
│   │   ├── __init__.py
│   │   ├── strategy_base.py       # 策略基类
│   │   ├── strategy_manager.py    # 策略管理器
│   │   │
│   │   ├── original_signal_strategy.py    # 原有策略
│   │   ├── macd_rsi_strategy.py           # MACD+RSI
│   │   ├── ma_crossover_strategy.py       # 双均线
│   │   ├── bollinger_strategy.py          # 布林带
│   │   ├── momentum_strategy.py           # 动量
│   │   ├── multi_factor_strategy.py       # 多因子
│   │   ├── strategy_ensemble.py           # 策略集成
│   │   └── fundamental_strategy.py        # 基本面（预留）
│   │
│   └── backtest/                  # 回测层
│       ├── __init__.py
│       ├── backtest_engine.py     # 回测引擎
│       ├── portfolio.py           # 账户管理
│       └── risk_manager.py        # 风控系统
│
├── src/                           # 原有模块（完整保留）
│   ├── data_fetcher.py            # 数据获取（AKShare）
│   ├── technical.py               # 技术指标计算
│   ├── fundamentals.py            # 基本面分析
│   ├── signal_engine.py           # 信号引擎（原逻辑）
│   ├── sector_heat.py             # 板块热度
│   ├── stock_screener.py          # 股票筛选
│   └── notifier.py                # 通知推送
│
├── ui/                            # Web界面
│   └── app.py                     # Streamlit应用
│
├── data/                          # 数据目录
│   ├── cache/                     # 缓存文件
│   └── stock_pools.json           # 股票池
│
├── docs/                          # 文档
│   ├── ARCHITECTURE.md            # 架构文档（本文件）
│   ├── PHASE1_GUIDE.md            # Phase 1 指南
│   └── PHASE1_ARCHITECTURE.md     # Phase 1 架构
│
├── tests/                         # 测试文件
│   ├── test_phase1.py             # Phase 1 测试
│   ├── test_phase2.py             # Phase 2 测试
│   ├── test_multi_strategies.py   # 多策略测试
│   └── test_original_vs_new.py    # 原有vs新策略对比
│
├── config.py                      # 配置文件
├── main.py                        # 主程序（原有逻辑保留）
├── backtest.py                    # 旧回测脚本
└── requirements.txt               # 依赖包

```

### 模块职责

| 模块 | 职责 | 状态 |
|------|------|------|
| **core/** | 新架构核心模块 | ✅ 已完成 |
| **src/** | 原有业务逻辑 | ✅ 完整保留 |
| **ui/** | Web界面 | ✅ 正常运行 |
| **main.py** | 原有主程序 | ✅ 向后兼容 |

---

## 策略系统

### 策略生命周期

```python
# 1. 定义策略
class MyStrategy(Strategy):
    def get_required_indicators(self):
        return ["MA", "MACD", "RSI"]

    def generate_signals(self, df):
        # 策略逻辑
        if condition:
            return StrategyResult(action="buy", ...)
        return StrategyResult(action="hold", ...)

# 2. 注册策略
from core.strategies import StrategyManager

manager = StrategyManager()
manager.register_strategy("my_strategy", MyStrategy())

# 3. 运行策略
result = manager.run_strategy("my_strategy", code="000001", mode="realtime")

# 4. 回测策略
from core.backtest import BacktestEngine

engine = BacktestEngine()
backtest_result = engine.run(
    strategy=MyStrategy(),
    stock_pool=["000001", "000002"],
    start_date="20240101",
    end_date="20241231"
)
```

### 策略开发指南

#### 1. 继承 Strategy 基类

```python
from core.strategies import Strategy, StrategyResult
from typing import List
import pandas as pd

class MyNewStrategy(Strategy):
    def __init__(self, params: dict = None):
        self.name = "My New Strategy"
        self.description = "策略描述"
        self.params = params or {}

    def get_required_indicators(self) -> List[str]:
        """返回需要的指标"""
        return ["MA", "MACD"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """生成信号"""
        # 获取最新数据
        latest = df.iloc[-1]

        # 策略逻辑
        score = 0
        reasons = []

        if latest["MA5"] > latest["MA20"]:
            score += 50
            reasons.append("均线多头")

        # 返回结果
        if score >= 60:
            return StrategyResult(
                action="buy",
                score=score,
                reasons=reasons,
                confidence=score/100,
                metadata={}
            )

        return StrategyResult(action="hold", score=0, ...)
```

#### 2. 测试策略

```python
# test_my_strategy.py
from core.backtest import BacktestEngine
from my_strategy import MyNewStrategy

strategy = MyNewStrategy()
engine = BacktestEngine()

result = engine.run(
    strategy=strategy,
    stock_pool=["000001"],
    start_date="20240101",
    end_date="20241231"
)

print(f"收益率: {result.total_return}%")
print(f"胜率: {result.win_rate}%")
```

#### 3. 注册到系统

```python
# core/strategies/__init__.py

from .my_strategy import MyNewStrategy

__all__ = [
    ...
    "MyNewStrategy",
]
```

---

## 回测引擎

### 回测流程

```
开始回测
  ↓
[1] 加载历史数据
  ├─ 从缓存/AKShare获取数据
  ├─ 计算技术指标
  └─ 数据预处理
  ↓
[2] 初始化账户
  ├─ 设置初始资金
  ├─ 创建Portfolio
  └─ 创建RiskManager
  ↓
[3] 回测循环 (每N天检查一次)
  │
  ├─ 3.1 更新持仓价格
  │   └─ portfolio.update_positions()
  │
  ├─ 3.2 检查卖出信号
  │   ├─ 遍历所有持仓
  │   ├─ 检查止损 (RiskManager)
  │   ├─ 检查止盈 (RiskManager)
  │   ├─ 检查技术信号 (Strategy)
  │   └─ 执行卖出
  │
  ├─ 3.3 检查买入信号
  │   ├─ 遍历股票池
  │   ├─ 调用 strategy.generate_signals()
  │   ├─ 过滤已持仓
  │   ├─ 检查仓位限制
  │   └─ 执行买入
  │
  └─ 循环至结束日期
  ↓
[4] 平仓剩余持仓
  └─ 以最后价格全部卖出
  ↓
[5] 计算回测指标
  ├─ 总收益率
  ├─ 交易次数
  ├─ 胜率
  ├─ 最大回撤
  └─ 盈亏比
  ↓
返回 BacktestResult
```

### 风控规则详解

#### 止损规则

```python
# 1. 硬止损 (-10%)
if (current_price - entry_price) / entry_price <= -0.10:
    卖出全部持仓
    原因: "触发止损"

# 2. 移动止损 (从最高点回撤4%)
peak_price = max(peak_price, current_price)  # 更新最高价
if (current_price - peak_price) / peak_price <= -0.04:
    卖出全部持仓
    原因: "移动止损"
```

#### 止盈规则

```python
# 分批止盈策略

# 第一次止盈 (+8%)
if gain >= 0.08 and not tp1_taken:
    卖出50%持仓
    tp1_taken = True
    原因: "止盈T1"

# 第二次止盈 (+18%)
if gain >= 0.18 and not tp2_taken:
    卖出全部剩余持仓
    tp2_taken = True
    原因: "止盈T2"
```

#### 仓位管理

```python
# 最大持仓数限制
max_positions = 3  # 同时最多持有3只股票

# 单只股票仓位
position_size = 0.30  # 每只股票占用30%资金
buy_amount = cash * position_size

# 买入股数（向下取整到100股）
shares = (buy_amount // price) // 100 * 100
```

---

## 使用指南

### 快速开始

#### 1. 环境准备

```bash
# 克隆项目
git clone <repo>
cd stock_picker

# 安装依赖
pip install -r requirements.txt

# 或创建conda环境
conda create -n stock_picker python=3.10
conda activate stock_picker
pip install -r requirements.txt
```

#### 2. 运行原有系统

```bash
# 方式1: Web界面
streamlit run ui/app.py

# 方式2: 命令行
python main.py

# 方式3: 更新股票池
python main.py --update-pools
```

#### 3. 使用新架构

##### 单策略回测

```python
from core.strategies import MACrossoverStrategy
from core.backtest import BacktestEngine

# 创建策略
strategy = MACrossoverStrategy(params={
    "short_window": 5,
    "long_window": 20
})

# 创建回测引擎
engine = BacktestEngine(
    initial_capital=100000,
    risk_config={
        "max_positions": 3,
        "position_size": 0.30,
        "stop_loss": -0.10,
    }
)

# 运行回测
result = engine.run(
    strategy=strategy,
    stock_pool=["000001", "000002", "600036"],
    start_date="20240101",
    end_date="20241231",
    check_interval=5
)

# 查看结果
print(f"收益率: {result.total_return:.2f}%")
print(f"胜率: {result.win_rate:.1f}%")
print(f"最大回撤: {result.max_drawdown:.2f}%")
```

##### 多策略对比

```python
from core.strategies import (
    OriginalSignalStrategy,
    MACrossoverStrategy,
    BollingerStrategy
)

strategies = {
    "原有策略": OriginalSignalStrategy(),
    "双均线": MACrossoverStrategy(),
    "布林带": BollingerStrategy(),
}

results = {}
for name, strategy in strategies.items():
    result = engine.run(strategy, stock_pool, start, end)
    results[name] = result

# 对比结果
for name, result in results.items():
    print(f"{name}: {result.total_return:.2f}%")
```

##### 策略集成

```python
from core.strategies import StrategyEnsemble

# 组合多个策略
ensemble = StrategyEnsemble(
    strategies=[
        (OriginalSignalStrategy(), 0.4),    # 40%权重
        (MACrossoverStrategy(), 0.3),       # 30%权重
        (BollingerStrategy(), 0.3),         # 30%权重
    ],
    voting_method="weighted",  # 加权投票
    min_agreement=0.6          # 最小一致性60%
)

# 回测集成策略
result = engine.run(ensemble, stock_pool, start, end)
```

### 测试脚本

```bash
# Phase 1 测试（基础设施）
python test_phase1.py

# Phase 2 测试（回测引擎）
python test_phase2.py

# 多策略对比测试
python test_multi_strategies.py

# 原有vs新策略对比
python test_original_vs_new.py
```

---

## 扩展开发

### 添加新策略

#### 步骤1: 创建策略文件

```python
# core/strategies/my_custom_strategy.py

from typing import Dict, List
import pandas as pd
from .strategy_base import Strategy, StrategyResult

class MyCustomStrategy(Strategy):
    """我的自定义策略"""

    def __init__(self, params: Dict = None):
        default_params = {
            "param1": 10,
            "param2": 0.5,
        }
        self.params = {**default_params, **(params or {})}
        self.name = "My Custom Strategy"
        self.description = "自定义策略描述"

    def get_required_indicators(self) -> List[str]:
        return ["MA", "MACD", "RSI"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        if df.empty:
            return StrategyResult(
                action="hold", score=0,
                reasons=["数据不足"],
                confidence=0.0, metadata={}
            )

        latest = df.iloc[-1]
        score = 0
        reasons = []

        # 你的策略逻辑
        if latest["MA5"] > latest["MA20"]:
            score += 50
            reasons.append("多头排列")

        if latest["RSI"] < 30:
            score += 30
            reasons.append("RSI超卖")

        # 买入判断
        if score >= 60:
            return StrategyResult(
                action="buy",
                score=score,
                reasons=reasons,
                confidence=score/100,
                metadata={"ma5": latest["MA5"]}
            )

        # 卖出判断
        if latest["RSI"] > 70:
            return StrategyResult(
                action="sell",
                score=80,
                reasons=["RSI超买"],
                confidence=0.8,
                metadata={}
            )

        return StrategyResult(
            action="hold", score=score,
            reasons=reasons, confidence=0.0, metadata={}
        )
```

#### 步骤2: 注册策略

```python
# core/strategies/__init__.py

from .my_custom_strategy import MyCustomStrategy

__all__ = [
    ...
    "MyCustomStrategy",
]
```

#### 步骤3: 测试策略

```python
# test_my_custom.py

from core.strategies import MyCustomStrategy
from core.backtest import BacktestEngine

strategy = MyCustomStrategy(params={"param1": 20})
engine = BacktestEngine()

result = engine.run(
    strategy=strategy,
    stock_pool=["000001"],
    start_date="20240101",
    end_date="20241231"
)

print(result)
```

### 添加新指标

```python
# core/indicators/custom_indicators.py

def calculate_my_indicator(df):
    """自定义指标"""
    df["MY_IND"] = df["close"].rolling(10).mean()
    return df

# 注册到工厂
from core.indicators import IndicatorFactory

IndicatorFactory.register("MY_IND", calculate_my_indicator)

# 使用
df = IndicatorFactory.calculate(df, "MY_IND")
```

### 自定义风控规则

```python
# 创建自定义风控管理器
class MyRiskManager(RiskManager):
    def check_stop_loss(self, position):
        # 自定义止损逻辑
        if position.current_price < position.entry_price * 0.85:
            return True, position.shares, "自定义止损-15%"
        return False, 0, ""

# 使用自定义风控
engine = BacktestEngine(risk_manager=MyRiskManager(config))
```

---

## 性能优化

### 数据缓存

```python
# 自动缓存历史数据
dm = DataManager()
df = dm.get_data("000001", mode="historical",
                 start_date="20240101",
                 end_date="20241231",
                 use_cache=True)  # 启用缓存

# 缓存位置
# data/cache/stock_hist_000001_20240101_20241231_qfq.pkl
```

### 并行回测

```python
from concurrent.futures import ProcessPoolExecutor

def backtest_single(args):
    strategy, stock_pool, start, end = args
    engine = BacktestEngine()
    return engine.run(strategy, stock_pool, start, end)

# 并行测试多个策略
strategies = [Strategy1(), Strategy2(), Strategy3()]
args_list = [(s, pool, start, end) for s in strategies]

with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(backtest_single, args_list))
```

---

## 常见问题

### Q1: 原有 main.py 还能用吗？

**A**: 能！原有系统完全保留，`main.py` 和 `ui/app.py` 正常运行。新架构是增量式的，不影响原有功能。

### Q2: 如何在原有系统中使用新策略？

**A**: 可以通过 StrategyManager 桥接：

```python
# 在 main.py 中使用新策略
from core.strategies import StrategyManager, MACrossoverStrategy

manager = StrategyManager()
manager.register_strategy("ma_cross", MACrossoverStrategy())

# 生成信号
result = manager.run_strategy("ma_cross", code="000001")
if result.action == "buy":
    print(f"买入信号: {result.reasons}")
```

### Q3: 如何对比不同参数的策略？

**A**: 创建多个实例：

```python
strategies = {
    "MA(5,20)": MACrossoverStrategy({"short_window": 5, "long_window": 20}),
    "MA(10,30)": MACrossoverStrategy({"short_window": 10, "long_window": 30}),
    "MA(20,60)": MACrossoverStrategy({"short_window": 20, "long_window": 60}),
}

for name, strategy in strategies.items():
    result = engine.run(strategy, ...)
    print(f"{name}: {result.total_return}%")
```

### Q4: 如何在生产环境使用？

**A**: 推荐流程：

1. **离线回测** - 使用历史数据验证策略
2. **参数优化** - 调整策略参数
3. **实盘模拟** - 使用最新数据生成信号（不实际交易）
4. **小资金实盘** - 验证策略在真实市场的表现
5. **扩大规模** - 确认稳定后增加资金

```python
# 实盘信号生成
from core.strategies import StrategyManager

manager = StrategyManager()
manager.register_strategy("my_prod", MyStrategy())

# 每天定时运行
result = manager.run_strategy("my_prod", code="000001", mode="realtime")

if result.action == "buy" and result.confidence > 0.7:
    print(f"高置信度买入信号: {result.reasons}")
    # 发送通知 / 执行交易
```

---

## 路线图

### ✅ 已完成

- [x] Phase 1: 数据层 + 指标层 + 策略层
- [x] Phase 2: 回测引擎 + 风控系统
- [x] 7种策略实现
- [x] 策略集成机制
- [x] 完整测试覆盖

### 🚧 进行中

- [ ] Phase 3A: 实盘信号生成模块
- [ ] Phase 3B: REST API + WebSocket
- [ ] Phase 3C: 策略优化模块

### 📅 计划中

- [ ] 参数优化（网格搜索、遗传算法）
- [ ] Walk-forward 分析
- [ ] Monte Carlo 模拟
- [ ] 实时推送系统
- [ ] 前端可视化增强

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **数据获取** | AKShare, pandas |
| **数据存储** | Pickle缓存, JSON |
| **指标计算** | pandas, numpy |
| **策略框架** | Python ABC, dataclass |
| **回测引擎** | 自研 (策略无关设计) |
| **Web界面** | Streamlit |
| **测试** | pytest (计划) |
| **部署** | Conda环境 |

---

## 贡献指南

### 代码规范

- 遵循 PEP 8
- 类型注解（Type Hints）
- Docstring（Google风格）
- 单元测试覆盖

### 提交规范

```bash
# feat: 新功能
git commit -m "feat: 添加XXX策略"

# fix: 修复bug
git commit -m "fix: 修复回测引擎的XXX问题"

# docs: 文档
git commit -m "docs: 更新架构文档"

# test: 测试
git commit -m "test: 添加策略单元测试"
```

---

## 联系方式

- Issue: [GitHub Issues]
- Email: [你的邮箱]
- 文档: `docs/`

---

**最后更新**: 2024-01-28
**版本**: v2.0 (Phase 1 + Phase 2 完成)
