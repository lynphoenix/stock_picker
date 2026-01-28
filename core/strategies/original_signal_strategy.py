# -*- coding: utf-8 -*-
"""
原有信号引擎策略 (Original SignalEngine Logic)

这是从 src/signal_engine.py 中提取的原始策略逻辑
保持与原有代码完全一致的评分规则
"""
from typing import Dict, List
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .strategy_base import Strategy, StrategyResult
from src.technical import TechnicalIndicators


class OriginalSignalStrategy(Strategy):
    """
    原有信号引擎策略

    完全复制 src/signal_engine.py 中的 SignalEngine.analyze_stock() 逻辑
    买入评分规则：
    - MACD金叉: 30分
    - RSI超卖: 25分
    - 站上20日均线: 20分
    - 板块热度: 最多25分
    买入阈值: 50分

    卖出条件：
    - MACD死叉: 30分
    - RSI超买: 25分
    - 跌破20日均线: 20分
    - 止损: 100分
    卖出阈值: 60分
    """

    def __init__(self, params: Dict = None):
        """
        Args:
            params:
                - buy_threshold: 买入阈值（默认50）
                - sell_threshold: 卖出阈值（默认60）
                - sector_heat: 板块热度（默认0.5，范围0-1）
                - stop_loss: 止损比例（默认-10%）
        """
        default_params = {
            "buy_threshold": 50,
            "sell_threshold": 60,
            "sector_heat": 0.5,  # 模拟板块热度
            "stop_loss": -10,
        }

        self.params = {**default_params, **(params or {})}
        self.name = "Original Signal Engine"
        self.description = "原有信号引擎策略（src/signal_engine.py）"
        self.tech = TechnicalIndicators()

    def get_required_indicators(self) -> List[str]:
        """需要的技术指标"""
        return ["MACD", "RSI", "MA"]

    def generate_signals(self, df: pd.DataFrame) -> StrategyResult:
        """
        生成交易信号

        完全按照原有 SignalEngine 的逻辑
        """
        if df.empty or len(df) < 60:
            return StrategyResult(
                action="hold",
                score=0,
                reasons=["数据不足"],
                confidence=0.0,
                metadata={}
            )

        # 计算技术指标（如果还没有）
        if "MACD_DIF" not in df.columns:
            df = self.tech.calculate_all(df)

        # 获取最新数据
        latest = df.iloc[-1]
        close = latest["close"]

        # 获取技术信号
        tech_signals = self.tech.get_latest_signals(df)

        # 计算买入信号评分
        buy_score = 0
        buy_reasons = []

        # 1. MACD金叉 (30分)
        if tech_signals.get("macd_signal") == "golden_cross":
            buy_score += 30
            buy_reasons.append("MACD金叉")

        # 2. RSI超卖反弹 (25分)
        if tech_signals.get("rsi_signal") == "oversold":
            buy_score += 25
            buy_reasons.append("RSI超卖")

        # 3. 站上20日均线 (20分)
        if tech_signals.get("ma_signal") == "bullish":
            buy_score += 20
            buy_reasons.append("站上20日均线")

        # 4. 板块热度 (最多25分)
        sector_heat = self.params["sector_heat"]
        if sector_heat > 0.6:  # 对应原代码的 sector_heat_percentile
            heat_score = int(sector_heat * 25)
            buy_score += heat_score
            buy_reasons.append(f"板块热度({int(sector_heat*100)}%)")

        # 计算卖出信号评分
        sell_score = 0
        sell_reasons = []

        # 1. MACD死叉 (30分)
        if tech_signals.get("macd_signal") == "death_cross":
            sell_score += 30
            sell_reasons.append("MACD死叉")

        # 2. RSI超买 (25分)
        if tech_signals.get("rsi_signal") == "overbought":
            sell_score += 25
            sell_reasons.append("RSI超买")

        # 3. 跌破20日均线 (20分)
        if tech_signals.get("ma_signal") == "bearish":
            sell_score += 20
            sell_reasons.append("跌破20日均线")

        # 4. 止损检查（如果有持仓成本价的话）
        # 这里简化处理，假设没有持仓成本

        # 风险提示
        risks = []
        if tech_signals.get("trend") == "down":
            risks.append("处于下跌趋势")
        if latest["RSI"] > 80:
            risks.append("RSI严重超买")

        # 综合判断（完全按原逻辑）
        if sell_score >= self.params["sell_threshold"]:
            return StrategyResult(
                action="sell",
                score=sell_score,
                reasons=sell_reasons,
                confidence=min(sell_score / 100, 1.0),
                metadata={
                    "risks": risks,
                    "indicators": {
                        "macd": float(latest["MACD"]),
                        "dif": float(latest["MACD_DIF"]),
                        "dea": float(latest["MACD_DEA"]),
                        "rsi": float(latest["RSI"]),
                        "ma20": float(latest["MA20"]),
                    }
                }
            )

        if buy_score >= self.params["buy_threshold"]:
            return StrategyResult(
                action="buy",
                score=buy_score,
                reasons=buy_reasons,
                confidence=min(buy_score / 100, 1.0),
                metadata={
                    "risks": risks,
                    "indicators": {
                        "macd": float(latest["MACD"]),
                        "dif": float(latest["MACD_DIF"]),
                        "dea": float(latest["MACD_DEA"]),
                        "rsi": float(latest["RSI"]),
                        "ma20": float(latest["MA20"]),
                    }
                }
            )

        # 持有
        return StrategyResult(
            action="hold",
            score=max(buy_score, sell_score),
            reasons=buy_reasons + sell_reasons if (buy_reasons or sell_reasons) else ["信号不足"],
            confidence=0.0,
            metadata={
                "risks": risks,
                "buy_score": buy_score,
                "sell_score": sell_score,
            }
        )
