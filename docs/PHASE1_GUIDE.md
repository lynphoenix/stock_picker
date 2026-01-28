# Phase 1: 基础设施重构 - 使用指南

## 概述

Phase 1 完成了系统的基础架构重构，实现了三个核心模块：

1. **DataManager** - 统一数据管理接口
2. **IndicatorFactory** - 指标计算工厂
3. **StrategyManager** - 策略管理系统

## 目录结构

```
core/
├── __init__.py
├── data/                      # 数据层
│   ├── __init__.py
│   ├── data_manager.py        # 数据管理器
│   ├── providers.py           # 数据提供者(历史/实时)
│   └── cache_manager.py       # 缓存管理器
│
├── indicators/                # 指标层
│   ├── __init__.py
│   ├── factory.py             # 指标工厂
│   ├── technical.py           # 技术指标
│   └── fundamental.py         # 基本面指标
│
└── strategies/                # 策略层
    ├── __init__.py
    ├── strategy_base.py       # 策略基类
    ├── strategy_manager.py    # 策略管理器
    ├── macd_rsi_strategy.py   # MACD+RSI策略
    └── fundamental_strategy.py # 基本面策略
```

---

## 1. DataManager 使用

### 基本用法

```python
from core.data import DataManager

dm = DataManager()

# 获取实时数据(最新+最近120天)
df = dm.get_data("000001", mode="realtime")

# 获取历史数据(指定时间范围)
df = dm.get_data(
    "000001",
    mode="historical",
    start_date="20250101",
    end_date="20251231"
)

# 智能模式(优先实时，失败则用历史)
df = dm.get_data("000001", mode="latest")
```

### 添加指标

```python
# 为数据添加技术指标
df = dm.add_indicators(df, ["MA", "MACD", "RSI"])

# 查看添加的指标列
print(df.columns)
# ['date', 'open', 'high', 'low', 'close', 'volume',
#  'MA5', 'MA20', 'MA60', 'MACD_DIF', 'MACD_DEA', 'MACD', 'RSI', ...]
```

### 批量获取数据

```python
# 批量获取多只股票的数据
codes = ["000001", "000002", "600036"]
data_dict = dm.get_batch_data(codes, mode="realtime")

for code, df in data_dict.items():
    print(f"{code}: {len(df)} 行数据")
```

### 数据模式对比

| 模式 | 适用场景 | 数据范围 | 缓存时间 |
|------|---------|---------|---------|
| realtime | 实盘交易 | 最近120天 | 5分钟 |
| historical | 回测 | 指定范围 | 2小时 |
| latest | 通用 | 自动选择 | 动态 |

---

## 2. IndicatorFactory 使用

### 查看可用指标

```python
from core.indicators import IndicatorFactory

# 列出所有指标
indicators = IndicatorFactory.list_indicators()
print(indicators)
# ['MA', 'MACD', 'RSI', 'BOLL', 'KDJ', 'VOLUME', 'ALL_TECHNICAL', ...]
```

### 计算单个指标

```python
import pandas as pd

# 假设已有DataFrame
df = pd.DataFrame(...)

# 计算MACD
df = IndicatorFactory.calculate(df, "MACD")

# 计算RSI
df = IndicatorFactory.calculate(df, "RSI")
```

### 批量计算指标

```python
# 一次性计算多个指标
df = IndicatorFactory.calculate_multiple(df, ["MA", "MACD", "RSI"])

# 或者使用ALL_TECHNICAL一次性计算所有技术指标
df = IndicatorFactory.calculate(df, "ALL_TECHNICAL")
```

### 注册自定义指标

```python
def my_custom_indicator(df):
    """自定义指标: 10日动量"""
    df['MOMENTUM_10'] = df['close'].diff(10)
    return df

# 注册
IndicatorFactory.register_custom('MOMENTUM', my_custom_indicator)

# 使用
df = IndicatorFactory.calculate(df, 'MOMENTUM')
```

---

## 3. StrategyManager 使用

### 基本用法

```python
from core.strategies import StrategyManager

manager = StrategyManager()

# 列出所有策略
strategies = manager.list_strategies()
print(strategies)
# ['MACD_RSI', 'Fundamental']

# 查看策略信息
info = manager.get_strategy_info('MACD_RSI')
print(info)
# {
#   'name': 'MACD_RSI',
#   'version': '1.0',
#   'required_indicators': ['MACD', 'RSI', 'MA', 'VOLUME'],
#   'params': {'macd_weight': 30, 'rsi_weight': 15, ...}
# }
```

### 运行策略

```python
# 对单只股票运行策略
result = manager.run_strategy("MACD_RSI", "000001", mode="realtime")

print(f"动作: {result.action}")          # buy | sell | hold
print(f"评分: {result.score}")            # 0-100
print(f"原因: {result.reasons}")          # ['MACD金叉', 'RSI超卖']
print(f"置信度: {result.confidence}")     # 0.0-1.0
print(f"元数据: {result.metadata}")       # 额外信息
```

### 批量运行

```python
# 批量运行策略
codes = ["000001", "000002", "600036"]
results = manager.batch_run("MACD_RSI", codes, mode="realtime")

# 筛选买入信号
buy_signals = [
    (code, result)
    for code, result in results.items()
    if result.action == "buy"
]

for code, result in buy_signals:
    print(f"{code}: {result.score:.1f}分 - {', '.join(result.reasons)}")
```

### 自定义策略参数

```python
from core.strategies import MACDRSIStrategy

# 创建自定义参数的策略
custom_strategy = MACDRSIStrategy(params={
    "buy_threshold": 60,      # 提高买入阈值
    "sell_threshold": 70,     # 提高卖出阈值
    "rsi_oversold": 25,       # 更严格的超卖条件
    "macd_weight": 40,        # 增加MACD权重
})

# 注册到管理器
manager.register(custom_strategy)

# 使用
result = manager.run_strategy("MACD_RSI", "000001")
```

---

## 4. 策略结果对象

```python
@dataclass
class StrategyResult:
    action: str           # "buy" | "sell" | "hold"
    score: float          # 信号强度 0-100
    reasons: List[str]    # 信号原因列表
    confidence: float     # 置信度 0.0-1.0
    metadata: Dict        # 额外信息
```

### 示例输出

```python
StrategyResult(
    action="buy",
    score=75.0,
    reasons=["MACD金叉", "RSI超卖(28.5)", "均线多头"],
    confidence=0.75,
    metadata={
        "buy_score": 75.0,
        "sell_score": 0.0,
        "rsi": 28.5,
        "macd": 0.15
    }
)
```

---

## 5. 完整示例

### 实盘选股示例

```python
from core.strategies import StrategyManager
from core.data import DataManager

def scan_stock_pool(pool_codes, strategy_name="MACD_RSI"):
    """扫描股票池生成交易信号"""

    manager = StrategyManager()

    # 批量运行策略
    results = manager.batch_run(strategy_name, pool_codes)

    # 筛选买入信号(评分>60)
    buy_signals = []
    for code, result in results.items():
        if result.action == "buy" and result.score >= 60:
            buy_signals.append({
                "code": code,
                "score": result.score,
                "reasons": result.reasons,
                "confidence": result.confidence
            })

    # 按评分排序
    buy_signals.sort(key=lambda x: x["score"], reverse=True)

    return buy_signals

# 使用
pool = ["000001", "000002", "600036", "600519"]
signals = scan_stock_pool(pool)

for signal in signals:
    print(f"{signal['code']}: {signal['score']:.1f}分")
    print(f"  原因: {', '.join(signal['reasons'])}")
```

### 回测准备示例

```python
from core.strategies import MACDRSIStrategy
from core.data import DataManager

def prepare_backtest_data(stock_pool, start_date, end_date):
    """为回测准备数据"""

    dm = DataManager()
    strategy = MACDRSIStrategy()

    data_dict = {}

    for code in stock_pool:
        # 获取历史数据
        df = dm.get_data(
            code,
            mode="historical",
            start_date=start_date,
            end_date=end_date
        )

        if not df.empty:
            # 添加策略需要的指标
            indicators = strategy.get_required_indicators()
            df = dm.add_indicators(df, indicators)
            data_dict[code] = df

    return data_dict

# 使用
data = prepare_backtest_data(
    stock_pool=["000001", "000002"],
    start_date="20250101",
    end_date="20251231"
)
```

---

## 6. 与旧代码的兼容性

Phase 1 完全向后兼容，旧代码可以继续使用：

```python
# 旧方式 (仍然有效)
from src.data_fetcher import DataFetcher
from src.signal_engine import SignalEngine

fetcher = DataFetcher()
df = fetcher.get_stock_history("000001")

engine = SignalEngine()
result = engine.analyze_stock("000001", "平安银行")

# 新方式 (推荐)
from core.data import DataManager
from core.strategies import StrategyManager

dm = DataManager()
df = dm.get_data("000001", mode="realtime")

manager = StrategyManager()
result = manager.run_strategy("MACD_RSI", "000001")
```

---

## 7. 运行测试

```bash
# 运行Phase 1功能测试
python test_phase1.py
```

测试内容：
- ✅ DataManager 数据获取
- ✅ IndicatorFactory 指标计算
- ✅ StrategyManager 策略运行
- ✅ 自定义策略参数

---

## 8. 下一步：Phase 2

Phase 2 将实现：
- BacktestEngine (策略无关回测引擎)
- Portfolio (组合管理)
- RiskManager (风险控制)
- SignalGenerator (实盘信号生成)

届时可以：
```python
# Phase 2 预览
from core.backtest import BacktestEngine
from core.strategies import MACDRSIStrategy

strategy = MACDRSIStrategy()
engine = BacktestEngine(initial_capital=100000)

result = engine.run(
    strategy=strategy,
    stock_pool=["000001", "000002"],
    start_date="20250101",
    end_date="20251231"
)

print(f"总收益: {result.total_return:.2f}%")
print(f"胜率: {result.win_rate:.2f}%")
```

---

## 常见问题

### Q1: 如何切换数据源？

```python
# 目前使用AKShare，未来可以切换
# 只需修改 core/data/providers.py 中的实现
# 策略层和业务层代码无需改动
```

### Q2: 策略评分标准是什么？

```python
# MACD_RSI策略评分:
# 买入: MACD金叉(30) + RSI未超买(15) + 均线多头(20) + 成交量(15) + 支撑(10)
# 卖出: MACD死叉(30) + RSI超买(35) + 跌破均线(20)
# 阈值: 买入≥50, 卖出≥60
```

### Q3: 如何添加新策略？

```python
from core.strategies import Strategy, StrategyResult

class MyStrategy(Strategy):
    def __init__(self):
        super().__init__("MyStrategy", {"param1": 10})

    def get_required_indicators(self):
        return ["MA", "MACD"]

    def generate_signals(self, df):
        # 实现策略逻辑
        return StrategyResult(
            action="buy",
            score=80,
            reasons=["自定义原因"],
            confidence=0.8
        )

# 注册
manager = StrategyManager()
manager.register(MyStrategy())
```

---

## 总结

Phase 1 完成了核心基础设施的重构：

✅ **统一数据接口** - 历史/实时数据透明切换
✅ **指标工厂模式** - 指标计算标准化
✅ **策略框架** - 策略可插拔、可配置
✅ **向后兼容** - 不影响现有代码

现在可以：
- 用统一接口获取数据
- 动态添加技术指标
- 灵活运行和切换策略
- 自定义策略参数

下一步将在此基础上构建回测引擎和交易信号系统。
