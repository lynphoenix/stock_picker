# -*- coding: utf-8 -*-
"""
动量策略

追踪强势上涨的股票：
- 买入：持续上涨 + 突破新高
- 卖出：动量衰减 + 跌破关键支撑
"""
from typing import Dict, List
import pandas as pd
import numpy as np

from .strategy_base import Strategy, StrategyResult


class MomentumStrategy(Strategy):
    """
    动量策略

    适用场景：牛市、强势趋势
    风险：顶部追高、回撤较大
    """

    def __init__(self, params: Dict = None):
        """
        Args:
            params:
                - lookback_period: 动量计算周期（默认20天）
                - min_momentum: 最小动量要求（默认5%）
                - breakout_window: 突破周期（默认60天）
                - volume_multiplier: 成交量倍数（默认2）
                - max_rsi: 最大RSI限制（默认85，避免极度超买）
        """
        default_params = {
            "lookback_period": 20,
            "min_momentum": 5,  # 5%
            "breakout_window": 60,
            "volume_multiplier": 2,
            "max_rsi": 85,
        }

        self.params = {**default_params, **(params or {})}
        self.name = "Momentum Strategy"
        self.description = f"动量策略({self.params['lookback_period']}日)"

    def get_required_indicators(self) -> List[str]:
        """需要的技术指标"""
        return ["MA5", "MA20", "RSI", "volume"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号

        买入条件：
        1. 20日动量 > 5%
        2. 创60日新高
        3. 成交量放大
        4. RSI < 85（避免极度超买）

        卖出条件：
        1. 动量转负
        2. 跌破MA20
        3. RSI < 40（动量衰减）
        """
        if df.empty or len(df) < self.params["breakout_window"]:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据不足"],
                confidence=0.0,
                metadata={}
            )

        # 计算动量指标
        df = df.copy()
        lookback = self.params["lookback_period"]

        # 1. 价格动量（N日涨幅）
        df["momentum"] = (df["close"] / df["close"].shift(lookback) - 1) * 100

        # 2. 是否创新高
        df["is_new_high"] = df["close"] == df["close"].rolling(self.params["breakout_window"]).max()

        # 3. 连续上涨天数
        df["price_change"] = df["close"].diff()
        df["up_days"] = (df["price_change"] > 0).rolling(5).sum()

        # 获取最新数据
        latest = df.iloc[-1]
        close = latest["close"]
        momentum = latest["momentum"]
        is_new_high = latest["is_new_high"]
        up_days = latest["up_days"]
        rsi = latest.get("RSI", 50)
        ma5 = latest.get("MA5", close)
        ma20 = latest.get("MA20", close)

        # 成交量
        volume = latest["volume"]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1

        # 计算近期波动率（用于风险评估）
        recent_volatility = df["close"].pct_change().rolling(20).std().iloc[-1] * 100

        score = 0
        reasons = []
        confidence = 0.0

        # 买入信号

        # 1. 强劲动量
        if momentum > self.params["min_momentum"]:
            momentum_score = min(30, int(momentum / self.params["min_momentum"] * 30))
            score += momentum_score
            reasons.append(f"{lookback}日动量+{momentum:.1f}%")
            confidence += 0.3

        # 2. 创新高
        if is_new_high:
            score += 25
            reasons.append(f"创{self.params['breakout_window']}日新高")
            confidence += 0.25

        # 3. 持续上涨
        if up_days >= 3:
            score += 15
            reasons.append(f"连涨{int(up_days)}天")
            confidence += 0.15

        # 4. 成交量放大
        if volume_ratio >= self.params["volume_multiplier"]:
            score += 15
            reasons.append(f"放量({volume_ratio:.1f}倍)")
            confidence += 0.15

        # 5. 多头排列
        if close > ma5 > ma20:
            score += 10
            reasons.append("多头排列")
            confidence += 0.1

        # 风险控制：避免极度超买
        if rsi > self.params["max_rsi"]:
            score = max(0, score - 30)
            reasons.append(f"⚠️ RSI过高({rsi:.0f})")
            confidence *= 0.5

        # 卖出信号

        # 1. 动量转负
        if momentum < -5:
            return StrategyResult(
                action="sell",
                score=80,
                reasons=[f"动量转负({momentum:.1f}%)"],
                confidence=0.8,
                metadata={
                    "momentum": momentum,
                    "close": close
                }
            )

        # 2. 跌破MA20
        if close < ma20 * 0.97:
            return StrategyResult(
                action="sell",
                score=75,
                reasons=["跌破MA20"],
                confidence=0.75,
                metadata={
                    "close": close,
                    "ma20": ma20
                }
            )

        # 3. 动量衰减（RSI < 40 且动量 < 0）
        if rsi < 40 and momentum < 0:
            return StrategyResult(
                action="sell",
                score=70,
                reasons=[f"动量衰减(RSI={rsi:.0f}, 动量={momentum:.1f}%)"],
                confidence=0.7,
                metadata={
                    "rsi": rsi,
                    "momentum": momentum
                }
            )

        # 买入判断
        if score >= 70:
            return StrategyResult(
                action="buy",
                score=score,
                reasons=reasons,
                confidence=min(confidence, 1.0),
                metadata={
                    "momentum": momentum,
                    "is_new_high": is_new_high,
                    "up_days": up_days,
                    "volume_ratio": volume_ratio,
                    "rsi": rsi,
                    "volatility": recent_volatility
                }
            )

        # 持有
        return StrategyResult(
            action="hold",
            score=score,
            reasons=reasons if reasons else [f"动量不足({momentum:.1f}%)"],
            confidence=confidence,
            metadata={
                "momentum": momentum,
                "rsi": rsi
            }
        )
