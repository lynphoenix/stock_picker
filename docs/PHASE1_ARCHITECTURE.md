# Phase 1 架构设计文档

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Phase 1: 基础设施层                        │
└─────────────────────────────────────────────────────────────┘

┌────────────────────┐
│  StrategyManager   │  策略管理与执行
│  • 策略注册        │
│  • 策略执行        │
│  • 批量运行        │
└────────┬───────────┘
         │ 使用
         ↓
┌────────────────────┐         ┌────────────────────┐
│   DataManager      │────────→│  IndicatorFactory  │
│  • 统一数据接口     │  添加    │  • 指标计算        │
│  • 历史/实时切换   │  指标    │  • 动态注册        │
│  • 批量获取        │         │  • 自定义扩展      │
└────────┬───────────┘         └────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│           Data Providers                │
├─────────────────┬───────────────────────┤
│ Historical      │ Realtime              │
│ • 指定时间范围   │ • 最新+近120天        │
│ • 用于回测      │ • 用于实盘            │
│ • 长缓存(2h)    │ • 短缓存(5min)        │
└─────────────────┴───────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│         CacheManager                    │
│  • 统一缓存管理                          │
│  • TTL过期机制                          │
│  • 缓存清理                             │
└─────────────────────────────────────────┘
         │
         ↓
┌─────────────────────────────────────────┐
│         AKShare API                     │
│  • 东方财富数据源                        │
└─────────────────────────────────────────┘
```

---

## 核心模块详解

### 1. DataManager (数据管理器)

**职责:**
- 提供统一的数据访问接口
- 屏蔽历史数据和实时数据的差异
- 集成指标计算

**关键方法:**
```python
get_data(code, mode, start_date, end_date)
  ├─ mode="realtime"    → RealtimeDataProvider
  ├─ mode="historical"  → HistoricalDataProvider
  └─ mode="latest"      → 智能选择

add_indicators(df, indicators)
  └─ 调用 IndicatorFactory 添加指标

get_batch_data(codes, mode)
  └─ 批量获取多只股票数据
```

**数据流:**
```
用户请求
  ↓
DataManager.get_data(code, mode)
  ↓
[选择Provider]
  ├─ Historical: 指定范围 + 2小时缓存
  └─ Realtime: 近120天 + 5分钟缓存
  ↓
[检查缓存]
  ├─ Hit: 返回缓存数据
  └─ Miss: 调用AKShare API
  ↓
[保存缓存] → 返回DataFrame
```

---

### 2. Data Providers (数据提供者)

#### HistoricalDataProvider
- **用途:** 回测系统
- **数据范围:** 用户指定的 start_date ~ end_date
- **缓存策略:** 2小时 TTL（历史数据不变）
- **性能:** 适合大批量预加载

#### RealtimeDataProvider
- **用途:** 实盘交易
- **数据范围:** 最近 120 天（足够计算所有技术指标）
- **缓存策略:** 5分钟 TTL（数据实时性要求）
- **性能:** 快速响应最新行情

**对比:**

| 特性 | Historical | Realtime |
|------|-----------|----------|
| 数据范围 | 自定义 | 固定120天 |
| 缓存时长 | 2小时 | 5分钟 |
| 适用场景 | 回测 | 实盘 |
| 数据稳定性 | 高 | 中 |

---

### 3. CacheManager (缓存管理器)

**职责:**
- 统一缓存管理
- TTL过期机制
- 缓存清理

**存储格式:**
```python
{
    "data": <actual_data>,
    "timestamp": datetime.now(),
    "metadata": {
        "code": "000001",
        "start_date": "20250101",
        ...
    }
}
```

**缓存键生成:**
```python
# 历史数据
cache_key = f"hist_{code}_{start_date}_{end_date}"

# 实时数据
cache_key = f"realtime_{code}_{today}"
```

---

### 4. IndicatorFactory (指标工厂)

**职责:**
- 统一指标计算接口
- 支持动态注册新指标
- 指标复用和扩展

**内置指标:**
- **MA**: 移动平均线 (5, 10, 20, 60日)
- **MACD**: 指数平滑移动平均 (DIF, DEA, MACD柱)
- **RSI**: 相对强弱指标
- **BOLL**: 布林带
- **KDJ**: 随机指标
- **VOLUME**: 成交量指标

**使用模式:**
```python
# 单个指标
df = IndicatorFactory.calculate(df, "MACD")

# 多个指标
df = IndicatorFactory.calculate_multiple(df, ["MA", "RSI"])

# 所有技术指标
df = IndicatorFactory.calculate(df, "ALL_TECHNICAL")

# 自定义指标
IndicatorFactory.register_custom("MY_IND", my_calculator)
```

---

### 5. Strategy Framework (策略框架)

#### Strategy 基类

**抽象方法:**
```python
class Strategy(ABC):
    @abstractmethod
    def get_required_indicators(self) -> List[str]:
        """返回策略需要的指标"""
        pass

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """生成交易信号"""
        pass
```

**生命周期:**
```
初始化
  ↓
设置参数 (params)
  ↓
声明需要的指标 (get_required_indicators)
  ↓
数据准备 (DataManager自动添加指标)
  ↓
生成信号 (generate_signals)
  ↓
返回结果 (StrategyResult)
```

#### StrategyResult (策略结果)

**数据结构:**
```python
@dataclass
class StrategyResult:
    action: str          # "buy" | "sell" | "hold"
    score: float         # 0-100 信号强度
    reasons: List[str]   # 信号原因
    confidence: float    # 0.0-1.0 置信度
    metadata: Dict       # 额外信息
```

**示例:**
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

### 6. StrategyManager (策略管理器)

**职责:**
- 策略注册与管理
- 策略执行协调
- 数据准备与指标添加

**工作流:**
```
用户调用 run_strategy(strategy_name, code, mode)
  ↓
[1] 获取策略对象
  └─ strategy = get_strategy(strategy_name)
  ↓
[2] 获取数据
  └─ df = DataManager.get_data(code, mode)
  ↓
[3] 添加指标
  └─ indicators = strategy.get_required_indicators()
  └─ df = DataManager.add_indicators(df, indicators)
  ↓
[4] 生成信号
  └─ result = strategy.generate_signals(df)
  ↓
[5] 返回结果
  └─ StrategyResult
```

**批量运行优化:**
```python
batch_run(strategy_name, codes, mode)
  ↓
[并行获取数据]
  ├─ code1 → DataProvider
  ├─ code2 → DataProvider
  └─ code3 → DataProvider
  ↓
[串行执行策略]
  └─ 避免并发导致的资源竞争
```

---

## 内置策略

### MACDRSIStrategy (MACD + RSI 组合策略)

**信号评分机制:**

**买入信号 (满分90):**
- MACD金叉: 30分
- RSI超卖/偏低: 15分
- 均线多头: 20分
- 成交量放大: 15分
- 价格接近支撑: 10分

**卖出信号 (满分75):**
- MACD死叉: 30分
- RSI超买: 35分
- 跌破均线: 20分

**决策规则:**
```python
if sell_score >= 60:
    action = "sell"
elif buy_score >= 50:
    action = "buy"
else:
    action = "hold"
```

**可配置参数:**
```python
{
    "macd_weight": 30,
    "rsi_weight": 15,
    "ma_weight": 20,
    "volume_weight": 15,
    "support_weight": 10,
    "rsi_oversold": 30,
    "rsi_overbought": 70,
    "buy_threshold": 50,
    "sell_threshold": 60,
}
```

---

## 数据流示例

### 实盘选股流程

```
用户: scan_stocks(["000001", "000002"], "MACD_RSI")
  ↓
StrategyManager.batch_run()
  ↓
对每只股票:
  ├─ DataManager.get_data(code, mode="realtime")
  │   ↓
  │   RealtimeDataProvider.fetch()
  │   ↓
  │   [检查5分钟缓存]
  │   ↓
  │   AKShare API (如果缓存miss)
  │   ↓
  │   返回最近120天数据
  │
  ├─ DataManager.add_indicators(df, ["MACD", "RSI", "MA"])
  │   ↓
  │   IndicatorFactory.calculate(df, "MACD")
  │   IndicatorFactory.calculate(df, "RSI")
  │   IndicatorFactory.calculate(df, "MA")
  │
  └─ MACDRSIStrategy.generate_signals(df)
      ↓
      计算买入/卖出评分
      ↓
      返回 StrategyResult
  ↓
返回: {code: StrategyResult} 字典
```

### 回测准备流程

```
用户: prepare_backtest(codes, start, end)
  ↓
DataManager.get_batch_data(codes, mode="historical")
  ↓
对每只股票:
  ├─ HistoricalDataProvider.fetch(code, start, end)
  │   ↓
  │   [检查2小时缓存]
  │   ↓
  │   AKShare API (如果缓存miss)
  │   ↓
  │   返回指定时间范围数据
  │
  └─ DataManager.add_indicators(df, strategy.get_required_indicators())
      ↓
      返回带指标的DataFrame
  ↓
返回: {code: DataFrame} 字典
```

---

## 设计模式

### 1. 策略模式 (Strategy Pattern)

```python
# 策略接口
class Strategy(ABC):
    @abstractmethod
    def generate_signals(self, df): pass

# 具体策略
class MACDRSIStrategy(Strategy):
    def generate_signals(self, df):
        # 实现具体逻辑
        pass

# 上下文
class StrategyManager:
    def run_strategy(self, strategy_name, code):
        strategy = self.get_strategy(strategy_name)
        return strategy.generate_signals(df)
```

**优势:**
- 策略可插拔
- 易于扩展新策略
- 策略可独立测试

### 2. 工厂模式 (Factory Pattern)

```python
class IndicatorFactory:
    _indicators = {
        "MACD": calculate_macd,
        "RSI": calculate_rsi,
        ...
    }

    @classmethod
    def calculate(cls, df, indicator):
        calculator = cls._indicators[indicator]
        return calculator(df)
```

**优势:**
- 统一创建接口
- 支持动态注册
- 便于管理和扩展

### 3. 代理模式 (Proxy Pattern)

```python
class CacheManager:
    def get(self, key, ttl):
        # 检查缓存
        if cached and not expired:
            return cached_data
        # 否则从真实源获取
        return fetch_from_source()
```

**优势:**
- 透明缓存
- 减少API调用
- 提升性能

---

## 性能优化

### 1. 缓存策略

```
历史数据: 2小时TTL
  └─ 历史数据不变，可以长时间缓存

实时数据: 5分钟TTL
  └─ 平衡实时性和性能

指标计算: 不缓存
  └─ 计算快，内存占用小
```

### 2. 批量处理

```python
# 批量获取数据（共享缓存检查）
data_dict = dm.get_batch_data(codes)

# 批量运行策略（避免重复数据加载）
results = manager.batch_run(strategy_name, codes)
```

### 3. 惰性加载

```python
# 只在需要时才计算指标
indicators = strategy.get_required_indicators()
df = dm.add_indicators(df, indicators)  # 按需计算
```

---

## 扩展性

### 添加新策略

```python
from core.strategies import Strategy, StrategyResult

class MyCustomStrategy(Strategy):
    def __init__(self):
        super().__init__("MyStrategy", {"threshold": 50})

    def get_required_indicators(self):
        return ["MA", "BOLL"]

    def generate_signals(self, df):
        # 实现策略逻辑
        return StrategyResult(...)

# 注册
manager = StrategyManager()
manager.register(MyCustomStrategy())
```

### 添加新指标

```python
def my_indicator(df):
    df['MY_IND'] = df['close'].rolling(20).std()
    return df

# 注册
IndicatorFactory.register_custom('MY_IND', my_indicator)

# 使用
df = IndicatorFactory.calculate(df, 'MY_IND')
```

### 切换数据源

```python
# 修改 core/data/providers.py
class AlternativeDataProvider(BaseDataProvider):
    def fetch(self, code, **kwargs):
        # 使用其他数据源（如tushare, wind等）
        return alternative_api.get_data(code)

# 修改 DataManager
self.realtime = AlternativeDataProvider()
```

---

## 向后兼容

Phase 1 完全不影响现有代码：

```python
# 旧代码继续工作
from src.data_fetcher import DataFetcher
from src.signal_engine import SignalEngine

# 新代码使用新接口
from core.data import DataManager
from core.strategies import StrategyManager
```

两套系统可以并行运行，逐步迁移。

---

## 测试覆盖

```python
test_phase1.py
├─ test_data_manager()
│  ├─ 测试获取实时数据
│  ├─ 测试获取历史数据
│  └─ 测试添加指标
│
├─ test_indicator_factory()
│  ├─ 测试列出指标
│  ├─ 测试计算单个指标
│  └─ 测试批量计算
│
├─ test_strategy_manager()
│  ├─ 测试列出策略
│  ├─ 测试运行单个策略
│  └─ 测试批量运行
│
└─ test_custom_strategy()
   └─ 测试自定义参数
```

---

## 下一步: Phase 2

Phase 2 将基于 Phase 1 构建：

```
Phase 2 模块:
├─ BacktestEngine
│  └─ 使用 Strategy + DataManager
│
├─ Portfolio
│  └─ 组合管理（买入/卖出/持仓）
│
├─ RiskManager
│  └─ 风险控制（止损/仓位）
│
└─ SignalGenerator
   └─ 实盘信号生成（使用 StrategyManager）
```

**关键特性:**
- 策略和回测引擎完全解耦
- 同一个策略可用于回测和实盘
- 统一的数据接口和指标计算

---

## 总结

Phase 1 完成了核心基础设施：

✅ **统一数据接口** - DataManager
✅ **指标工厂** - IndicatorFactory
✅ **策略框架** - Strategy + StrategyManager
✅ **缓存管理** - CacheManager
✅ **向后兼容** - 不影响现有代码

**核心优势:**
1. **可扩展** - 策略、指标可插拔
2. **可配置** - 参数化策略
3. **可复用** - 回测和实盘共用逻辑
4. **高性能** - 智能缓存策略
5. **易测试** - 模块独立，职责清晰

现在可以基于此构建更高级的功能（回测、实盘、组合管理等）。
