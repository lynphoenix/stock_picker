# 快速开始指南

## 🚀 5分钟上手

### 1. 环境准备

```bash
# 激活环境
conda activate stock_picker

# 验证安装
python -c "import akshare, pandas; print('✓ 环境就绪')"
```

### 2. 运行原有系统

```bash
# Web界面（推荐）
streamlit run ui/app.py

# 命令行模式
python main.py
```

### 3. 使用新架构

#### 单策略回测

```python
from core.strategies import MACrossoverStrategy
from core.backtest import BacktestEngine

# 创建策略
strategy = MACrossoverStrategy()

# 创建回测引擎
engine = BacktestEngine(initial_capital=100000)

# 运行回测
result = engine.run(
    strategy=strategy,
    stock_pool=["000001", "000002"],
    start_date="20240101",
    end_date="20241231"
)

# 查看结果
print(f"收益率: {result.total_return}%")
print(f"胜率: {result.win_rate}%")
```

#### 策略对比

```bash
# 运行多策略对比测试
python test_multi_strategies.py

# 原有策略 vs 新策略对比
python test_original_vs_new.py
```

---

## 📚 核心概念

### Strategy - 策略

所有策略继承自 `Strategy` 基类，实现两个方法：

```python
class MyStrategy(Strategy):
    def get_required_indicators(self):
        return ["MA", "MACD", "RSI"]

    def generate_signals(self, df):
        # 返回 StrategyResult
        return StrategyResult(action="buy", score=80, ...)
```

### BacktestEngine - 回测引擎

策略无关的回测引擎，任何策略都能直接回测：

```python
engine = BacktestEngine(
    initial_capital=100000,
    risk_config={
        "max_positions": 3,      # 最多持有3只
        "position_size": 0.30,   # 每只30%资金
        "stop_loss": -0.10,      # -10%止损
        "trailing_stop": 0.04,   # 4%移动止损
    }
)
```

### StrategyResult - 信号结果

```python
@dataclass
class StrategyResult:
    action: str          # "buy" | "sell" | "hold"
    score: float         # 0-100
    reasons: List[str]   # ["MACD金叉", "RSI超卖"]
    confidence: float    # 0.0-1.0
    metadata: Dict       # 额外信息
```

---

## 🎯 常用策略

| 策略 | 适用场景 | 特点 | 导入 |
|------|---------|------|------|
| OriginalSignalStrategy | 震荡市 | 稳健，高胜率 | `from core.strategies import OriginalSignalStrategy` |
| MACrossoverStrategy | 趋势市 | 高收益，追踪趋势 | `from core.strategies import MACrossoverStrategy` |
| BollingerStrategy | 震荡市 | 均值回归 | `from core.strategies import BollingerStrategy` |
| MomentumStrategy | 牛市 | 追涨强势股 | `from core.strategies import MomentumStrategy` |
| MultiFactorStrategy | 全市场 | 多因子综合 | `from core.strategies import MultiFactorStrategy` |
| StrategyEnsemble | 通用 | 组合策略 | `from core.strategies import StrategyEnsemble` |

---

## 💡 典型用例

### 用例1: 对比不同均线周期

```python
from core.strategies import MACrossoverStrategy

strategies = {
    "MA(5,20)": MACrossoverStrategy({"short_window": 5, "long_window": 20}),
    "MA(10,30)": MACrossoverStrategy({"short_window": 10, "long_window": 30}),
    "MA(20,60)": MACrossoverStrategy({"short_window": 20, "long_window": 60}),
}

for name, strategy in strategies.items():
    result = engine.run(strategy, stock_pool, "20240101", "20241231")
    print(f"{name}: 收益{result.total_return:.2f}%, 回撤{result.max_drawdown:.2f}%")
```

### 用例2: 策略组合

```python
from core.strategies import StrategyEnsemble

ensemble = StrategyEnsemble(
    strategies=[
        (OriginalSignalStrategy(), 0.4),   # 40%权重
        (MACrossoverStrategy(), 0.3),      # 30%权重
        (BollingerStrategy(), 0.3),        # 30%权重
    ],
    voting_method="weighted"
)

result = engine.run(ensemble, stock_pool, "20240101", "20241231")
```

### 用例3: 实时信号生成

```python
from core.strategies import StrategyManager

manager = StrategyManager()
manager.register_strategy("my_strategy", MACrossoverStrategy())

# 获取最新信号
result = manager.run_strategy("my_strategy", code="000001", mode="realtime")

if result.action == "buy" and result.confidence > 0.7:
    print(f"强烈买入信号: {result.reasons}")
```

---

## 🔧 调试技巧

### 查看策略详细输出

```python
result = strategy.generate_signals(df)
print(f"动作: {result.action}")
print(f"评分: {result.score}")
print(f"原因: {result.reasons}")
print(f"置信度: {result.confidence}")
print(f"元数据: {result.metadata}")
```

### 查看回测交易记录

```python
result = engine.run(...)

for trade in result.trades:
    print(f"{trade.date} {trade.action} {trade.code} "
          f"{trade.shares}股 @{trade.price:.2f} - {trade.reason}")
```

### 使用缓存加速

```python
from core.data import DataManager

dm = DataManager()
df = dm.get_data("000001", mode="historical",
                 start_date="20240101", end_date="20241231",
                 use_cache=True)  # 使用缓存
```

---

## 📊 性能基准

基于2024年全年数据，股票池：000001, 000002, 600036

| 策略 | 收益率 | 胜率 | 最大回撤 | 交易次数 |
|------|--------|------|----------|----------|
| OriginalSignalStrategy | +3.78% | 80.0% | 1.64% | 5 |
| MACrossoverStrategy | +14.15% | 75.0% | 7.18% | 12 |
| BollingerStrategy | +8.55% | 76.9% | 6.60% | 13 |
| MomentumStrategy | +4.15% | 55.6% | 7.38% | 9 |
| MultiFactorStrategy | +8.03% | 57.1% | 6.52% | 7 |
| StrategyEnsemble | +12.55% | 76.9% | 4.93% | 13 |

---

## ❓ 常见问题

**Q: 如何添加新策略？**

A: 继承 `Strategy` 类，实现 `get_required_indicators()` 和 `generate_signals()` 方法。详见 [ARCHITECTURE.md](./ARCHITECTURE.md#策略开发指南)

**Q: 原有系统还能用吗？**

A: 完全可以！原有 `main.py` 和 `ui/app.py` 保持不变，新架构是增量式的。

**Q: 如何查看策略需要的指标？**

A: `strategy.get_required_indicators()` 返回指标列表，如 `["MA", "MACD", "RSI"]`

**Q: 如何调整风控参数？**

A: 在创建 `BacktestEngine` 时传入 `risk_config` 字典：

```python
engine = BacktestEngine(
    initial_capital=100000,
    risk_config={
        "max_positions": 5,       # 改为5只
        "stop_loss": -0.08,       # 改为-8%
        "take_profit_1": 0.10,    # 改为10%
    }
)
```

---

## 📖 更多文档

- [完整架构文档](./ARCHITECTURE.md)
- [Phase 1 指南](./PHASE1_GUIDE.md)
- [代码结构说明](./ARCHITECTURE.md#代码结构)

---

**Happy Trading! 🚀**
