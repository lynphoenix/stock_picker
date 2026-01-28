# -*- coding: utf-8 -*-
"""
布林带均值回归策略

基于布林带的超买超卖反转策略：
- 触及下轨买入（超卖反转）
- 触及上轨卖出（超买回归）
"""
from typing import Dict, List
import pandas as pd
import numpy as np

from .strategy_base import Strategy, StrategyResult


class BollingerStrategy(Strategy):
    """
    布林带均值回归策略

    适用场景：震荡市、区间盘整
    风险：趋势市场容易过早买入/卖出
    """

    def __init__(self, params: Dict = None):
        """
        Args:
            params:
                - window: 布林带周期（默认20）
                - num_std: 标准差倍数（默认2）
                - lower_touch_threshold: 下轨触及阈值（默认0.02，即2%）
                - upper_touch_threshold: 上轨触及阈值（默认0.02）
                - rsi_oversold: RSI超卖线（默认30）
                - rsi_overbought: RSI超买线（默认70）
        """
        default_params = {
            "window": 20,
            "num_std": 2,
            "lower_touch_threshold": 0.02,  # 2%范围内算触及
            "upper_touch_threshold": 0.02,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
        }

        self.params = {**default_params, **(params or {})}
        self.name = "Bollinger Bands Strategy"
        self.description = f"布林带均值回归({self.params['window']}, {self.params['num_std']}σ)"

    def get_required_indicators(self) -> List[str]:
        """需要的技术指标"""
        return ["MA20", "RSI"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号

        买入条件：
        1. 价格触及或突破下轨
        2. RSI < 30（超卖）
        3. 成交量放大

        卖出条件：
        1. 价格触及或突破上轨
        2. RSI > 70（超买）
        """
        if df.empty or len(df) < self.params["window"]:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据不足"],
                confidence=0.0,
                metadata={}
            )

        # 计算布林带
        df = df.copy()
        rolling_mean = df["close"].rolling(window=self.params["window"]).mean()
        rolling_std = df["close"].rolling(window=self.params["window"]).std()

        df["bb_upper"] = rolling_mean + (rolling_std * self.params["num_std"])
        df["bb_middle"] = rolling_mean
        df["bb_lower"] = rolling_mean - (rolling_std * self.params["num_std"])

        # 计算带宽比例（用于判断波动性）
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]

        # 获取最新数据
        latest = df.iloc[-1]
        close = latest["close"]
        bb_upper = latest["bb_upper"]
        bb_middle = latest["bb_middle"]
        bb_lower = latest["bb_lower"]
        bb_width = latest["bb_width"]
        rsi = latest.get("RSI", 50)

        # 计算价格位置（0=下轨, 0.5=中轨, 1=上轨）
        bb_position = (close - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5

        # 成交量
        volume = latest["volume"]
        avg_volume = df["volume"].rolling(20).mean().iloc[-1]
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1

        score = 0
        reasons = []
        confidence = 0.0

        # 买入信号（触及下轨）
        lower_distance = (close - bb_lower) / bb_lower
        if lower_distance <= self.params["lower_touch_threshold"]:
            score += 35
            reasons.append(f"触及下轨(位置{bb_position:.2f})")
            confidence += 0.35

        # RSI超卖
        if rsi < self.params["rsi_oversold"]:
            score += 25
            reasons.append(f"RSI超卖({rsi:.0f})")
            confidence += 0.25

        # 低波动性环境（更适合反转）
        if bb_width < 0.1:  # 带宽小于10%
            score += 15
            reasons.append("低波动环境")
            confidence += 0.15

        # 放量
        if volume_ratio > 1.5:
            score += 10
            reasons.append(f"放量({volume_ratio:.1f}倍)")
            confidence += 0.1

        # 卖出信号（触及上轨）
        upper_distance = (bb_upper - close) / bb_upper
        if upper_distance <= self.params["upper_touch_threshold"]:
            return StrategyResult(
                action="sell",
                score=70,
                reasons=[f"触及上轨(位置{bb_position:.2f})"],
                confidence=0.7,
                metadata={
                    "bb_position": bb_position,
                    "bb_upper": bb_upper,
                    "close": close,
                    "rsi": rsi
                }
            )

        # RSI超买
        if rsi > self.params["rsi_overbought"] and bb_position > 0.7:
            return StrategyResult(
                action="sell",
                score=75,
                reasons=[f"RSI超买({rsi:.0f})", f"接近上轨(位置{bb_position:.2f})"],
                confidence=0.75,
                metadata={
                    "bb_position": bb_position,
                    "rsi": rsi
                }
            )

        # 买入判断
        if score >= 60:
            return StrategyResult(
                action="buy",
                score=score,
                reasons=reasons,
                confidence=min(confidence, 1.0),
                metadata={
                    "bb_position": bb_position,
                    "bb_lower": bb_lower,
                    "bb_middle": bb_middle,
                    "bb_upper": bb_upper,
                    "rsi": rsi,
                    "bb_width": bb_width
                }
            )

        # 持有
        return StrategyResult(
            action="hold",
            score=score,
            reasons=reasons if reasons else [f"中性位置({bb_position:.2f})"],
            confidence=confidence,
            metadata={
                "bb_position": bb_position,
                "rsi": rsi
            }
        )
