# Jesse 项目技术分析文档

## 1. 项目概述

**项目名称**: Jesse
**GitHub**: https://github.com/jesse-ai/jesse
**主要语言**: Python
**许可证**: MIT

Jesse 是一个**加密货币交易框架**，专为量化交易设计，支持回测、实盘交易和策略优化。定位为"更准确、更简单"的交易框架。

---

## 2. 项目结构

```
jesse/
├── jesse/                      # 核心框架代码
│   ├── strategies/             # 策略目录 (139+ 策略)
│   ├── indicators/            # 技术指标库 (175+ 指标)
│   ├── models/                # 数据模型 (22个)
│   ├── services/             # 核心服务
│   ├── modes/                # 运行模式
│   ├── exchanges/            # 交易所集成
│   ├── repositories/         # 数据持久化
│   ├── store/                # 状态管理
│   └── routes/               # 路由配置
├── tests/                     # 测试套件
└── modes/                     # 运行模式 (backtest, optimize, live)
```

---

## 3. 核心功能模块

### 3.1 策略系统 (`jesse/strategies/`)
```python
class Strategy:
    def should_long(self): pass      # 判断是否开多
    def go_long(self): pass          # 执行开多
    def should_short(self): pass     # 判断是否开空
    def go_short(self): pass         # 执行开空
    def on_open_position(self): pass  # 开仓回调
    def on_close_position(self): pass # 平仓回调
```

### 3.2 技术指标库 (175+ 指标)
- 移动平均线: EMA, SMA, WMA, ALMA
- 动量指标: RSI, MACD, Stochastic
- 趋势指标: ADX, Aroon, Ichimoku
- 波动率指标: ATR, Bollinger Bands

### 3.3 运行模式
- **backtest_mode** - 回测模式
- **optimize_mode** - 参数优化 (使用 Optuna)
- **monte_carlo_mode** - 蒙特卡洛模拟

### 3.4 核心服务
- **order_service.py** - 订单服务
- **candle_service.py** - K线服务
- **broker.py** - 经纪商服务
- **metrics.py** - 性能指标计算

---

## 4. 技术架构

### 4.1 核心技术栈
```python
numpy~=1.26.4          # 数值计算
pandas~=2.2.3          # 数据处理
numba~=0.61.0          # JIT 编译加速
optuna~=4.2.0          # 超参数优化
fastapi~=0.111.1       # Web API
redis~=4.1.4           # 缓存
jesse-rust==1.0.1      # Rust 加速核心
```

### 4.2 性能优化
- **Rust (jesse_rust)**: 核心计算使用 Rust 加速
- **Numba JIT**: 数值计算使用 Numba 加速

### 4.3 状态管理
```python
store.app          # 应用状态
store.orders      # 订单状态
store.positions   # 持仓状态
store.candles     # K线数据
store.exchanges   # 交易所状态
```

---

## 5. 策略实现方式

### 5.1 策略基类设计
```python
class Strategy(ABC):
    # 订单管理
    self.buy = (qty, price)         # 买入订单
    self.sell = (qty, price)        # 卖出订单
    self.stop_loss = (qty, price)   # 止损
    self.take_profit = (qty, price) # 止盈

    # 持仓信息
    self.position    # 当前持仓
    self.trade       # 当前交易
```

### 5.2 超参数系统
```python
def hyperparameters(self):
    return [
        {'name': 'slow_sma_period', 'type': int, 'min': 150, 'max': 210},
        {'name': 'fast_sma_period', 'type': int, 'min': 20, 'max': 100},
    ]
```

---

## 6. 数据流

```
1. 加载配置 (config.py)
   ↓
2. 初始化交易所和路由
   ↓
3. 加载历史K线数据
   ↓
4. 遍历每个时间点:
   a. 更新K线数据
   b. 调用策略的 should_long/should_short
   c. 执行 go_long/go_short
   d. 处理订单 (撮合)
   e. 更新持仓和账户
   ↓
5. 计算性能指标
```

---

## 7. 技术特点

| 特点 | 说明 |
|------|------|
| **高性能** | Rust + Numba 加速指标计算 |
| **丰富指标** | 175+ 技术指标内置 |
| **多模式** | 回测/优化/实盘/蒙特卡洛 |
| **简洁语法** | 策略代码简单直观 |
| **参数优化** | 内置 Optuna 优化支持 |
| **实时交易** | WebSocket 实时数据推送 |
| **多交易所** | 支持主流加密货币交易所 |
| **风控内置** | 自动止损止盈 |

---

## 8. 可借鉴的设计

1. **策略基类设计** - 清晰的 should_long/go_long 分离
2. **指标库** - 内置丰富指标，开箱即用
3. **状态管理 (Store 模式)** - 统一的状态管理
4. **超参数系统** - 内置参数优化支持
5. **性能优化** - Rust/Numba 加速

---

*文档生成时间: 2026-02-21*
