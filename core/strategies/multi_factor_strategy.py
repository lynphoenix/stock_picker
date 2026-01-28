# -*- coding: utf-8 -*-
"""
多因子综合策略

整合多个因子进行综合评分：
- 技术面：趋势、动量、波动率
- 资金面：成交量、资金流向
- 情绪面：超买超卖、市场强度
"""
from typing import Dict, List
import pandas as pd
import numpy as np

from .strategy_base import Strategy, StrategyResult


class MultiFactorStrategy(Strategy):
    """
    多因子综合策略

    适用场景：全市场选股、策略组合
    优势：分散风险、稳健性强
    """

    def __init__(self, params: Dict = None):
        """
        Args:
            params:
                - weights: 因子权重字典
                    - trend: 趋势因子（默认0.3）
                    - momentum: 动量因子（默认0.25）
                    - value: 价值因子（默认0.2）
                    - volume: 成交量因子（默认0.15）
                    - volatility: 波动率因子（默认0.1）
                - buy_threshold: 买入阈值（默认70分）
                - sell_threshold: 卖出阈值（默认40分）
        """
        default_weights = {
            "trend": 0.3,
            "momentum": 0.25,
            "value": 0.2,
            "volume": 0.15,
            "volatility": 0.1,
        }

        default_params = {
            "weights": default_weights,
            "buy_threshold": 70,
            "sell_threshold": 40,
        }

        self.params = {**default_params, **(params or {})}
        self.name = "Multi-Factor Strategy"
        self.description = "多因子综合策略"

    def get_required_indicators(self) -> List[str]:
        """需要的技术指标"""
        return ["MA5", "MA10", "MA20", "MA60", "MACD_DIF", "MACD_DEA", "RSI", "volume"]

    def _calculate_trend_factor(self, df: pd.DataFrame, latest: pd.Series) -> tuple[float, List[str]]:
        """
        计算趋势因子（0-100分）

        考虑：
        - 均线排列
        - MACD方向
        - 价格相对位置
        """
        score = 0
        reasons = []

        close = latest["close"]
        ma5 = latest.get("MA5", close)
        ma10 = latest.get("MA10", close)
        ma20 = latest.get("MA20", close)
        ma60 = latest.get("MA60", close)

        # 1. 均线排列（40分）
        if close > ma5 > ma10 > ma20:
            score += 40
            reasons.append("完美多头排列")
        elif close > ma5 > ma20:
            score += 30
            reasons.append("多头排列")
        elif close > ma20:
            score += 20
            reasons.append("站上MA20")
        elif close < ma5 < ma10 < ma20:
            score += 0
            reasons.append("空头排列")

        # 2. MACD趋势（30分）
        dif = latest.get("MACD_DIF", 0)
        dea = latest.get("MACD_DEA", 0)

        if dif > 0 and dea > 0 and dif > dea:
            score += 30
            reasons.append("MACD多头")
        elif dif > dea:
            score += 20
            reasons.append("MACD金叉")
        elif dif < dea:
            score += 0
            reasons.append("MACD空头")

        # 3. 价格相对位置（30分）
        high_60 = df["high"].rolling(60).max().iloc[-1]
        low_60 = df["low"].rolling(60).min().iloc[-1]

        if high_60 > low_60:
            position = (close - low_60) / (high_60 - low_60)
            if position > 0.8:
                score += 30
                reasons.append("60日高位")
            elif position > 0.5:
                score += 20
                reasons.append("60日中高位")
            elif position < 0.3:
                score += 10
                reasons.append("60日低位")

        return score, reasons

    def _calculate_momentum_factor(self, df: pd.DataFrame, latest: pd.Series) -> tuple[float, List[str]]:
        """
        计算动量因子（0-100分）

        考虑：
        - 短期涨幅
        - 中期涨幅
        - ROC（变化率）
        """
        score = 0
        reasons = []

        close = latest["close"]

        # 1. 5日涨幅（35分）
        if len(df) >= 5:
            gain_5d = (close / df.iloc[-5]["close"] - 1) * 100
            if gain_5d > 5:
                score += 35
                reasons.append(f"5日+{gain_5d:.1f}%")
            elif gain_5d > 2:
                score += 25
                reasons.append(f"5日+{gain_5d:.1f}%")
            elif gain_5d > 0:
                score += 15
                reasons.append(f"5日+{gain_5d:.1f}%")

        # 2. 20日涨幅（35分）
        if len(df) >= 20:
            gain_20d = (close / df.iloc[-20]["close"] - 1) * 100
            if gain_20d > 15:
                score += 35
                reasons.append(f"20日+{gain_20d:.1f}%")
            elif gain_20d > 8:
                score += 25
                reasons.append(f"20日+{gain_20d:.1f}%")
            elif gain_20d > 0:
                score += 15
                reasons.append(f"20日+{gain_20d:.1f}%")

        # 3. 加速度（30分）
        if len(df) >= 20:
            gain_5d = (close / df.iloc[-5]["close"] - 1) * 100
            gain_10d = (df.iloc[-5]["close"] / df.iloc[-10]["close"] - 1) * 100

            if gain_5d > gain_10d and gain_5d > 0:
                score += 30
                reasons.append("动量加速")
            elif gain_5d > 0:
                score += 15
                reasons.append("动量持续")

        return score, reasons

    def _calculate_value_factor(self, df: pd.DataFrame, latest: pd.Series) -> tuple[float, List[str]]:
        """
        计算价值因子（0-100分）

        考虑：
        - RSI超买超卖
        - 价格偏离度
        """
        score = 0
        reasons = []

        close = latest["close"]
        rsi = latest.get("RSI", 50)
        ma20 = latest.get("MA20", close)

        # 1. RSI位置（50分）
        if 30 < rsi < 50:
            score += 50
            reasons.append(f"RSI适中({rsi:.0f})")
        elif 50 <= rsi < 65:
            score += 40
            reasons.append(f"RSI温和({rsi:.0f})")
        elif rsi >= 80:
            score += 10
            reasons.append(f"⚠️ RSI超买({rsi:.0f})")
        elif rsi <= 20:
            score += 60
            reasons.append(f"RSI超卖({rsi:.0f})")

        # 2. 偏离MA20（50分）
        deviation = (close / ma20 - 1) * 100
        if -5 < deviation < 3:
            score += 50
            reasons.append(f"接近均值({deviation:+.1f}%)")
        elif deviation < -10:
            score += 60
            reasons.append(f"超卖偏离({deviation:.1f}%)")
        elif deviation > 10:
            score += 20
            reasons.append(f"超买偏离({deviation:+.1f}%)")

        return score, reasons

    def _calculate_volume_factor(self, df: pd.DataFrame, latest: pd.Series) -> tuple[float, List[str]]:
        """
        计算成交量因子（0-100分）

        考虑：
        - 量比
        - 量能趋势
        """
        score = 0
        reasons = []

        volume = latest["volume"]
        avg_volume_20 = df["volume"].rolling(20).mean().iloc[-1]

        # 1. 量比（70分）
        if avg_volume_20 > 0:
            volume_ratio = volume / avg_volume_20

            if volume_ratio > 2:
                score += 70
                reasons.append(f"放量({volume_ratio:.1f}倍)")
            elif volume_ratio > 1.5:
                score += 55
                reasons.append(f"温和放量({volume_ratio:.1f}倍)")
            elif volume_ratio > 0.8:
                score += 40
                reasons.append("量能平稳")
            else:
                score += 20
                reasons.append("缩量")

        # 2. 量能趋势（30分）
        if len(df) >= 10:
            avg_volume_5 = df["volume"].rolling(5).mean().iloc[-1]
            avg_volume_10 = df["volume"].rolling(10).mean().iloc[-5]

            if avg_volume_5 > avg_volume_10 * 1.2:
                score += 30
                reasons.append("量能放大")
            elif avg_volume_5 > avg_volume_10:
                score += 20
                reasons.append("量能温和")

        return score, reasons

    def _calculate_volatility_factor(self, df: pd.DataFrame, latest: pd.Series) -> tuple[float, List[str]]:
        """
        计算波动率因子（0-100分）

        考虑：
        - 历史波动率
        - ATR（真实波动幅度）
        """
        score = 0
        reasons = []

        # 1. 20日波动率（100分）
        if len(df) >= 20:
            volatility = df["close"].pct_change().rolling(20).std().iloc[-1] * 100

            if 1 < volatility < 3:
                score += 80
                reasons.append(f"波动适中({volatility:.1f}%)")
            elif volatility < 1:
                score += 50
                reasons.append(f"波动较小({volatility:.1f}%)")
            elif volatility > 5:
                score += 30
                reasons.append(f"⚠️ 波动过大({volatility:.1f}%)")
            else:
                score += 60
                reasons.append(f"波动温和({volatility:.1f}%)")

        return score, reasons

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号

        综合多个因子评分，加权计算总分
        """
        if df.empty or len(df) < 60:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据不足"],
                confidence=0.0,
                metadata={}
            )

        latest = df.iloc[-1]

        # 计算各因子得分
        trend_score, trend_reasons = self._calculate_trend_factor(df, latest)
        momentum_score, momentum_reasons = self._calculate_momentum_factor(df, latest)
        value_score, value_reasons = self._calculate_value_factor(df, latest)
        volume_score, volume_reasons = self._calculate_volume_factor(df, latest)
        volatility_score, volatility_reasons = self._calculate_volatility_factor(df, latest)

        # 加权计算总分
        weights = self.params["weights"]
        total_score = (
            trend_score * weights["trend"] +
            momentum_score * weights["momentum"] +
            value_score * weights["value"] +
            volume_score * weights["volume"] +
            volatility_score * weights["volatility"]
        )

        # 组合原因
        all_reasons = []
        if trend_reasons:
            all_reasons.append(f"趋势({trend_score:.0f}分): {', '.join(trend_reasons[:2])}")
        if momentum_reasons:
            all_reasons.append(f"动量({momentum_score:.0f}分): {', '.join(momentum_reasons[:2])}")
        if value_reasons:
            all_reasons.append(f"价值({value_score:.0f}分): {', '.join(value_reasons[:2])}")

        # 计算置信度
        factor_scores = [trend_score, momentum_score, value_score, volume_score, volatility_score]
        score_std = np.std(factor_scores)
        confidence = min(1.0, total_score / 100 * (1 - score_std / 50))  # 分数一致性越高，置信度越高

        # 判断信号
        if total_score >= self.params["buy_threshold"]:
            action = "buy"
        elif total_score <= self.params["sell_threshold"]:
            action = "sell"
        else:
            action = "hold"

        return StrategyResult(
            action=action,
            score=total_score,
            reasons=all_reasons,
            confidence=confidence,
            metadata={
                "trend_score": trend_score,
                "momentum_score": momentum_score,
                "value_score": value_score,
                "volume_score": volume_score,
                "volatility_score": volatility_score,
                "factor_consistency": 100 - score_std,
            }
        )
