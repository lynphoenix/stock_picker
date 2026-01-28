# -*- coding: utf-8 -*-
"""
MACD + RSI 组合策略

基于原有 signal_engine.py 的逻辑重构
"""
import pandas as pd
import numpy as np
from typing import List
from .strategy_base import Strategy, StrategyResult


class MACDRSIStrategy(Strategy):
    """
    MACD + RSI 组合策略

    买入信号评分:
        - MACD金叉: 30分
        - RSI未超买: 15分
        - 均线多头: 20分
        - 成交量放大: 15分
        - 价格接近支撑: 10分

    卖出信号评分:
        - MACD死叉: 30分
        - RSI超买: 25分
        - 跌破均线: 20分
    """

    def __init__(self, params: dict = None):
        """
        Args:
            params: 策略参数
                - macd_weight: MACD权重 (默认30)
                - rsi_weight: RSI权重 (默认15)
                - ma_weight: 均线权重 (默认20)
                - volume_weight: 成交量权重 (默认15)
                - rsi_oversold: RSI超卖阈值 (默认30)
                - rsi_overbought: RSI超买阈值 (默认70)
                - buy_threshold: 买入阈值 (默认50)
                - sell_threshold: 卖出阈值 (默认60)
        """
        default_params = {
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

        # 合并用户参数
        if params:
            default_params.update(params)

        super().__init__("MACD_RSI", default_params)

    def get_required_indicators(self) -> List[str]:
        """需要的指标"""
        return ["MACD", "RSI", "MA", "VOLUME"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """生成交易信号"""
        if not self.validate_data(df):
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据不完整"],
                confidence=0.0
            )

        # 获取最新数据
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        # 计算买入评分
        buy_score, buy_reasons = self._calculate_buy_score(df, latest, prev)

        # 计算卖出评分
        sell_score, sell_reasons = self._calculate_sell_score(df, latest, prev)

        # 决策
        if sell_score >= self.params["sell_threshold"]:
            action = "sell"
            score = sell_score
            reasons = sell_reasons
        elif buy_score >= self.params["buy_threshold"]:
            action = "buy"
            score = buy_score
            reasons = buy_reasons
        else:
            action = "hold"
            score = max(buy_score, sell_score)
            reasons = ["信号不足"]

        return StrategyResult(
            action=action,
            score=score,
            reasons=reasons,
            confidence=score / 100.0,
            metadata={
                "buy_score": buy_score,
                "sell_score": sell_score,
                "rsi": latest.get("RSI", 0),
                "macd": latest.get("MACD", 0),
            }
        )

    def _calculate_buy_score(self, df: pd.DataFrame, latest: pd.Series, prev: pd.Series) -> tuple:
        """计算买入评分"""
        score = 0
        reasons = []

        # 1. MACD金叉
        if self._is_golden_cross(latest, prev):
            score += self.params["macd_weight"]
            reasons.append("MACD金叉")

        # 2. RSI超卖或未超买
        rsi = latest.get("RSI", 50)
        if rsi < self.params["rsi_oversold"]:
            score += self.params["rsi_weight"]
            reasons.append(f"RSI超卖({rsi:.1f})")
        elif rsi < 50:
            score += self.params["rsi_weight"] * 0.5
            reasons.append(f"RSI偏低({rsi:.1f})")

        # 3. 均线多头
        if self._is_bullish_ma(latest):
            score += self.params["ma_weight"]
            reasons.append("均线多头")
        elif latest.get("close", 0) > latest.get("MA20", 0):
            score += self.params["ma_weight"] * 0.5
            reasons.append("站上MA20")

        # 4. 成交量放大
        if self._is_volume_increase(df):
            score += self.params["volume_weight"]
            reasons.append("成交量放大")

        # 5. 价格接近支撑
        if self._is_near_support(latest):
            score += self.params["support_weight"]
            reasons.append("接近支撑位")

        return score, reasons

    def _calculate_sell_score(self, df: pd.DataFrame, latest: pd.Series, prev: pd.Series) -> tuple:
        """计算卖出评分"""
        score = 0
        reasons = []

        # 1. MACD死叉
        if self._is_death_cross(latest, prev):
            score += self.params["macd_weight"]
            reasons.append("MACD死叉")

        # 2. RSI超买
        rsi = latest.get("RSI", 50)
        if rsi > self.params["rsi_overbought"]:
            score += self.params["rsi_weight"] + 10
            reasons.append(f"RSI超买({rsi:.1f})")

        # 3. 跌破均线
        if self._is_bearish_ma(latest):
            score += self.params["ma_weight"]
            reasons.append("跌破均线")

        return score, reasons

    def _is_golden_cross(self, latest: pd.Series, prev: pd.Series) -> bool:
        """判断MACD金叉"""
        dif = latest.get("MACD_DIF", 0)
        dea = latest.get("MACD_DEA", 0)
        prev_dif = prev.get("MACD_DIF", 0)
        prev_dea = prev.get("MACD_DEA", 0)

        return dif > dea and prev_dif <= prev_dea

    def _is_death_cross(self, latest: pd.Series, prev: pd.Series) -> bool:
        """判断MACD死叉"""
        dif = latest.get("MACD_DIF", 0)
        dea = latest.get("MACD_DEA", 0)
        prev_dif = prev.get("MACD_DIF", 0)
        prev_dea = prev.get("MACD_DEA", 0)

        return dif < dea and prev_dif >= prev_dea

    def _is_bullish_ma(self, latest: pd.Series) -> bool:
        """判断均线多头排列"""
        close = latest.get("close", 0)
        ma5 = latest.get("MA5", 0)
        ma20 = latest.get("MA20", 0)

        return close > ma5 > ma20

    def _is_bearish_ma(self, latest: pd.Series) -> bool:
        """判断均线空头排列"""
        close = latest.get("close", 0)
        ma5 = latest.get("MA5", 0)
        ma20 = latest.get("MA20", 0)

        return close < ma5 < ma20

    def _is_volume_increase(self, df: pd.DataFrame) -> bool:
        """判断成交量放大"""
        if len(df) < 2 or "VOLUME_RATIO" not in df.columns:
            return False

        volume_ratio = df.iloc[-1].get("VOLUME_RATIO", 1.0)
        return volume_ratio > 1.2

    def _is_near_support(self, latest: pd.Series) -> bool:
        """判断价格接近支撑位"""
        close = latest.get("close", 0)
        ma20 = latest.get("MA20", 0)

        if ma20 == 0:
            return False

        diff_pct = (close - ma20) / ma20 * 100
        return 0 <= diff_pct <= 2
