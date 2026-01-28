# 策略库参考手册

本文档详细说明系统中所有可用策略的逻辑、参数和使用场景。

---

## 📑 目录

1. [OriginalSignalStrategy - 原有信号引擎策略](#1-originalsignalstrategy)
2. [MACDRSIStrategy - MACD+RSI策略](#2-macdrsistrategy)
3. [MACrossoverStrategy - 双均线穿越策略](#3-macrossoverstrategy)
4. [BollingerStrategy - 布林带策略](#4-bollingerstrategy)
5. [MomentumStrategy - 动量策略](#5-momentumstrategy)
6. [MultiFactorStrategy - 多因子策略](#6-multifactorstrategy)
7. [StrategyEnsemble - 策略集成](#7-strategyensemble)
8. [策略对比表](#策略对比表)

---

## 1. OriginalSignalStrategy

### 概述

这是从原有 `src/signal_engine.py` 中提取的策略逻辑，完全保留原系统的评分规则和信号生成逻辑。

### 买入逻辑

| 条件 | 得分 | 说明 |
|------|------|------|
| MACD金叉 | 30分 | DIF上穿DEA |
| RSI超卖 | 25分 | RSI < 30 |
| 站上20日均线 | 20分 | 价格 > MA20 |
| 板块热度高 | 0-25分 | 板块热度 > 60% |

**买入阈值**: 50分

### 卖出逻辑

| 条件 | 得分 | 说明 |
|------|------|------|
| MACD死叉 | 30分 | DIF下穿DEA |
| RSI超买 | 25分 | RSI > 70 |
| 跌破20日均线 | 20分 | 价格 < MA20 |
| 止损 | 100分 | 亏损 > 10% |

**卖出阈值**: 60分

### 参数配置

```python
OriginalSignalStrategy(params={
    "buy_threshold": 50,      # 买入阈值
    "sell_threshold": 60,     # 卖出阈值
    "sector_heat": 0.5,       # 板块热度（0-1）
    "stop_loss": -10,         # 止损百分比
})
```

### 适用场景

- ✅ 震荡市场
- ✅ 风险控制优先
- ✅ 稳健型投资者

### 性能（2024年）

- 收益率: +3.78%
- 胜率: 80.0% ⭐
- 最大回撤: 1.64% ⭐
- 交易次数: 5次

### 代码示例

```python
from core.strategies import OriginalSignalStrategy
from core.backtest import BacktestEngine

strategy = OriginalSignalStrategy(params={
    "buy_threshold": 45,  # 降低门槛，增加交易频率
    "sector_heat": 0.7    # 提高板块热度要求
})

engine = BacktestEngine()
result = engine.run(
    strategy=strategy,
    stock_pool=["000001", "000002"],
    start_date="20240101",
    end_date="20241231"
)
```

---

## 2. MACDRSIStrategy

### 概述

基于MACD、RSI和均线的综合技术指标策略，是 OriginalSignalStrategy 的变种，采用不同的评分权重。

### 买入逻辑

| 条件 | 得分 | 说明 |
|------|------|------|
| MACD金叉 | 30分 | DIF上穿DEA |
| RSI超卖反弹 | 15分 | 30 < RSI < 50 |
| 均线多头排列 | 20分 | MA5 > MA10 > MA20 |
| 成交量放大 | 15分 | 成交量 > 均量1.5倍 |
| 近期涨幅合理 | 10分 | 5日涨幅 < 10% |

**买入阈值**: 默认45分（可调整）

### 卖出逻辑

- MACD死叉
- RSI超买 (>70)
- 跌破MA20
- 触发止损/止盈

### 参数配置

```python
MACDRSIStrategy(params={
    "buy_threshold": 45,        # 买入阈值
    "rsi_oversold": 30,         # RSI超卖线
    "rsi_overbought": 70,       # RSI超买线
    "volume_threshold": 1.5,    # 成交量倍数
    "weights": {                # 各因子权重
        "macd": 0.35,
        "rsi": 0.20,
        "ma": 0.25,
        "volume": 0.20
    }
})
```

### 适用场景

- ✅ 震荡市
- ✅ 趋势初期
- ⚠️ 强势牛市（可能错过）

### 性能（2024年）

- 收益率: +3.78%
- 胜率: 80.0%
- 最大回撤: 1.64%
- 交易次数: 5次

---

## 3. MACrossoverStrategy

### 概述

经典的双均线穿越策略，金叉买入、死叉卖出，适合趋势明显的市场。

### 买入逻辑

| 条件 | 得分 | 说明 |
|------|------|------|
| 金叉 | 40分 | 短期均线上穿长期均线 |
| 多头排列 | 20分 | 价格 > MA5 > MA20 |
| 成交量放大 | 15分 | 成交量 > 均量1.5倍 |
| 5日涨幅合理 | 10分 | 涨幅 > -5% |

**买入阈值**: 60分

### 卖出逻辑

- 死叉（短均线下穿长均线）
- 跌破长期均线3%

### 参数配置

```python
MACrossoverStrategy(params={
    "short_window": 5,          # 短期均线周期
    "long_window": 20,          # 长期均线周期
    "volume_threshold": 1.5,    # 成交量倍数
    "min_gain_pct": -5,         # 最小涨幅要求
})
```

### 常用参数组合

| 组合 | 特点 | 适用场景 |
|------|------|----------|
| (5, 20) | 灵敏，信号多 | 短线交易 |
| (10, 30) | 平衡 | 中线交易 |
| (20, 60) | 稳定，信号少 | 长线交易 |

### 适用场景

- ✅ 趋势明显的市场
- ✅ 单边行情（牛市/熊市）
- ⚠️ 震荡市（频繁假信号）

### 性能（2024年）

- 收益率: +14.15% ⭐
- 胜率: 75.0%
- 最大回撤: 7.18%
- 交易次数: 12次

---

## 4. BollingerStrategy

### 概述

基于布林带的均值回归策略，在价格触及上下轨时反向操作。

### 买入逻辑

| 条件 | 得分 | 说明 |
|------|------|------|
| 触及下轨 | 35分 | 价格接近或突破下轨 |
| RSI超卖 | 25分 | RSI < 30 |
| 低波动环境 | 15分 | 带宽 < 10% |
| 成交量放大 | 10分 | 量比 > 1.5 |

**买入阈值**: 60分

### 卖出逻辑

- 触及上轨（价格位置 > 0.98）
- RSI超买且接近上轨

### 参数配置

```python
BollingerStrategy(params={
    "window": 20,                   # 布林带周期
    "num_std": 2,                   # 标准差倍数
    "lower_touch_threshold": 0.02,  # 下轨触及阈值（2%）
    "upper_touch_threshold": 0.02,  # 上轨触及阈值
    "rsi_oversold": 30,
    "rsi_overbought": 70,
})
```

### 布林带位置

```
价格位置 = (当前价 - 下轨) / (上轨 - 下轨)

0.0  - 触及下轨（超卖）
0.5  - 中轨（均值）
1.0  - 触及上轨（超买）
```

### 适用场景

- ✅ 震荡市、区间盘整
- ✅ 均值回归特征明显
- ⚠️ 趋势市场（逆势操作）

### 性能（2024年）

- 收益率: +8.55%
- 胜率: 76.9%
- 最大回撤: 6.60%
- 交易次数: 13次

---

## 5. MomentumStrategy

### 概述

追踪强势上涨股票的动量策略，适合牛市和明确上升趋势。

### 买入逻辑

| 条件 | 得分 | 说明 |
|------|------|------|
| 强劲动量 | 30分 | 20日涨幅 > 5% |
| 创新高 | 25分 | 创60日新高 |
| 连续上涨 | 15分 | 5日内上涨≥3天 |
| 成交量放大 | 15分 | 量比 ≥ 2倍 |
| 多头排列 | 10分 | 价格 > MA5 > MA20 |

**买入阈值**: 70分

**风险控制**: RSI > 85 时降低评分

### 卖出逻辑

- 动量转负（20日涨幅 < -5%）
- 跌破MA20超过3%
- RSI < 40 且动量<0（动量衰减）

### 参数配置

```python
MomentumStrategy(params={
    "lookback_period": 20,      # 动量计算周期
    "min_momentum": 5,          # 最小动量要求（5%）
    "breakout_window": 60,      # 突破周期
    "volume_multiplier": 2,     # 成交量倍数
    "max_rsi": 85,              # 最大RSI（避免极度超买）
})
```

### 适用场景

- ✅ 牛市、强势趋势
- ✅ 追涨强势股
- ⚠️ 熊市（容易顶部追高）
- ⚠️ 震荡市（假突破）

### 性能（2024年）

- 收益率: +4.15%
- 胜率: 55.6%
- 最大回撤: 7.38%
- 交易次数: 9次

---

## 6. MultiFactorStrategy

### 概述

综合多个因子的评分策略，将趋势、动量、价值、成交量、波动率等多个维度加权计算。

### 因子体系

#### 1. 趋势因子 (权重30%)

- 均线排列 (40分)
- MACD趋势 (30分)
- 价格相对位置 (30分)

#### 2. 动量因子 (权重25%)

- 5日涨幅 (35分)
- 20日涨幅 (35分)
- 动量加速度 (30分)

#### 3. 价值因子 (权重20%)

- RSI位置 (50分)
- 偏离MA20 (50分)

#### 4. 成交量因子 (权重15%)

- 量比 (70分)
- 量能趋势 (30分)

#### 5. 波动率因子 (权重10%)

- 20日波动率 (100分)

### 评分规则

```
总分 = 趋势因子×30% + 动量因子×25% + 价值因子×20% +
       成交量因子×15% + 波动率因子×10%
```

### 参数配置

```python
MultiFactorStrategy(params={
    "weights": {
        "trend": 0.3,       # 趋势权重
        "momentum": 0.25,   # 动量权重
        "value": 0.2,       # 价值权重
        "volume": 0.15,     # 成交量权重
        "volatility": 0.1,  # 波动率权重
    },
    "buy_threshold": 70,    # 买入阈值
    "sell_threshold": 40,   # 卖出阈值
})
```

### 置信度计算

```python
# 因子得分一致性越高，置信度越高
score_std = np.std([趋势分, 动量分, 价值分, 成交量分, 波动分])
confidence = min(1.0, 总分/100 * (1 - score_std/50))
```

### 适用场景

- ✅ 全市场选股
- ✅ 不确定环境
- ✅ 追求稳健

### 性能（2024年）

- 收益率: +8.03%
- 胜率: 57.1%
- 最大回撤: 6.52%
- 交易次数: 7次

---

## 7. StrategyEnsemble

### 概述

组合多个策略，通过投票机制做出最终决策，提高决策稳健性。

### 投票方式

#### 1. 加权投票 (Weighted)

```python
# 每个策略的评分 × 权重，求和
action_scores = {
    "buy": Σ(策略i评分 × 权重i) for action="buy",
    "sell": Σ(策略i评分 × 权重i) for action="sell",
    "hold": Σ(策略i评分 × 权重i) for action="hold",
}
最终动作 = max(action_scores)
```

#### 2. 多数投票 (Majority)

```python
# 每个策略一票，取票数最多的
votes = {"buy": 0, "sell": 0, "hold": 0}
for 策略 in 策略列表:
    votes[策略.action] += 1
最终动作 = max(votes)
```

#### 3. 一致投票 (Unanimous)

```python
# 所有策略必须一致，否则hold
if all(策略.action == "buy" for 策略 in 策略列表):
    最终动作 = "buy"
else:
    最终动作 = "hold"
```

### 使用示例

```python
from core.strategies import StrategyEnsemble

ensemble = StrategyEnsemble(
    strategies=[
        (OriginalSignalStrategy(), 0.4),   # 40%权重
        (MACrossoverStrategy(), 0.3),      # 30%权重
        (BollingerStrategy(), 0.3),        # 30%权重
    ],
    voting_method="weighted",  # 投票方式
    min_agreement=0.6          # 最小一致性60%
)

result = ensemble.generate_signals(df)
```

### 一致性检查

```python
# 计算策略间的一致性
agreement = (最高票数 - 第二高票数) / 总票数

if agreement < min_agreement:
    # 策略分歧，降低置信度
    confidence *= 0.5
```

### 适用场景

- ✅ 降低单一策略风险
- ✅ 提高决策稳健性
- ✅ 综合多种策略优势

### 性能（2024年）

- 收益率: +12.55%
- 胜率: 76.9%
- 最大回撤: 4.93%
- 交易次数: 13次

### 推荐组合

#### 保守组合
```python
[
    (OriginalSignalStrategy(), 0.5),
    (BollingerStrategy(), 0.3),
    (MultiFactorStrategy(), 0.2)
]
# 特点：高胜率，低回撤
```

#### 平衡组合
```python
[
    (MACrossoverStrategy(), 0.3),
    (BollingerStrategy(), 0.3),
    (MultiFactorStrategy(), 0.4)
]
# 特点：收益与风险平衡
```

#### 激进组合
```python
[
    (MACrossoverStrategy(), 0.4),
    (MomentumStrategy(), 0.4),
    (MultiFactorStrategy(), 0.2)
]
# 特点：高收益，容忍高回撤
```

---

## 策略对比表

### 按收益率排名

| 排名 | 策略 | 收益率 | 胜率 | 回撤 | 适合 |
|------|------|--------|------|------|------|
| 🥇 | MACrossoverStrategy | +14.15% | 75.0% | 7.18% | 趋势市 |
| 🥈 | StrategyEnsemble | +12.55% | 76.9% | 4.93% | 综合 |
| 🥉 | BollingerStrategy | +8.55% | 76.9% | 6.60% | 震荡市 |
| 4 | MultiFactorStrategy | +8.03% | 57.1% | 6.52% | 全市场 |
| 5 | MomentumStrategy | +4.15% | 55.6% | 7.38% | 牛市 |
| 6 | OriginalSignalStrategy | +3.78% | 80.0% | 1.64% | 稳健 |
| 6 | MACDRSIStrategy | +3.78% | 80.0% | 1.64% | 稳健 |

### 按胜率排名

| 排名 | 策略 | 胜率 | 收益率 | 特点 |
|------|------|------|--------|------|
| 🥇 | OriginalSignalStrategy | 80.0% | +3.78% | ⭐ 最稳健 |
| 🥇 | MACDRSIStrategy | 80.0% | +3.78% | 稳健 |
| 🥉 | BollingerStrategy | 76.9% | +8.55% | 均值回归 |
| 🥉 | StrategyEnsemble | 76.9% | +12.55% | 组合策略 |
| 5 | MACrossoverStrategy | 75.0% | +14.15% | 高收益 |
| 6 | MultiFactorStrategy | 57.1% | +8.03% | 综合 |
| 7 | MomentumStrategy | 55.6% | +4.15% | 激进 |

### 按回撤排名（越小越好）

| 排名 | 策略 | 回撤 | 收益率 | 特点 |
|------|------|------|--------|------|
| 🥇 | OriginalSignalStrategy | 1.64% | +3.78% | ⭐ 最小回撤 |
| 🥇 | MACDRSIStrategy | 1.64% | +3.78% | 控制回撤 |
| 🥉 | StrategyEnsemble | 4.93% | +12.55% | 平衡 |
| 4 | MultiFactorStrategy | 6.52% | +8.03% | 适中 |
| 5 | BollingerStrategy | 6.60% | +8.55% | 可接受 |
| 6 | MACrossoverStrategy | 7.18% | +14.15% | 高收益代价 |
| 7 | MomentumStrategy | 7.38% | +4.15% | 波动大 |

---

## 选择建议

### 根据市场环境

| 市场环境 | 推荐策略 | 原因 |
|---------|---------|------|
| 🐂 **牛市** | MACrossoverStrategy, MomentumStrategy | 追踪趋势，获取高收益 |
| 🐻 **熊市** | OriginalSignalStrategy, BollingerStrategy | 控制回撤，高胜率 |
| 📊 **震荡市** | BollingerStrategy, OriginalSignalStrategy | 均值回归，稳健盈利 |
| ❓ **不确定** | StrategyEnsemble, MultiFactorStrategy | 综合决策，降低风险 |

### 根据风险偏好

| 风险偏好 | 推荐策略 | 预期收益 | 预期回撤 |
|---------|---------|----------|----------|
| 🛡️ **保守型** | OriginalSignalStrategy | 3-5% | < 2% |
| ⚖️ **平衡型** | StrategyEnsemble, MultiFactorStrategy | 8-12% | 4-7% |
| ⚡ **激进型** | MACrossoverStrategy, MomentumStrategy | 10-15% | 7-10% |

### 根据交易频率

| 交易频率 | 推荐策略 | 年交易次数 |
|---------|---------|-----------|
| 低频 | OriginalSignalStrategy | 5-10次 |
| 中频 | MACrossoverStrategy, MultiFactorStrategy | 10-15次 |
| 高频 | BollingerStrategy, MomentumStrategy | 15-20次 |

---

## 参数调优建议

### MACrossoverStrategy

```python
# 提高灵敏度（增加信号）
{"short_window": 5, "long_window": 15}

# 降低灵敏度（减少假信号）
{"short_window": 10, "long_window": 40}

# 平衡设置
{"short_window": 5, "long_window": 20}  # 默认
```

### BollingerStrategy

```python
# 更激进（宽容度更高）
{"window": 20, "num_std": 1.5, "lower_touch_threshold": 0.05}

# 更保守（严格触及）
{"window": 20, "num_std": 2.5, "lower_touch_threshold": 0.01}
```

### MomentumStrategy

```python
# 降低门槛（增加信号）
{"min_momentum": 3, "max_rsi": 90}

# 提高门槛（只买强势股）
{"min_momentum": 8, "max_rsi": 80}
```

---

## 策略组合示例

### 四季轮换策略

```python
# 根据季节选择策略
import datetime

month = datetime.datetime.now().month

if month in [3, 4, 5]:  # 春季（上涨季）
    strategy = MomentumStrategy()
elif month in [6, 7, 8]:  # 夏季（震荡季）
    strategy = BollingerStrategy()
elif month in [9, 10, 11]:  # 秋季（分化季）
    strategy = MultiFactorStrategy()
else:  # 冬季（防守季）
    strategy = OriginalSignalStrategy()
```

### 风险自适应策略

```python
# 根据账户盈亏调整策略
if portfolio.total_return > 0.10:
    # 盈利超过10%，切换保守策略
    strategy = OriginalSignalStrategy()
elif portfolio.total_return < -0.05:
    # 亏损超过5%，切换防守策略
    strategy = BollingerStrategy()
else:
    # 正常情况，使用平衡策略
    strategy = StrategyEnsemble([...])
```

---

**最后更新**: 2024-01-28
**版本**: v2.0

需要更多帮助？查看 [完整架构文档](./ARCHITECTURE.md)
