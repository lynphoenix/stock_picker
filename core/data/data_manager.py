# -*- coding: utf-8 -*-
"""
数据管理器 - 统一数据接口
"""
import pandas as pd
from typing import List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from .providers import HistoricalDataProvider, RealtimeDataProvider
from .cache_manager import CacheManager


class DataManager:
    """
    数据管理器

    提供统一的数据访问接口，屏蔽历史数据和实时数据的差异
    """

    def __init__(self):
        self.historical = HistoricalDataProvider()
        self.realtime = RealtimeDataProvider()
        self.cache = CacheManager()

    def get_data(
        self,
        code: str,
        mode: str = "realtime",
        start_date: str = None,
        end_date: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        统一数据获取接口

        Args:
            code: 股票代码
            mode: 数据模式
                - "realtime": 实时数据（最新+最近120天）
                - "historical": 历史数据（指定时间范围）
                - "latest": 智能选择（优先实时，失败则用历史最新）
            start_date: 开始日期 (mode="historical" 时使用)
            end_date: 结束日期 (mode="historical" 时使用)
            use_cache: 是否使用缓存

        Returns:
            包含 OHLCV 的 DataFrame
        """
        if mode == "realtime":
            return self.realtime.fetch(code, use_cache=use_cache)

        elif mode == "historical":
            if start_date is None or end_date is None:
                raise ValueError("historical模式需要指定start_date和end_date")
            return self.historical.fetch(
                code,
                start_date=start_date,
                end_date=end_date,
                use_cache=use_cache
            )

        elif mode == "latest":
            # 优先获取实时数据
            df = self.realtime.fetch(code, use_cache=use_cache)

            # 如果失败，尝试获取最近的历史数据
            if df.empty:
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
                df = self.historical.fetch(
                    code,
                    start_date=start_date,
                    end_date=end_date,
                    use_cache=use_cache
                )

            return df

        else:
            raise ValueError(f"不支持的mode: {mode}，可选: realtime, historical, latest")

    def add_indicators(
        self,
        df: pd.DataFrame,
        indicators: List[str]
    ) -> pd.DataFrame:
        """
        为数据添加技术指标

        Args:
            df: 原始数据
            indicators: 指标列表，如 ["MACD", "RSI", "MA"]

        Returns:
            添加指标后的DataFrame
        """
        if df.empty:
            return df

        from core.indicators import IndicatorFactory

        df = df.copy()

        for indicator in indicators:
            try:
                df = IndicatorFactory.calculate(df, indicator)
            except Exception as e:
                print(f"计算指标 {indicator} 失败: {e}")

        return df

    def get_batch_data(
        self,
        codes: List[str],
        mode: str = "realtime",
        **kwargs
    ) -> dict:
        """
        批量获取数据

        Args:
            codes: 股票代码列表
            mode: 数据模式
            **kwargs: 传递给get_data的其他参数

        Returns:
            {code: DataFrame} 字典
        """
        result = {}

        for code in codes:
            df = self.get_data(code, mode=mode, **kwargs)
            if not df.empty:
                result[code] = df

        return result
