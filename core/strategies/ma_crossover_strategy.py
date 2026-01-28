# -*- coding: utf-8 -*-
"""
双均线穿越策略

经典的趋势跟踪策略：
- 金叉买入：短期均线上穿长期均线
- 死叉卖出：短期均线下穿长期均线
"""
from typing import Dict, List
import pandas as pd
import numpy as np

from .strategy_base import Strategy, StrategyResult


class MACrossoverStrategy(Strategy):
    """
    双均线穿越策略

    适用场景：趋势明显的市场环境
    风险：震荡市容易频繁买卖，产生假信号
    """

    def __init__(self, params: Dict = None):
        """
        Args:
            params:
                - short_window: 短期均线周期（默认5）
                - long_window: 长期均线周期（默认20）
                - volume_threshold: 成交量阈值倍数（默认1.5）
                - min_gain_pct: 最小涨幅要求（默认-5，即最近5日涨幅）
        """
        default_params = {
            "short_window": 5,
            "long_window": 20,
            "volume_threshold": 1.5,
            "min_gain_pct": -5,  # 允许-5%以上的近期表现
        }

        self.params = {**default_params, **(params or {})}
        self.name = "MA Crossover Strategy"
        self.description = f"双均线穿越({self.params['short_window']}/{self.params['long_window']})"

    def get_required_indicators(self) -> List[str]:
        """需要的技术指标"""
        return ["MA5", "MA10", "MA20", "volume"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号

        买入条件：
        1. 短期均线上穿长期均线（金叉）
        2. 当前价格在短期均线上方
        3. 成交量放大

        卖出条件：
        1. 短期均线下穿长期均线（死叉）
        2. 或价格跌破长期均线
        """
        if df.empty or len(df) < self.params["long_window"]:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据不足"],
                confidence=0.0,
                metadata={}
            )

        # 获取最新数据
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else latest

        # 获取均线
        short_ma = latest[f"MA{self.params['short_window']}"]
        long_ma = latest[f"MA{self.params['long_window']}"]
        prev_short_ma = prev[f"MA{self.params['short_window']}"]
        prev_long_ma = prev[f"MA{self.params['long_window']}"]

        close = latest["close"]
        volume = latest["volume"]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]

        # 计算信号评分
        score = 0
        reasons = []
        confidence = 0.0

        # 检测金叉/死叉
        golden_cross = (prev_short_ma <= prev_long_ma) and (short_ma > long_ma)
        death_cross = (prev_short_ma >= prev_long_ma) and (short_ma < long_ma)

        # 买入信号
        if golden_cross:
            score += 40
            reasons.append(f"金叉({self.params['short_window']}/{self.params['long_window']})")
            confidence += 0.4

        # 价格在均线上方
        if close > short_ma > long_ma:
            score += 20
            reasons.append("多头排列")
            confidence += 0.2

        # 成交量放大
        if volume > avg_volume * self.params["volume_threshold"]:
            score += 15
            reasons.append(f"放量({volume/avg_volume:.1f}倍)")
            confidence += 0.15

        # 近期涨幅
        recent_gain = (close - df.iloc[-5]["close"]) / df.iloc[-5]["close"] * 100 if len(df) >= 5 else 0
        if recent_gain > self.params["min_gain_pct"]:
            score += 10
            reasons.append(f"5日涨幅{recent_gain:.1f}%")
            confidence += 0.1

        # 卖出信号
        if death_cross:
            return StrategyResult(
                action="sell",
                score=80,
                reasons=[f"死叉({self.params['short_window']}/{self.params['long_window']})"],
                confidence=0.8,
                metadata={
                    "short_ma": short_ma,
                    "long_ma": long_ma,
                    "cross_type": "death"
                }
            )

        # 跌破长期均线
        if close < long_ma * 0.97:  # 跌破3%
            return StrategyResult(
                action="sell",
                score=70,
                reasons=[f"跌破MA{self.params['long_window']}"],
                confidence=0.7,
                metadata={
                    "close": close,
                    "long_ma": long_ma
                }
            )

        # 判断买入
        if score >= 60:
            return StrategyResult(
                action="buy",
                score=score,
                reasons=reasons,
                confidence=min(confidence, 1.0),
                metadata={
                    "short_ma": short_ma,
                    "long_ma": long_ma,
                    "close": close,
                    "volume_ratio": volume / avg_volume
                }
            )

        # 持有
        return StrategyResult(
            action="hold",
            score=score,
            reasons=reasons if reasons else ["无明确信号"],
            confidence=confidence,
            metadata={
                "short_ma": short_ma,
                "long_ma": long_ma
            }
        )
