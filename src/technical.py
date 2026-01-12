# -*- coding: utf-8 -*-
"""
技术指标计算模块
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class TechnicalIndicators:
    """技术指标计算类"""

    def __init__(self):
        self.cfg = config.TECHNICAL_CONFIG

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算所有技术指标

        Args:
            df: 包含OHLCV数据的DataFrame

        Returns:
            添加技术指标后的DataFrame
        """
        if df.empty:
            return df

        df = df.copy()

        # MA均线
        df = self.add_ma(df)

        # MACD
        df = self.add_macd(df)

        # RSI
        df = self.add_rsi(df)

        # BOLL布林带
        df = self.add_boll(df)

        # KDJ
        df = self.add_kdj(df)

        # 成交量相关
        df = self.add_volume_indicators(df)

        return df

    def add_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加移动平均线"""
        for period in self.cfg["ma_periods"]:
            df[f"MA{period}"] = df["close"].rolling(window=period).mean()
        return df

    def add_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加MACD指标"""
        fast = self.cfg["macd_fast"]
        slow = self.cfg["macd_slow"]
        signal = self.cfg["macd_signal"]

        # 计算EMA
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

        # DIF
        df["MACD_DIF"] = ema_fast - ema_slow

        # DEA
        df["MACD_DEA"] = df["MACD_DIF"].ewm(span=signal, adjust=False).mean()

        # MACD柱
        df["MACD"] = 2 * (df["MACD_DIF"] - df["MACD_DEA"])

        return df

    def add_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加RSI指标"""
        period = self.cfg["rsi_period"]

        # 计算涨跌
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        # 计算平均涨跌
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # RSI
        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))

        return df

    def add_boll(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加布林带"""
        period = 20

        # 中轨
        df["BOLL_MID"] = df["close"].rolling(window=period).mean()

        # 标准差
        std = df["close"].rolling(window=period).std()

        # 上下轨
        df["BOLL_UPPER"] = df["BOLL_MID"] + 2 * std
        df["BOLL_LOWER"] = df["BOLL_MID"] - 2 * std

        return df

    def add_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加KDJ指标"""
        period = 9

        low_min = df["low"].rolling(window=period).min()
        high_max = df["high"].rolling(window=period).max()

        # RSV
        rsv = (df["close"] - low_min) / (high_max - low_min) * 100

        # K、D、J
        df["KDJ_K"] = rsv.ewm(com=2, adjust=False).mean()
        df["KDJ_D"] = df["KDJ_K"].ewm(com=2, adjust=False).mean()
        df["KDJ_J"] = 3 * df["KDJ_K"] - 2 * df["KDJ_D"]

        return df

    def add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加成交量指标"""
        # 量比（简化版：当前成交量/5日均量）
        df["VOLUME_MA5"] = df["volume"].rolling(window=5).mean()
        df["VOLUME_RATIO"] = df["volume"] / df["VOLUME_MA5"]

        # 换手率（如果有的话）
        # 这里简化为成交额/流通市值，实际应使用真实换手率
        if "amount" in df.columns and "float_cap" in df.columns:
            df["TURNOVER"] = (df["amount"] * 1000) / (df["float_cap"] * 100000000) * 100

        return df

    def get_latest_signals(self, df: pd.DataFrame) -> Dict:
        """
        获取最新的技术指标信号

        Returns:
            {
                "macd_signal": "golden_cross" / "death_cross" / "neutral",
                "rsi_signal": "oversold" / "overbought" / "neutral",
                "ma_signal": "bullish" / "bearish" / "neutral",
                "trend": "up" / "down" / "sideways"
            }
        """
        if df.empty or len(df) < 2:
            return {}

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        signals = {}

        # MACD信号
        if latest["MACD_DIF"] > latest["MACD_DEA"]:
            if prev["MACD_DIF"] <= prev["MACD_DEA"]:
                signals["macd_signal"] = "golden_cross"  # 金叉
            else:
                signals["macd_signal"] = "bullish"
        else:
            if prev["MACD_DIF"] >= prev["MACD_DEA"]:
                signals["macd_signal"] = "death_cross"  # 死叉
            else:
                signals["macd_signal"] = "bearish"

        # RSI信号
        rsi = latest["RSI"]
        if rsi < 30:
            signals["rsi_signal"] = "oversold"
        elif rsi > 70:
            signals["rsi_signal"] = "overbought"
        else:
            signals["rsi_signal"] = "neutral"

        # MA信号（价格与20日均线关系）
        if latest["close"] > latest["MA20"]:
            signals["ma_signal"] = "bullish"
        elif latest["close"] < latest["MA20"]:
            signals["ma_signal"] = "bearish"
        else:
            signals["ma_signal"] = "neutral"

        # 趋势判断
        if latest["MA5"] > latest["MA20"] > latest["MA60"]:
            signals["trend"] = "up"
        elif latest["MA5"] < latest["MA20"] < latest["MA60"]:
            signals["trend"] = "down"
        else:
            signals["trend"] = "sideways"

        return signals


if __name__ == "__main__":
    # 测试代码
    from src.data_fetcher import DataFetcher

    fetcher = DataFetcher()
    tech = TechnicalIndicators()

    # 获取测试数据
    df = fetcher.get_stock_history("000001")

    if not df.empty:
        print("=== 原始数据 ===")
        print(df.tail())

        print("\n=== 计算技术指标 ===")
        df_with_indicators = tech.calculate_all(df)
        print(df_with_indicators[["date", "close", "MA20", "MACD", "RSI"]].tail())

        print("\n=== 技术信号 ===")
        signals = tech.get_latest_signals(df_with_indicators)
        for key, value in signals.items():
            print(f"{key}: {value}")
