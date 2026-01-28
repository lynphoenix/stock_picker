# A股智能选股系统 v2.0

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Status](https://img.shields.io/badge/Status-Production-green.svg)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()

一个**模块化、可扩展**的A股量化交易框架，支持多策略回测、风控管理和实时信号生成。

## ✨ 核心特性

- 🎯 **7+ 种交易策略** - 趋势跟踪、均值回归、动量、多因子、策略组合
- 🔄 **策略无关回测引擎** - 任何策略都能直接回测，无需修改回测代码
- 🛡️ **完整风控系统** - 止损、止盈、仓位管理、移动止损
- 📊 **历史数据管理** - 自动缓存、数据提供者模式
- 🔧 **原有逻辑保留** - 完整保留并增强原 SignalEngine
- 🚀 **易于扩展** - 新增策略只需继承基类，3步完成

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────┐
│            展示层 (UI)                           │
│   Streamlit界面  |  命令行工具                    │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│           应用层 (Application)                   │
│   SignalEngine  |  StrategyManager              │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│            策略层 (Strategy)                     │
│  原有策略 | 双均线 | 布林带 | 动量 | 多因子      │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│            回测层 (Backtest)                     │
│  BacktestEngine | Portfolio | RiskManager       │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│            指标层 (Indicators)                   │
│  IndicatorFactory | TechnicalIndicators         │
└─────────────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────┐
│             数据层 (Data)                        │
│  DataManager | CacheManager | DataFetcher       │
└─────────────────────────────────────────────────┘
```

完整架构说明：[ARCHITECTURE.md](./docs/ARCHITECTURE.md)

## 🚀 快速开始

### 安装依赖

```bash
# 克隆项目
git clone <repo>
cd stock_picker

# 创建环境
conda create -n stock_picker python=3.10
conda activate stock_picker

# 安装依赖
pip install -r requirements.txt
```

### 运行原有系统

```bash
# Web界面（推荐）
streamlit run ui/app.py

# 命令行模式
python main.py

# 更新股票池
python main.py --update-pools
```

### 使用新架构

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
    stock_pool=["000001", "000002", "600036"],
    start_date="20240101",
    end_date="20241231"
)

# 查看结果
print(f"收益率: {result.total_return:.2f}%")
print(f"胜率: {result.win_rate:.1f}%")
print(f"最大回撤: {result.max_drawdown:.2f}%")
```

#### 多策略对比

```bash
# 运行多策略对比测试
python test_multi_strategies.py

# 原有策略 vs 新策略对比
python test_original_vs_new.py
```

更多示例：[QUICK_START.md](./docs/QUICK_START.md)

## 📊 策略库

### 内置策略

| 策略 | 类型 | 收益率 | 胜率 | 回撤 | 适用场景 |
|------|------|--------|------|------|----------|
| **OriginalSignalStrategy** | 原有逻辑 | +3.78% | 80.0% ⭐ | 1.64% ⭐ | 震荡市/稳健 |
| **MACrossoverStrategy** | 趋势跟踪 | +14.15% ⭐ | 75.0% | 7.18% | 趋势市/激进 |
| **BollingerStrategy** | 均值回归 | +8.55% | 76.9% | 6.60% | 震荡市/平衡 |
| **MomentumStrategy** | 动量追踪 | +4.15% | 55.6% | 7.38% | 牛市/追涨 |
| **MultiFactorStrategy** | 多因子 | +8.03% | 57.1% | 6.52% | 全市场/综合 |
| **StrategyEnsemble** | 策略集成 | +12.55% | 76.9% | 4.93% | 通用/组合 |

> 基于 2024年全年数据，股票池：000001, 000002, 600036

详细说明：[STRATEGY_REFERENCE.md](./docs/STRATEGY_REFERENCE.md)

### 策略选择建议

| 市场环境 | 推荐策略 | 预期收益 | 风险等级 |
|---------|---------|----------|----------|
| 🐂 牛市 | MACrossover, Momentum | 10-15% | 中高 |
| 🐻 熊市 | OriginalSignal, Bollinger | 3-8% | 低 |
| 📊 震荡市 | Bollinger, OriginalSignal | 5-10% | 低中 |
| ❓ 不确定 | Ensemble, MultiFactor | 8-12% | 中 |

## 📁 项目结构

```
stock_picker/
├── core/                       # 新架构核心模块
│   ├── data/                   # 数据层
│   ├── indicators/             # 指标层
│   ├── strategies/             # 策略层 (7+ 种策略)
│   └── backtest/               # 回测层
│
├── src/                        # 原有业务逻辑 (完整保留)
│   ├── data_fetcher.py         # AKShare数据获取
│   ├── technical.py            # 技术指标
│   ├── signal_engine.py        # 原信号引擎
│   └── ...
│
├── ui/                         # Web界面
│   └── app.py                  # Streamlit应用
│
├── docs/                       # 文档
│   ├── ARCHITECTURE.md         # 完整架构文档
│   ├── QUICK_START.md          # 快速开始
│   └── STRATEGY_REFERENCE.md   # 策略参考手册
│
├── tests/                      # 测试脚本
│   ├── test_multi_strategies.py
│   └── test_original_vs_new.py
│
├── data/                       # 数据目录
│   └── cache/                  # 缓存文件
│
├── config.py                   # 配置文件
├── main.py                     # 主程序
└── requirements.txt            # 依赖
```

## 🎯 使用场景

### 场景1: 策略研究员

```python
# 快速实现新策略想法
class MyStrategy(Strategy):
    def get_required_indicators(self):
        return ["MA", "MACD"]

    def generate_signals(self, df):
        # 你的策略逻辑
        ...

# 立即回测验证
engine = BacktestEngine()
result = engine.run(MyStrategy(), stock_pool, start, end)
```

### 场景2: 量化投资者

```python
# 对比多个策略，选择最优
strategies = [
    OriginalSignalStrategy(),
    MACrossoverStrategy(),
    BollingerStrategy(),
]

for strategy in strategies:
    result = engine.run(strategy, ...)
    print(f"{strategy.name}: {result.total_return}%")
```

### 场景3: 风险管理

```python
# 自定义风控规则
engine = BacktestEngine(
    risk_config={
        "max_positions": 3,      # 最多3只
        "position_size": 0.30,   # 每只30%
        "stop_loss": -0.08,      # -8%止损
        "trailing_stop": 0.04,   # 4%移动止损
    }
)
```

### 场景4: 实盘交易

```python
# 每日定时生成信号
from core.strategies import StrategyManager

manager = StrategyManager()
result = manager.run_strategy("my_strategy", code="000001", mode="realtime")

if result.action == "buy" and result.confidence > 0.7:
    # 发送通知 / 执行交易
    send_notification(result)
```

## 🔧 扩展开发

### 添加新策略 (3步)

**步骤1**: 创建策略类

```python
# core/strategies/my_strategy.py
from .strategy_base import Strategy, StrategyResult

class MyStrategy(Strategy):
    def get_required_indicators(self):
        return ["MA", "RSI"]

    def generate_signals(self, df):
        latest = df.iloc[-1]

        if latest["MA5"] > latest["MA20"]:
            return StrategyResult(
                action="buy", score=80,
                reasons=["均线多头"], confidence=0.8
            )

        return StrategyResult(action="hold", ...)
```

**步骤2**: 注册策略

```python
# core/strategies/__init__.py
from .my_strategy import MyStrategy

__all__ = [..., "MyStrategy"]
```

**步骤3**: 测试策略

```python
from core.strategies import MyStrategy

strategy = MyStrategy()
result = engine.run(strategy, stock_pool, start, end)
print(result)
```

完整指南：[ARCHITECTURE.md#扩展开发](./docs/ARCHITECTURE.md#扩展开发)

## 📚 文档

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 完整架构设计和技术细节 |
| [QUICK_START.md](./docs/QUICK_START.md) | 5分钟快速上手指南 |
| [STRATEGY_REFERENCE.md](./docs/STRATEGY_REFERENCE.md) | 所有策略的详细说明 |
| [PHASE1_GUIDE.md](./docs/PHASE1_GUIDE.md) | Phase 1 开发指南 |

## 🧪 测试

```bash
# Phase 1 测试 (数据+指标+策略基础)
python test_phase1.py

# Phase 2 测试 (回测引擎)
python test_phase2.py

# 多策略对比测试
python test_multi_strategies.py

# 原有vs新策略对比
python test_original_vs_new.py
```

## 🛣️ 开发路线图

### ✅ 已完成

- [x] Phase 1: 数据层 + 指标层 + 策略层
- [x] Phase 2: 回测引擎 + 风控系统
- [x] 7种策略实现
- [x] 策略集成机制
- [x] 完整文档和测试

### 🚧 进行中

- [ ] Phase 3A: 实盘信号生成模块
- [ ] Phase 3B: REST API + WebSocket
- [ ] Phase 3C: 策略优化模块

### 📅 计划中

- [ ] 参数优化（网格搜索、遗传算法）
- [ ] Walk-forward 分析
- [ ] Monte Carlo 模拟
- [ ] 前端可视化增强
- [ ] 实时推送系统

## 💡 设计理念

1. **分层架构** - 数据、指标、策略、回测清晰分离
2. **策略无关** - 回测引擎与具体策略解耦
3. **易于扩展** - 新增策略只需继承基类
4. **复用为主** - 最大程度复用原有代码
5. **向后兼容** - 原有系统继续正常运行

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发规范

- 遵循 PEP 8
- 添加类型注解
- 编写 Docstring
- 单元测试覆盖

## 📄 许可证

MIT License

## 📞 联系方式

- Issue: [GitHub Issues]
- Email: [你的邮箱]

---

**最后更新**: 2024-01-28
**版本**: v2.0 (Phase 1 + Phase 2 完成)

**🌟 如果这个项目对你有帮助，欢迎 Star！**
