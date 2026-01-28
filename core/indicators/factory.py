# -*- coding: utf-8 -*-
"""
指标工厂 - 统一指标计算接口
"""
import pandas as pd
from typing import Dict, Callable
from .technical import TechnicalIndicators
from .fundamental import FundamentalIndicators


class IndicatorFactory:
    """
    指标工厂

    提供统一的指标计算接口，支持动态注册新指标
    """

    # 技术指标实例
    _tech = TechnicalIndicators()
    _fund = FundamentalIndicators()

    # 指标映射表
    _indicators: Dict[str, Callable] = {}

    @classmethod
    def register_indicators(cls):
        """注册所有内置指标"""
        # 技术指标
        cls._indicators["MA"] = cls._tech.add_ma
        cls._indicators["MACD"] = cls._tech.add_macd
        cls._indicators["RSI"] = cls._tech.add_rsi
        cls._indicators["BOLL"] = cls._tech.add_boll
        cls._indicators["KDJ"] = cls._tech.add_kdj
        cls._indicators["VOLUME"] = cls._tech.add_volume_indicators

        # 组合指标（一次性计算所有）
        cls._indicators["ALL_TECHNICAL"] = cls._tech.calculate_all

        # 基本面指标
        cls._indicators["FUNDAMENTAL"] = cls._fund.add_fundamental_score

    @classmethod
    def calculate(cls, df: pd.DataFrame, indicator: str) -> pd.DataFrame:
        """
        计算指标

        Args:
            df: 原始数据
            indicator: 指标名称，如 "MACD", "RSI", "MA"

        Returns:
            添加指标后的DataFrame

        Raises:
            ValueError: 如果指标不存在
        """
        # 确保指标已注册
        if not cls._indicators:
            cls.register_indicators()

        # 查找指标计算函数
        calculator = cls._indicators.get(indicator)

        if calculator is None:
            raise ValueError(
                f"未知的指标: {indicator}\n"
                f"支持的指标: {list(cls._indicators.keys())}"
            )

        # 计算指标
        return calculator(df)

    @classmethod
    def calculate_multiple(cls, df: pd.DataFrame, indicators: list) -> pd.DataFrame:
        """
        批量计算多个指标

        Args:
            df: 原始数据
            indicators: 指标列表

        Returns:
            添加所有指标后的DataFrame
        """
        for indicator in indicators:
            df = cls.calculate(df, indicator)
        return df

    @classmethod
    def register_custom(cls, name: str, calculator: Callable):
        """
        注册自定义指标

        Args:
            name: 指标名称
            calculator: 计算函数，接收DataFrame返回DataFrame

        Example:
            def my_indicator(df):
                df['MY_IND'] = df['close'].rolling(10).mean()
                return df

            IndicatorFactory.register_custom('MY_IND', my_indicator)
        """
        cls._indicators[name] = calculator

    @classmethod
    def list_indicators(cls) -> list:
        """列出所有可用指标"""
        if not cls._indicators:
            cls.register_indicators()
        return list(cls._indicators.keys())
